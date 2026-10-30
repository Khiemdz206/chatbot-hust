"""API của Chatbot HUST.

Chạy (từ thư mục backend/):
    uvicorn app.main:app --reload --port 8000
Mở http://localhost:8000 để dùng giao diện trong thư mục web/.
"""
from __future__ import annotations

import asyncio
import json
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .config import REPO_ROOT, settings
from .rag import pipeline
from .schemas import ChatRequest, ChatResponse, FeedbackRequest
from .store import store

app = FastAPI(title="Chatbot HUST API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# ------------------------------------------------------------ giới hạn tần suất
_last_seen: dict[str, float] = {}


def _check_rate(key: str) -> None:
    now = time.monotonic()
    if now - _last_seen.get(key, 0) < settings.min_seconds_between_questions:
        raise HTTPException(429, detail={"code": "RATE_LIMITED", "message": "Bạn hỏi nhanh quá, chờ vài giây rồi hỏi lại."})
    _last_seen[key] = now


def _sse(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


# ------------------------------------------------------------ endpoints
@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "llm_provider": settings.llm_provider,
        "llm_model": settings.llm_model or None,
        "retriever": settings.retriever,
    }


@app.post("/api/chat", response_model=None)
async def chat(req: ChatRequest, request: Request, stream: bool = Query(True)):
    _check_rate(req.session_id or (request.client.host if request.client else "anon"))

    answer_id = str(uuid.uuid4())
    started = time.monotonic()
    history = [t.model_dump() for t in req.history]

    async def run():
        """Chạy pipeline, gom kết quả để ghi log."""
        state = {"text": [], "sources": [], "meta": {}}
        async for ev in pipeline.answer(req.message, history):
            if ev["type"] == "token":
                state["text"].append(ev["text"])
            elif ev["type"] == "sources":
                state["sources"] = ev["items"]
            elif ev["type"] == "meta":
                state["meta"] = ev
            yield ev, state

    def log_row(state) -> dict:
        meta = state["meta"]
        return {
            "id": answer_id,
            "session_id": req.session_id,
            "question": req.message,
            "rewritten_question": meta.get("rewritten"),
            "answer": "".join(state["text"]),
            "chunk_ids": meta.get("chunk_ids", []),
            "model": meta.get("model"),
            "refused": meta.get("refused", False),
            "latency_ms": int((time.monotonic() - started) * 1000),
        }

    # ---- chế độ không stream: script eval dùng
    if not stream:
        state = None
        try:
            async for _, state in run():
                pass
        except Exception as e:
            return JSONResponse(status_code=502, content={"code": "UPSTREAM_ERROR", "message": str(e)})
        row = log_row(state)
        asyncio.create_task(store.log_chat(row))
        return ChatResponse(
            answer_id=answer_id,
            answer=row["answer"],
            sources=state["sources"],
            refused=row["refused"],
            latency_ms=row["latency_ms"],
        )

    # ---- chế độ stream (SSE): giao diện web dùng
    async def events():
        state = None
        try:
            async for ev, state in run():
                if ev["type"] == "token":
                    yield _sse("token", {"text": ev["text"]})
                elif ev["type"] == "sources":
                    yield _sse("sources", ev["items"])
            row = log_row(state)
            yield _sse("done", {"answer_id": answer_id, "refused": row["refused"], "latency_ms": row["latency_ms"]})
            asyncio.create_task(store.log_chat(row))
        except Exception as e:
            print(f"[chat] lỗi: {e!r}")
            yield _sse("error", {"code": "UPSTREAM_ERROR", "message": "Hệ thống đang lỗi, bạn thử lại sau ít phút."})

    return StreamingResponse(events(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.post("/api/feedback")
async def feedback(req: FeedbackRequest):
    await store.log_feedback(req.model_dump())
    return {"ok": True}


@app.post("/admin/reindex")
async def reindex(x_admin_token: str = Header(default="")):
    if not settings.admin_token or x_admin_token != settings.admin_token:
        raise HTTPException(401, detail={"code": "UNAUTHORIZED"})
    # TODO (T9): gọi pipeline của thư mục data/ (crawl -> clean -> chunk -> embed_upload)
    return {"ok": True, "message": "Chưa cài đặt. Hiện chạy tay các script trong data/."}


@app.exception_handler(HTTPException)
async def http_error(_, exc: HTTPException):
    detail = exc.detail if isinstance(exc.detail, dict) else {"code": "ERROR", "message": str(exc.detail)}
    return JSONResponse(status_code=exc.status_code, content=detail)


# ------------------------------------------------------------ phục vụ giao diện web/
WEB_DIR: Path = REPO_ROOT / "web"
if WEB_DIR.exists():
    app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
