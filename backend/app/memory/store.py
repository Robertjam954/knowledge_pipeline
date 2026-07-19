"""Agent memory as vault markdown - the vault is the memory store.

Memories are ordinary notes in Memory/ with `type: memory` frontmatter, retrieved
through the same RAG path as everything else (filtered to the Memory folder), and
human-editable in Obsidian. Hard rule elsewhere: memory notes never leave the vault
(excluded from blog sources).
"""
from __future__ import annotations

from app.core.config import settings
from app.rag.retriever import HybridRetriever
from app.vault import write_note


def remember(text: str, topic: str, tags: list[str] | None = None) -> str:
    path = write_note(
        settings.vault_path, settings.memory_folder, topic, text,
        meta={"type": "memory", "tags": tags or []},
    )
    return str(path)


async def recall(retriever: HybridRetriever, query: str, k: int = 5) -> list[dict]:
    hits = await retriever.search(query, k=k, folder=settings.memory_folder)
    return [
        {"note_title": h.note_title, "note_path": h.note_path, "text": h.text,
         "score": round(h.score, 4)}
        for h in hits
    ]
