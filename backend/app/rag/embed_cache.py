"""File-based embedding cache - the replacement for a vector database.

Layout under cache_dir/embeddings/:
    manifest.json  - per-chunk records {id, note_path, note_title, chunk_index, sha}
    vectors.npz    - one float32 matrix, row i corresponds to manifest[i]

A chunk's identity is the sha256 of its text; unchanged chunks are never re-embedded.
Delete the folder to force a full rebuild - the vault markdown is always the source
of truth.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Awaitable, Callable

import numpy as np

EmbedFn = Callable[[list[str]], Awaitable[list[list[float]]]]


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class EmbedCache:
    def __init__(self, cache_dir: Path) -> None:
        self.dir = cache_dir / "embeddings"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.manifest_path = self.dir / "manifest.json"
        self.vectors_path = self.dir / "vectors.npz"
        self.records: list[dict] = []
        self.matrix: np.ndarray | None = None
        self._load()

    def _load(self) -> None:
        if self.manifest_path.exists() and self.vectors_path.exists():
            self.records = json.loads(self.manifest_path.read_text())
            self.matrix = np.load(self.vectors_path)["vectors"]

    def _save(self) -> None:
        self.manifest_path.write_text(json.dumps(self.records))
        if self.matrix is not None:
            np.savez_compressed(self.vectors_path, vectors=self.matrix)

    async def sync(self, chunks: list[dict], embed: EmbedFn) -> None:
        """Bring cache in line with `chunks` (dicts with note_path, note_title,
        chunk_index, text). Embeds only new/changed chunks; drops deleted ones."""
        wanted = {}
        for c in chunks:
            sha = _sha(c["text"])
            wanted[sha] = {**c, "sha": sha}

        have = {r["sha"]: i for i, r in enumerate(self.records)}
        keep_shas = [s for s in wanted if s in have]
        new_shas = [s for s in wanted if s not in have]

        rows = []
        records = []
        if self.matrix is not None and keep_shas:
            for s in keep_shas:
                rows.append(self.matrix[have[s]])
                records.append({k: wanted[s][k] for k in ("note_path", "note_title", "chunk_index", "sha")}
                               | {"text": wanted[s]["text"]})
        if new_shas:
            texts = [wanted[s]["text"] for s in new_shas]
            vectors = await embed(texts)
            for s, v in zip(new_shas, vectors):
                rows.append(np.asarray(v, dtype=np.float32))
                records.append({k: wanted[s][k] for k in ("note_path", "note_title", "chunk_index", "sha")}
                               | {"text": wanted[s]["text"]})

        self.records = records
        self.matrix = np.vstack(rows).astype(np.float32) if rows else None
        self._save()

    def cosine_scores(self, query_vec: list[float]) -> np.ndarray:
        if self.matrix is None or not len(self.records):
            return np.zeros(0)
        q = np.asarray(query_vec, dtype=np.float32)
        qn = np.linalg.norm(q) or 1.0
        mn = np.linalg.norm(self.matrix, axis=1)
        mn[mn == 0] = 1.0
        return (self.matrix @ q) / (mn * qn)
