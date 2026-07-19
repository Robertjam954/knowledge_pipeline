"""Fixtures: temp vault + temp cache + deterministic fake embeddings (no LM Studio)."""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from app.core.config import settings

DIM = 32


async def fake_embed(texts: list[str]) -> list[list[float]]:
    """Bag-of-words hash embedding: texts sharing tokens get similar vectors."""
    out = []
    for text in texts:
        v = [0.0] * DIM
        for tok in text.lower().split():
            v[int(hashlib.md5(tok.encode()).hexdigest(), 16) % DIM] += 1.0
        out.append(v)
    return out


@pytest.fixture()
def vault(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    vault_dir = tmp_path / "vault"
    vault_dir.mkdir()
    monkeypatch.setattr(settings, "vault_path", vault_dir)
    monkeypatch.setattr(settings, "cache_dir", tmp_path / "cache")
    monkeypatch.setattr(settings, "blog_posts_dir", tmp_path / "posts")
    return vault_dir


def make_note(vault_dir: Path, folder: str, name: str, text: str) -> Path:
    d = vault_dir / folder
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{name}.md"
    p.write_text(text, encoding="utf-8")
    return p
