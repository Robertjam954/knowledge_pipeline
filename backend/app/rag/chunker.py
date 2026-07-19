"""Paragraph-aware chunking. No sentence NLP dependency; blank-line paragraphs are
packed into ~chunk_chars windows with a small tail overlap so context survives cuts.
"""
from __future__ import annotations

from app.core.config import settings


def split_text(text: str, chunk_chars: int | None = None, overlap: int | None = None) -> list[str]:
    chunk_chars = chunk_chars or settings.chunk_chars
    overlap = overlap if overlap is not None else settings.chunk_overlap_chars
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    current = ""
    for para in paragraphs:
        # Hard-split any paragraph longer than a chunk on its own
        while len(para) > chunk_chars:
            head, para = para[:chunk_chars], para[chunk_chars - overlap:]
            if current:
                chunks.append(current)
                current = ""
            chunks.append(head)
        if len(current) + len(para) + 2 > chunk_chars and current:
            chunks.append(current)
            current = current[-overlap:] if overlap else ""
        current = f"{current}\n\n{para}".strip() if current else para
    if current:
        chunks.append(current)
    return chunks
