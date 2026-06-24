"""Routes for advanced features: Repository Comparison and Bug Investigation Assistant."""
from fastapi import APIRouter, HTTPException

from app import db
from app.models.schemas import BugInvestigationRequest, CompareRequest
from app.services.advanced_features import compare_repositories, investigate_bug

router = APIRouter(prefix="/api", tags=["advanced"])


@router.post("/repositories/{repo_id}/investigate")
def investigate(repo_id: str, payload: BugInvestigationRequest):
    repo = db.get_repository(repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found.")
    if repo["status"] != "ready":
        raise HTTPException(status_code=400, detail=f"Repository isn't ready yet (status: {repo['status']}).")
    return investigate_bug(repo_id, payload.description)


@router.post("/compare")
def compare(payload: CompareRequest):
    repo_a = db.get_repository(payload.repo_a_id)
    repo_b = db.get_repository(payload.repo_b_id)
    if not repo_a or not repo_b:
        raise HTTPException(status_code=404, detail="One or both repositories were not found.")
    if repo_a["status"] != "ready" or repo_b["status"] != "ready":
        raise HTTPException(status_code=400, detail="Both repositories must finish analyzing before comparing.")

    files_a = [f["rel_path"] for f in db.list_files(payload.repo_a_id)]
    files_b = [f["rel_path"] for f in db.list_files(payload.repo_b_id)]

    return compare_repositories(files_a, files_b, repo_a["name"], repo_b["name"])
