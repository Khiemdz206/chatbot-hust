"""Các "generator": thứ biến prompt thành câu trả lời.

Điểm quan trọng nhất của file này: dù dùng model thương mại (phương án A)
hay model nhóm tự fine-tune (phương án B), backend đều gọi qua HTTP API.
Model fine-tune được chạy bằng Ollama hoặc vLLM, hai công cụ này mở ra
một API theo chuẩn OpenAI, nên chỉ cần đổi 3 dòng trong .env:

    LLM_PROVIDER=openai_compat
    OPENAI_BASE_URL=http://localhost:11434/v1   # địa chỉ Ollama/vLLM
    LLM_MODEL=chatbot-hust                      # tên model đã tạo

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
    """Không gọi model. Dùng để dev UI/BE khi chưa có API key."""
    name = "mock"

    async def stream(self, system: str, messages: list[dict]) -> AsyncIterator[str]:
        text = (
            "Đây là câu trả lời giả lập (chế độ mock). Hệ thống đã tìm thấy đoạn văn bản liên quan [1]. "
            "Khi đổi LLM_PROVIDER trong .env, câu trả lời thật sẽ được sinh từ các nguồn bên dưới."
        )
        for word in text.split(" "):
            await asyncio.sleep(0.02)
            yield word + " "


class AnthropicGenerator(Generator):
    """Phương án A: gọi API Anthropic (vd. LLM_MODEL=claude-opus-5-5)."""
    name = "anthropic"

    def __init__(self):
        from anthropic import AsyncAnthropic
        self.client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def stream(self, system: str, messages: list[dict]) -> AsyncIterator[str]:
        async with self.client.messages.stream(
            model=settings.llm_model,
            max_tokens=settings.max_answer_tokens,
            system=system,
            messages=messages,
            temperature=0.2,
        ) as s:
            async for text in s.text_stream:
                yield text


class OpenAICompatGenerator(Generator):
    """Phương án A (OpenAI và các API cùng chuẩn) hoặc phương án B (Ollama/vLLM)."""
    name = "openai_compat"

    def __init__(self):
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(
            base_url=settings.openai_base_url,
            api_key=settings.openai_api_key or "not-needed",
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
    provider = settings.llm_provider
    if provider == "anthropic":
        return AnthropicGenerator()
    if provider == "openai_compat":
        return OpenAICompatGenerator()
    return MockGenerator()
