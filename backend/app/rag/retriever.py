"""Truy xuất đoạn văn bản liên quan đến câu hỏi.

- MockRetriever: đọc file mẫu, chấm điểm bằng số từ trùng. Đủ để dev UI/BE.
- SupabaseRetriever: embed câu hỏi rồi gọi hàm SQL match_chunks (hybrid:
  vector + full-text, gộp bằng RRF). Xem supabase/migrations/001_init.sql.
"""
from __future__ import annotations

import asyncio
import json
import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache

from ..config import REPO_ROOT, settings


@dataclass
class Chunk:
    id: str
    title: str
    content: str
    section: str | None = None
    url: str | None = None
    effective_date: str | None = None
    score: float = 0.0


class Retriever:
    async def search(self, query: str, k: int) -> list[Chunk]:
        raise NotImplementedError


# ---------------------------------------------------------------- mock

_STOP = {"là", "và", "thì", "của", "cho", "có", "không", "được", "các", "những", "một",
         "em", "mình", "tôi", "bạn", "ạ", "nào", "gì", "như", "thế", "với", "khi", "để", "bao", "nhiêu"}


def _tokens(text: str) -> set[str]:
    text = unicodedata.normalize("NFC", text.lower())
    return {w for w in re.findall(r"\w+", text) if w not in _STOP and len(w) > 1}


class MockRetriever(Retriever):
    def __init__(self, path=REPO_ROOT / "data" / "samples" / "sample_chunks.jsonl"):
        self.chunks: list[Chunk] = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    self.chunks.append(Chunk(**json.loads(line)))

    async def search(self, query: str, k: int) -> list[Chunk]:
        q = _tokens(query)
        if not q:
            return []
        scored = []
        for c in self.chunks:
            overlap = len(q & _tokens(c.title + " " + (c.section or "") + " " + c.content))
            score = overlap / len(q)
            if overlap >= 2 and score >= 0.45:
                scored.append(Chunk(**{**c.__dict__, "score": score}))
        scored.sort(key=lambda c: c.score, reverse=True)
        return scored[:k]


# ---------------------------------------------------------------- supabase

@lru_cache(maxsize=1)
def _embedder():
    # Tải model lần đầu mất vài phút (bge-m3 ~2GB). Chỉ tải khi RETRIEVER=supabase.
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(settings.embed_model)


class SupabaseRetriever(Retriever):
    def __init__(self):
        from supabase import create_client
        self.client = create_client(settings.supabase_url, settings.supabase_key)

    def _search_sync(self, query: str, k: int) -> list[Chunk]:
        vec = _embedder().encode(query, normalize_embeddings=True).tolist()
        res = self.client.rpc("match_chunks", {
            "query_embedding": vec,
            "query_text": query,
            "match_count": k,
        }).execute()
        return [
            Chunk(
                id=str(r["id"]),
                title=r["title"],
                content=r["content"],
                section=r.get("section"),
                url=r.get("url"),
                effective_date=r.get("effective_date"),
                score=r.get("score", 0.0),
            )
            for r in res.data
        ]

    async def search(self, query: str, k: int) -> list[Chunk]:
        return await asyncio.to_thread(self._search_sync, query, k)


def get_retriever() -> Retriever:
    if settings.retriever == "supabase":
        return SupabaseRetriever()
    return MockRetriever()
