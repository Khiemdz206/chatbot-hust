"""Pipeline RAG: câu hỏi -> (viết lại) -> truy xuất -> prompt -> sinh -> nguồn.

Backend chỉ gọi answer() và phát lại các sự kiện cho UI. Mọi logic AI nằm
trong thư mục rag/ để luồng AI đổi thoải mái mà không đụng tới API.
"""
from __future__ import annotations

import re
from typing import AsyncIterator

from ..config import settings
from .generators import get_generator
from .prompts import REFUSAL_TEXT, SYSTEM_PROMPT, build_messages
from .retriever import Chunk, get_retriever

_retriever = None
_generator = None


def _components():
    global _retriever, _generator
    if _retriever is None:
        _retriever = get_retriever()
    if _generator is None:
        _generator = get_generator()
    return _retriever, _generator


async def rewrite_question(question: str, history: list[dict]) -> str:
    """TODO (T10): dùng model rẻ để gộp ngữ cảnh hội thoại và mở rộng viết tắt.

    Ví dụ: "thế còn học lại thì sao?" + lịch sử -> "Học lại một học phần thì tính điểm thế nào?"
    Bản đầu tiên trả nguyên câu hỏi.
    """
    return question


def _sources(chunks: list[Chunk]) -> list[dict]:
    return [
        {"n": i, "title": c.title, "section": c.section, "url": c.url, "effective_date": c.effective_date}
        for i, c in enumerate(chunks, start=1)
    ]


async def answer(question: str, history: list[dict]) -> AsyncIterator[dict]:
    """Phát ra các sự kiện:
    {"type": "token", "text": ...}            nhiều lần
    {"type": "sources", "items": [...]}       một lần
    {"type": "meta", ...}                     một lần, cuối cùng
    """
    retriever, generator = _components()

    rewritten = await rewrite_question(question, history)
    chunks = await retriever.search(rewritten, settings.top_k)

    if not chunks:
        yield {"type": "token", "text": REFUSAL_TEXT}
        yield {"type": "sources", "items": []}
        yield {"type": "meta", "refused": True, "rewritten": rewritten, "model": generator.name}
        return

    messages = build_messages(question, chunks, history)
    full = []
    async for text in generator.stream(SYSTEM_PROMPT, messages):
        full.append(text)
        yield {"type": "token", "text": text}

    answer_text = "".join(full)
    cited = sorted({int(n) for n in re.findall(r"\[(\d+)\]", answer_text) if 1 <= int(n) <= len(chunks)})

    # TODO (T15): nếu không có trích dẫn hợp lệ nào, thay bằng câu trả lời an toàn.
    yield {"type": "sources", "items": _sources(chunks)}
    yield {
        "type": "meta",
        "refused": False,
        "rewritten": rewritten,
        "model": f"{generator.name}:{settings.llm_model}" if settings.llm_model else generator.name,
        "cited": cited,
        "chunk_ids": [c.id for c in chunks],
    }
