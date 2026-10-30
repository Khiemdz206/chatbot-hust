"""Kiểu dữ liệu vào/ra của API. Phải khớp docs/02-api-contract.md."""
from typing import Literal

from pydantic import BaseModel, Field


class Turn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    session_id: str | None = Field(default=None, max_length=100)
    history: list[Turn] = Field(default_factory=list, max_length=12)


class Source(BaseModel):
    n: int
    title: str
    section: str | None = None
    url: str | None = None
    effective_date: str | None = None


class ChatResponse(BaseModel):
    """Dùng khi gọi /api/chat?stream=false (script eval dùng cách này)."""
    answer_id: str
    answer: str
    sources: list[Source]
    refused: bool
    latency_ms: int


class FeedbackRequest(BaseModel):
    answer_id: str = Field(max_length=100)
    rating: Literal[1, -1]
    comment: str | None = Field(default=None, max_length=1000)
