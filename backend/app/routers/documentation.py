"""Routes for Module 5: Documentation Generator."""
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app import db
from app.services.ingestion import read_file_safely
from app.services.doc_generator import generate_readme, generate_api_docs, generate_install_guide

router = APIRouter(prefix="/api/repositories/{repo_id}/docs", tags=["documentation"])


def _get_ready_repo(repo_id: str) -> dict:
    repo = db.get_repository(repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found.")
    if repo["status"] != "ready":
        raise HTTPException(status_code=400, detail=f"Repository isn't ready yet (status: {repo['status']}).")
    return repo


def _sample_files(repo: dict, limit: int = 15) -> list[tuple[str, str]]:
    structure = json.loads(repo["structure_json"] or "{}")
    paths: list[str] = []
    for cat_files in structure.get("category_files", {}).values():
        paths.extend(cat_files[:4])
    paths = paths[:limit]

    samples = []
    for path in paths:
        abs_path = Path(repo["local_path"]) / path
        if abs_path.exists():
            samples.append((path, read_file_safely(abs_path, max_chars=2000)))
    return samples


@router.get("/readme")
def get_readme(repo_id: str):
    repo = _get_ready_repo(repo_id)
    structure = json.loads(repo["structure_json"] or "{}")
    samples = _sample_files(repo)
    content = generate_readme(structure, samples, repo["name"])
    return {"content": content}


@router.get("/api")
def get_api_docs(repo_id: str):
    repo = _get_ready_repo(repo_id)
    samples = _sample_files(repo, limit=20)
    content = generate_api_docs(samples)
    return {"content": content}


@router.get("/install-guide")
def get_install_guide(repo_id: str):
    repo = _get_ready_repo(repo_id)
    structure = json.loads(repo["structure_json"] or "{}")
    samples = _sample_files(repo, limit=8)
    content = generate_install_guide(structure, samples)
    return {"content": content}
