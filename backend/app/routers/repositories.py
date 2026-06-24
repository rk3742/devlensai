"""
Routes for Module 1 (Repository Import), Module 2 (Structure Analyzer),
Module 3 (Code Explainer), and Module 9 (Onboarding Assistant).
"""
import json
import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse

from app import db
from app.config import REPOS_DIR
from app.models.schemas import GitHubImportRequest
from app.services.ingestion import (
    clone_github_repo, extract_zip, IngestionError, read_file_safely,
)
from app.services.analysis_orchestrator import run_full_analysis, cleanup_repository
from app.services.code_intelligence import explain_file, generate_onboarding_path
from app.services.diagram_generator import generate_architecture_svg, generate_architecture_description

router = APIRouter(prefix="/api/repositories", tags=["repositories"])


@router.get("")
def list_repos():
    return db.list_repositories()


@router.post("/import/github", status_code=202)
def import_github(payload: GitHubImportRequest, background_tasks: BackgroundTasks):
    repo_name = payload.url.rstrip("/").split("/")[-1].replace(".git", "") or "repository"
    repo_id = db.create_repository(
        name=repo_name, source_type="github", source_url=payload.url, local_path=""
    )

    try:
        repo_path = clone_github_repo(payload.url, repo_id)
    except IngestionError as e:
        db.update_repository(repo_id, status="failed", error_message=str(e))
        raise HTTPException(status_code=400, detail=str(e))

    db.update_repository(repo_id, local_path=str(repo_path))
    background_tasks.add_task(run_full_analysis, repo_id, repo_path)
    return {"id": repo_id, "name": repo_name, "status": "analyzing"}


@router.post("/import/zip", status_code=202)
async def import_zip(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Please upload a .zip file.")

    repo_name = file.filename.rsplit(".zip", 1)[0]
    repo_id = db.create_repository(name=repo_name, source_type="zip", source_url=None, local_path="")

    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        content = await file.read()
        if len(content) > 200 * 1024 * 1024:
            db.update_repository(repo_id, status="failed", error_message="ZIP file exceeds the 200MB limit.")
            raise HTTPException(status_code=400, detail="ZIP file exceeds the 200MB limit.")
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        repo_path = extract_zip(tmp_path, repo_id)
    except IngestionError as e:
        db.update_repository(repo_id, status="failed", error_message=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        tmp_path.unlink(missing_ok=True)

    db.update_repository(repo_id, local_path=str(repo_path))
    background_tasks.add_task(run_full_analysis, repo_id, repo_path)
    return {"id": repo_id, "name": repo_name, "status": "analyzing"}


@router.get("/{repo_id}")
def get_repo(repo_id: str):
    repo = db.get_repository(repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found.")
    return repo


@router.delete("/{repo_id}")
def delete_repo(repo_id: str):
    repo = db.get_repository(repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found.")
    cleanup_repository(repo_id, Path(repo["local_path"]))
    db.delete_repository(repo_id)
    return {"deleted": True}


@router.get("/{repo_id}/structure")
def get_structure(repo_id: str):
    repo = db.get_repository(repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found.")
    if repo["status"] != "ready":
        return {"status": repo["status"], "error_message": repo.get("error_message")}
    structure = json.loads(repo["structure_json"] or "{}")
    return structure


@router.get("/{repo_id}/diagram")
def get_diagram(repo_id: str):
    repo = db.get_repository(repo_id)
    if not repo or repo["status"] != "ready":
        raise HTTPException(status_code=400, detail="Repository isn't ready yet.")
    structure = json.loads(repo["structure_json"] or "{}")
    svg = generate_architecture_svg(structure.get("categories", {}), structure.get("languages", {}))
    description = generate_architecture_description(structure.get("categories", {}), structure.get("languages", {}))
    return {"svg": svg, "description": description}


@router.get("/{repo_id}/files")
def get_files(repo_id: str):
    repo = db.get_repository(repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found.")
    return db.list_files(repo_id)


@router.get("/{repo_id}/files/explain")
def explain_repo_file(repo_id: str, path: str):
    repo = db.get_repository(repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found.")

    file_record = db.get_file_by_path(repo_id, path)
    if not file_record:
        raise HTTPException(status_code=404, detail=f"File '{path}' not found in this repository.")

    if file_record.get("explanation_json"):
        return json.loads(file_record["explanation_json"])

    abs_path = Path(repo["local_path"]) / path
    if not abs_path.exists():
        raise HTTPException(status_code=404, detail="File no longer exists on disk.")

    content = read_file_safely(abs_path)
    explanation = explain_file(path, file_record["language"], content)
    if not explanation.get("error"):
        db.cache_file_explanation(repo_id, path, explanation)
    return explanation


@router.get("/{repo_id}/onboarding")
def get_onboarding_path(repo_id: str):
    repo = db.get_repository(repo_id)
    if not repo or repo["status"] != "ready":
        raise HTTPException(status_code=400, detail="Repository isn't ready yet.")

    structure = json.loads(repo["structure_json"] or "{}")
    files = db.list_files(repo_id)

    # Sample a handful of representative files for onboarding context.
    sample_paths = []
    for cat_files in structure.get("category_files", {}).values():
        sample_paths.extend(cat_files[:2])
    sample_paths = sample_paths[:10]

    sample_context_parts = []
    for path in sample_paths:
        abs_path = Path(repo["local_path"]) / path
        if abs_path.exists():
            content = read_file_safely(abs_path, max_chars=800)
            sample_context_parts.append(f"--- {path} ---\n{content}")

    summary_for_prompt = {
        "total_files": structure.get("total_files"),
        "categories": structure.get("categories"),
        "languages": structure.get("languages"),
    }

    result = generate_onboarding_path(summary_for_prompt, "\n\n".join(sample_context_parts))
    return result
