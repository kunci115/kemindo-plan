"""DeepSeek LLM access (OpenAI-compatible).

Two entry points:
- chat_model(): LangChain ChatOpenAI bound to DeepSeek, for the LangGraph agent.
- json_complete(): raw OpenAI client for one-shot structured extraction / judging.

DeepSeek has no vision and no embeddings endpoint — handled elsewhere
(OCR preprocessing for images, local bge models for embeddings).
"""
from __future__ import annotations
import json
from functools import lru_cache
from typing import Any
from openai import OpenAI
from .config import get_settings


@lru_cache
def _client() -> OpenAI:
    s = get_settings()
    if not s.deepseek_api_key:
        raise RuntimeError("DEEPSEEK_API_KEY not set. Copy .env.example -> .env")
    return OpenAI(api_key=s.deepseek_api_key, base_url=s.deepseek_base_url)


@lru_cache
def chat_model(reasoning: bool = False):
    """LangChain chat model for the agent. Lazy import keeps base import light."""
    from langchain_openai import ChatOpenAI
    s = get_settings()
    return ChatOpenAI(
        api_key=s.deepseek_api_key,
        base_url=s.deepseek_base_url,
        model=s.model_reason if reasoning else s.model_tools,
        temperature=0.0 if reasoning else 0.2,
    )


def json_complete(system: str, user: str, *, reasoning: bool = False) -> dict[str, Any]:
    """One-shot completion that must return a JSON object."""
    s = get_settings()
    model = s.model_reason if reasoning else s.model_tools
    resp = _client().chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}],
        temperature=0.0,
        response_format={"type": "json_object"},
    )
    return json.loads(resp.choices[0].message.content or "{}")
