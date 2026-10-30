"""Các "generator": thứ biến prompt thành câu trả lời.

Nhóm chỉ dùng model tự fine-tune, chạy local bằng Ollama. Ollama mở ra một
API theo chuẩn OpenAI, nên backend gọi nó qua HTTP như gọi một API bình thường:

    LLM_PROVIDER=ollama
    LLM_BASE_URL=http://localhost:11434/v1   # địa chỉ Ollama
    LLM_MODEL=chatbot-hust                   # tên model đã tạo bằng `ollama create`

Trước khi có model fine-tune, đặt LLM_MODEL=qwen2.5:7b (model gốc) để chạy thử.
Xem docs/14-finetune.md, mục "Đưa model fine-tune lên web".
"""
from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import AsyncIterator

from ..config import settings


class Generator(ABC):
    name: str = "base"

    @abstractmethod
    def stream(self, system: str, messages: list[dict]) -> AsyncIterator[str]:
        """Trả về từng mẩu chữ (token) của câu trả lời."""


class MockGenerator(Generator):
    """Không gọi model. Dùng để dev UI/BE khi chưa chạy Ollama."""
    name = "mock"

    async def stream(self, system: str, messages: list[dict]) -> AsyncIterator[str]:
        text = (
            "Đây là câu trả lời giả lập (chế độ mock). Hệ thống đã tìm thấy đoạn văn bản liên quan [1]. "
            "Khi đổi LLM_PROVIDER=ollama trong .env, câu trả lời thật sẽ được sinh từ các nguồn bên dưới."
        )
        for word in text.split(" "):
            await asyncio.sleep(0.02)
            yield word + " "


class OllamaGenerator(Generator):
    """Model chạy bằng Ollama (hoặc vLLM), gọi qua API chuẩn OpenAI."""
    name = "ollama"

    def __init__(self):
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key or "not-needed",
        )

    async def stream(self, system: str, messages: list[dict]) -> AsyncIterator[str]:
        resp = await self.client.chat.completions.create(
            model=settings.llm_model,
            messages=[{"role": "system", "content": system}, *messages],
            max_tokens=settings.max_answer_tokens,
            temperature=0.2,
            stream=True,
        )
        async for chunk in resp:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


def get_generator() -> Generator:
    if settings.llm_provider == "ollama":
        return OllamaGenerator()
    return MockGenerator()
