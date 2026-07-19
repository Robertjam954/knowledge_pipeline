"""QA over the vault: retrieve -> prompt Gemma (or Claude) -> answer with citations."""
from __future__ import annotations

from app.agents.client import chat
from app.rag.retriever import Hit, HybridRetriever

QA_SYSTEM = """You answer questions strictly from the provided notes. Cite every claim
with the bracketed source number like [1]. If the notes do not contain the answer,
say so plainly rather than guessing. Keep answers direct and practical."""


def _context_block(hits: list[Hit]) -> str:
    lines = []
    for i, h in enumerate(hits, 1):
        lines.append(f"[{i}] {h.note_title} (chunk {h.chunk_index}, via {h.via})\n{h.text}")
    return "\n\n".join(lines)


async def answer(retriever: HybridRetriever, question: str, k: int | None = None) -> dict:
    hits = await retriever.search(question, k=k)
    if not hits:
        return {"answer": "No relevant notes found - the index may be empty. Run a refresh first.",
                "sources": []}
    user = f"Notes:\n\n{_context_block(hits)}\n\nQuestion: {question}"
    text = await chat(QA_SYSTEM, user)
    return {
        "answer": text,
        "sources": [
            {"n": i + 1, "note_title": h.note_title, "note_path": h.note_path,
             "chunk_index": h.chunk_index, "score": round(h.score, 4), "via": h.via}
            for i, h in enumerate(hits)
        ],
    }
