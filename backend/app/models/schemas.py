"""Pydantic schemas for request/response validation."""
from typing import Optional
from pydantic import BaseModel, Field


class GitHubImportRequest(BaseModel):
    url: str = Field(..., description="Public GitHub repository URL")


class QuestionRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)


class BugInvestigationRequest(BaseModel):
    description: str = Field(..., min_length=1, max_length=2000)


class CompareRequest(BaseModel):
    repo_a_id: str
    repo_b_id: str


class RepositoryResponse(BaseModel):
    id: str
    name: str
    source_type: str
    source_url: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    file_count: int = 0
    total_chunks: int = 0
    created_at: float
