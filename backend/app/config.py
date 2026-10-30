"""Cấu hình đọc từ file .env ở thư mục gốc repo.

Mọi thứ có thể thay đổi giữa các máy (API key, tên model, chế độ mock...)
đều đi qua đây. Không hard-code ở chỗ khác.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(REPO_ROOT / ".env")


def _get(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


class Settings:
    # --- Model sinh câu trả lời (generator) ---
    # mock          : không gọi model nào, trả lời giả để dev UI/BE
    # anthropic     : gọi API Anthropic (vd. Opus 5.5)
    # openai_compat : gọi bất kỳ API nào theo chuẩn OpenAI:
    #                 OpenAI, Ollama, vLLM (model fine-tune của nhóm)...
    llm_provider: str = _get("LLM_PROVIDER", "mock")
    llm_model: str = _get("LLM_MODEL", "")
    anthropic_api_key: str = _get("ANTHROPIC_API_KEY")
    openai_base_url: str = _get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    openai_api_key: str = _get("OPENAI_API_KEY")
    max_answer_tokens: int = int(_get("MAX_ANSWER_TOKENS", "1024"))

    # --- Truy xuất ---
    # mock     : đọc data/samples/sample_chunks.jsonl, tìm theo từ khoá
    # supabase : tìm hybrid (vector + full-text) trong Supabase
    retriever: str = _get("RETRIEVER", "mock")
    supabase_url: str = _get("SUPABASE_URL")
    supabase_key: str = _get("SUPABASE_SERVICE_KEY")
    embed_model: str = _get("EMBED_MODEL", "BAAI/bge-m3")
    top_k: int = int(_get("TOP_K", "6"))

    # --- Web ---
    cors_origins: list[str] = [o for o in _get("CORS_ORIGINS", "*").split(",") if o]
    min_seconds_between_questions: float = float(_get("MIN_SECONDS_BETWEEN_QUESTIONS", "2"))
    admin_token: str = _get("ADMIN_TOKEN")


settings = Settings()
