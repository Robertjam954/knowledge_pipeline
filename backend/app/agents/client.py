"""LLM + embedding clients. Default: LM Studio's OpenAI-compatible server, fully
local. Optional: Anthropic for drafting/extraction quality (KP_LLM_PROVIDER=anthropic).
"""
from __future__ import annotations

import logging
from functools import lru_cache

from openai import AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def lmstudio_client() -> AsyncOpenAI:
    return AsyncOpenAI(base_url=settings.lmstudio_base_url, api_key=settings.lmstudio_api_key)


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embeddings always come from the local model - they must be consistent with
    the cache, so provider switching does not apply here."""
    client = lmstudio_client()
    out: list[list[float]] = []
    # LM Studio handles moderate batches; chunk to stay well under request limits.
    for i in range(0, len(texts), 64):
        resp = await client.embeddings.create(model=settings.embed_model, input=texts[i : i + 64])
        out.extend([d.embedding for d in resp.data])
    return out


async def chat(system: str, user: str, provider: str | None = None, max_tokens: int = 4096) -> str:
    """Single-turn completion used by QA, ingestion extraction, and blog drafting."""
    provider = provider or settings.llm_provider
    if provider == "anthropic" and settings.anthropic_api_key:
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        msg = await client.messages.create(
            model=settings.anthropic_model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(b.text for b in msg.content if b.type == "text")

    resp = await lmstudio_client().chat.completions.create(
        model=settings.chat_model,
        max_tokens=max_tokens,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
    )
    return resp.choices[0].message.content or ""
