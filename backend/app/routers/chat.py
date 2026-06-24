"""Routes for Module 4: Ask Questions (RAG chat over the repository)."""
from fastapi import APIRouter, HTTPException

from app import db
from app.models.schemas import QuestionRequest
from app.services.code_intelligence import answer_question

router = APIRouter(prefix="/api/repositories/{repo_id}/chat", tags=["chat"])


@router.get("")
def get_chat_history(repo_id: str):
    repo = db.get_repository(repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found.")
    return db.list_chat_messages(repo_id)


@router.post("")
def ask_question(repo_id: str, payload: QuestionRequest):
    repo = db.get_repository(repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found.")
    if repo["status"] != "ready":
        raise HTTPException(
            status_code=400,
            detail=f"Repository isn't ready yet (status: {repo['status']}). Wait for analysis to finish.",
        )

    history = db.list_chat_messages(repo_id)
    db.insert_chat_message(repo_id, "user", payload.question)

    result = answer_question(repo_id, payload.question, chat_history=history)
    db.insert_chat_message(repo_id, "assistant", result["answer"], sources=result.get("sources", []))

    return result
