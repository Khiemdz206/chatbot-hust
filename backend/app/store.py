"""Ghi log hội thoại và feedback.

Có Supabase thì ghi vào bảng chat_logs / feedback; chưa có thì ghi ra file
backend/logs/*.jsonl để dev vẫn xem được. Không lưu thông tin cá nhân.
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

from .config import settings

LOG_DIR = Path(__file__).resolve().parents[1] / "logs"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self):
        self.client = None
        if settings.supabase_url and settings.supabase_key:
            from supabase import create_client
            self.client = create_client(settings.supabase_url, settings.supabase_key)
        LOG_DIR.mkdir(exist_ok=True)

    def _write(self, table: str, row: dict) -> None:
        if self.client:
            self.client.table(table).insert(row).execute()
        else:
            with open(LOG_DIR / f"{table}.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps({**row, "created_at": _now()}, ensure_ascii=False) + "\n")

    async def log_chat(self, row: dict) -> None:
        try:
            await asyncio.to_thread(self._write, "chat_logs", row)
        except Exception as e:  # log hỏng không được làm hỏng câu trả lời
            print(f"[store] không ghi được chat_logs: {e}")

    async def log_feedback(self, row: dict) -> None:
        await asyncio.to_thread(self._write, "feedback", row)


store = Store()
