"""Hàm gọi model đơn giản (không stream) dùng chung cho data/, finetune/, eval/.

Mỗi "vai trò" (teacher, judge1, judge2, cleaner...) đọc cấu hình riêng từ .env:
    <ROLE>_PROVIDER = anthropic | openai_compat
    <ROLE>_MODEL    = tên model
    <ROLE>_BASE_URL = (chỉ openai_compat) địa chỉ API, mặc định OpenAI
Ví dụ: TEACHER_PROVIDER=anthropic, TEACHER_MODEL=claude-opus-5-5
API key lấy từ ANTHROPIC_API_KEY / OPENAI_API_KEY.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(REPO_ROOT / ".env")


def chat(role: str, system: str, user: str, max_tokens: int = 2048, temperature: float = 0.2) -> str:
    prefix = role.upper()
    provider = os.getenv(f"{prefix}_PROVIDER", "anthropic")
    model = os.getenv(f"{prefix}_MODEL")
    if not model:
        raise RuntimeError(f"Chưa đặt {prefix}_MODEL trong .env")

    if provider == "anthropic":
        from anthropic import Anthropic
        client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        msg = client.messages.create(
            model=model, max_tokens=max_tokens, temperature=temperature,
            system=system, messages=[{"role": "user", "content": user}],
        )
        return "".join(b.text for b in msg.content if b.type == "text")

    from openai import OpenAI
    client = OpenAI(
        base_url=os.getenv(f"{prefix}_BASE_URL", "https://api.openai.com/v1"),
        api_key=os.getenv(f"{prefix}_API_KEY") or os.getenv("OPENAI_API_KEY") or "not-needed",
    )
    resp = client.chat.completions.create(
        model=model, max_tokens=max_tokens, temperature=temperature,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
    )
    return resp.choices[0].message.content or ""


def parse_json(text: str):
    """Lấy JSON đầu tiên trong câu trả lời của model (model hay bọc trong ```json)."""
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    raw = m.group(1) if m else text
    start = min([i for i in (raw.find("{"), raw.find("[")) if i != -1], default=0)
    return json.loads(raw[start:])
