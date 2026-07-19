"""Vault IO: the Obsidian vault is the single source of truth.

Notes are plain markdown with optional YAML frontmatter. This module is the only
place that reads/writes vault files, so parsing rules (frontmatter, [[wikilinks]],
#tags) stay in one spot.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Iterator

import yaml

WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:[#|][^\]]*)?\]\]")
TAG_RE = re.compile(r"(?:^|\s)#([A-Za-z][\w/-]*)")
FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)


@dataclass
class Note:
    path: Path  # absolute
    title: str  # filename stem, which is how wikilinks address it
    meta: dict[str, Any] = field(default_factory=dict)
    body: str = ""
    links: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    @property
    def is_private(self) -> bool:
        return bool(self.meta.get("private", False))


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    try:
        meta = yaml.safe_load(m.group(1)) or {}
        if not isinstance(meta, dict):
            meta = {}
    except yaml.YAMLError:
        meta = {}
    return meta, text[m.end():]


def compose_note(meta: dict[str, Any], body: str) -> str:
    if not meta:
        return body
    fm = yaml.safe_dump(meta, sort_keys=False, allow_unicode=True, default_flow_style=False).strip()
    return f"---\n{fm}\n---\n\n{body.lstrip()}"


def parse_note(path: Path, text: str) -> Note:
    meta, body = parse_frontmatter(text)
    links = list(dict.fromkeys(WIKILINK_RE.findall(body)))
    tags = [t for t in TAG_RE.findall(body)]
    meta_tags = meta.get("tags") or []
    if isinstance(meta_tags, str):
        meta_tags = [meta_tags]
    tags = list(dict.fromkeys([*meta_tags, *tags]))
    return Note(path=path, title=path.stem, meta=meta, body=body, links=links, tags=tags)


def read_note(path: Path) -> Note:
    return parse_note(path, path.read_text(encoding="utf-8"))


def iter_notes(vault: Path) -> Iterator[Note]:
    """All markdown notes, skipping hidden dirs (.obsidian, .trash, ...)."""
    for p in sorted(vault.rglob("*.md")):
        if any(part.startswith(".") for part in p.relative_to(vault).parts):
            continue
        try:
            yield read_note(p)
        except (OSError, UnicodeDecodeError):
            continue


def safe_filename(title: str) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|#^\[\]]', "", title).strip()
    return cleaned[:120] or "untitled"


def write_note(
    vault: Path,
    folder: str,
    title: str,
    body: str,
    meta: dict[str, Any] | None = None,
    date_prefix: bool = True,
) -> Path:
    meta = dict(meta or {})
    meta.setdefault("date", date.today().isoformat())
    name = safe_filename(title)
    if date_prefix:
        name = f"{meta['date']} {name}"
    target_dir = vault / folder
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / f"{name}.md"
    n = 1
    while path.exists():
        n += 1
        path = target_dir / f"{name} {n}.md"
    path.write_text(compose_note(meta, body), encoding="utf-8")
    return path
