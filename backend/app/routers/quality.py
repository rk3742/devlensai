"""Routes for Module 6: Dead Code Detection and Module 7: Technical Debt Detector."""
from fastapi import APIRouter, HTTPException

from app import db

router = APIRouter(prefix="/api/repositories/{repo_id}/quality", tags=["quality"])


@router.get("/dead-code")
def get_dead_code(repo_id: str):
    repo = db.get_repository(repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found.")
    if repo["status"] != "ready":
        raise HTTPException(status_code=400, detail=f"Repository isn't ready yet (status: {repo['status']}).")
    return db.list_findings(repo_id, kind="dead_code")


@router.get("/tech-debt")
def get_tech_debt(repo_id: str):
    repo = db.get_repository(repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found.")
    if repo["status"] != "ready":
        raise HTTPException(status_code=400, detail=f"Repository isn't ready yet (status: {repo['status']}).")
    return db.list_findings(repo_id, kind="tech_debt")


@router.get("/summary")
def get_quality_summary(repo_id: str):
    repo = db.get_repository(repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found.")
    if repo["status"] != "ready":
        raise HTTPException(status_code=400, detail=f"Repository isn't ready yet (status: {repo['status']}).")

    dead_code = db.list_findings(repo_id, kind="dead_code")
    tech_debt = db.list_findings(repo_id, kind="tech_debt")
    severity_counts = {"high": 0, "medium": 0, "low": 0}
    for f in tech_debt:
        severity_counts[f.get("severity", "low")] = severity_counts.get(f.get("severity", "low"), 0) + 1

    return {
        "dead_code_count": len(dead_code),
        "tech_debt_count": len(tech_debt),
        "severity_counts": severity_counts,
    }
