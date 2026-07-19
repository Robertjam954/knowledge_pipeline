"""Hybrid retrieval: numpy cosine + BM25, rank-fused, then wikilink-graph expansion.

The whole index is in-process: BM25 is rebuilt from the vault at refresh time and
vectors come from EmbedCache. ObsidianRAG's architecture, minus its ChromaDB layer.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np
from rank_bm25 import BM25Okapi

from app.core.config import settings
from app.rag.chunker import split_text
from app.rag.embed_cache import EmbedCache, EmbedFn
from app.rag.graph import VaultGraph
from app.vault import Note, iter_notes

logger = logging.getLogger(__name__)

RRF_K = 60  # standard reciprocal-rank-fusion constant


@dataclass
class Hit:
    note_path: str
    note_title: str
    chunk_index: int
    text: str
    score: float
    via: str = "hybrid"  # hybrid | graph
    detail: dict = field(default_factory=dict)


def _tokenize(text: str) -> list[str]:
    return [t for t in "".join(c.lower() if c.isalnum() else " " for c in text).split() if len(t) > 1]


class HybridRetriever:
    def __init__(self, embed: EmbedFn) -> None:
        self._embed = embed
        self.cache = EmbedCache(settings.cache_dir)
        self.notes: dict[str, Note] = {}
        self.graph = VaultGraph()
        self._bm25: BM25Okapi | None = None

    async def refresh(self, folder: str | None = None) -> int:
        """Rescan the vault, re-chunk, sync embeddings. Returns chunk count."""
        notes = [n for n in iter_notes(settings.vault_path) if not n.is_private]
        if folder:
            notes = [n for n in notes if n.path.is_relative_to(settings.vault_path / folder)]
        self.notes = {n.title: n for n in notes}
        self.graph = VaultGraph.build(notes)
        chunks = []
        for n in notes:
            for i, text in enumerate(split_text(n.body)):
                chunks.append(
                    {"note_path": str(n.path), "note_title": n.title, "chunk_index": i, "text": text}
                )
        await self.cache.sync(chunks, self._embed)
        corpus = [_tokenize(r["text"]) for r in self.cache.records]
        self._bm25 = BM25Okapi(corpus) if corpus else None
        logger.info("index refreshed: %d notes, %d chunks", len(notes), len(chunks))
        return len(chunks)

    async def search(self, query: str, k: int | None = None, folder: str | None = None) -> list[Hit]:
        k = k or settings.top_k
        records = self.cache.records
        if not records:
            return []

        qvec = (await self._embed([query]))[0]
        vec_scores = self.cache.cosine_scores(qvec)
        bm25_scores = (
            np.asarray(self._bm25.get_scores(_tokenize(query))) if self._bm25 else np.zeros(len(records))
        )

        # Reciprocal rank fusion weighted by settings.vector_weight
        vec_rank = np.argsort(-vec_scores)
        bm_rank = np.argsort(-bm25_scores)
        fused = np.zeros(len(records))
        for rank_pos, idx in enumerate(vec_rank):
            fused[idx] += settings.vector_weight / (RRF_K + rank_pos + 1)
        for rank_pos, idx in enumerate(bm_rank):
            fused[idx] += (1 - settings.vector_weight) / (RRF_K + rank_pos + 1)

        if folder:
            prefix = str(settings.vault_path / folder)
            for i, r in enumerate(records):
                if not r["note_path"].startswith(prefix):
                    fused[i] = -1.0

        order = np.argsort(-fused)[:k]
        hits = [
            Hit(
                note_path=records[i]["note_path"],
                note_title=records[i]["note_title"],
                chunk_index=records[i]["chunk_index"],
                text=records[i]["text"],
                score=float(fused[i]),
                detail={"vector": float(vec_scores[i]), "bm25": float(bm25_scores[i])},
            )
            for i in order
            if fused[i] > 0
        ]

        if settings.graph_expansion and hits:
            hits.extend(self._expand_via_graph(hits, k))
        return hits

    def _expand_via_graph(self, hits: list[Hit], k: int) -> list[Hit]:
        """Pull in first chunks of notes linked from the top hits (GraphRAG-lite)."""
        have_titles = {h.note_title for h in hits}
        extra: list[Hit] = []
        by_title: dict[str, dict] = {}
        for r in self.cache.records:
            if r["chunk_index"] == 0:
                by_title.setdefault(r["note_title"], r)
        for h in hits[: max(3, k // 2)]:
            for neighbor in self.graph.neighbors(h.note_title, hops=1):
                if neighbor in have_titles or neighbor not in by_title:
                    continue
                r = by_title[neighbor]
                extra.append(
                    Hit(
                        note_path=r["note_path"],
                        note_title=r["note_title"],
                        chunk_index=0,
                        text=r["text"],
                        score=h.score * settings.graph_neighbor_discount,
                        via="graph",
                        detail={"linked_from": h.note_title},
                    )
                )
                have_titles.add(neighbor)
        return extra
