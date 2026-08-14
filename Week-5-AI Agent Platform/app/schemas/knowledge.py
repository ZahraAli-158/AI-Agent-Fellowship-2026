from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class DocumentOut(BaseModel):
    id: str
    filename: str
    file_type: str
    status: str
    num_chunks: int
    summary: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class SearchResult(BaseModel):
    document_id: str
    filename: str
    chunk_index: int
    content: str
    score: float


class AskRequest(BaseModel):
    question: str
    top_k: int = 5


class AskResponse(BaseModel):
    answer: str
    sources: list[SearchResult]
