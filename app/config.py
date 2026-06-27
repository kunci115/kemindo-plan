"""Central config. Reads .env. No secrets hardcoded."""
from __future__ import annotations
import os
from pathlib import Path
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
KNOWLEDGE_DIR = DATA_DIR / "knowledge"


def _b(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    # DeepSeek (OpenAI-compatible)
    deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "")
    deepseek_base_url: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    model_tools: str = os.getenv("DEEPSEEK_MODEL_TOOLS", "deepseek-chat")
    model_reason: str = os.getenv("DEEPSEEK_MODEL_REASON", "deepseek-reasoner")

    # Retrieval
    embed_model: str = os.getenv("EMBED_MODEL", "BAAI/bge-small-en-v1.5")
    rerank_model: str = os.getenv("RERANK_MODEL", "BAAI/bge-reranker-base")
    enable_dense: bool = _b("ENABLE_DENSE_RETRIEVAL", "true")

    # OCR
    enable_ocr: bool = _b("ENABLE_OCR", "false")

    @property
    def has_llm(self) -> bool:
        return bool(self.deepseek_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
