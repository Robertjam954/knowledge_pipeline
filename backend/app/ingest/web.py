"""Web ingestion: URL -> extracted text -> vault markdown.

Modes:
  article (default) - container note in Research/ + optional atomic Zettelkasten notes
  paper             - academic paper: structured summary note using the paper-summary format
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

import httpx
import trafilatura
from jinja2 import Environment, FileSystemLoader

from app.agents.client import chat
from app.core.config import settings
from app.vault import write_note

logger = logging.getLogger(__name__)

_env = Environment(loader=FileSystemLoader(Path(__file__).parent / "prompts"), autoescape=False)


async def fetch_text(url: str) -> tuple[str, str]:
    """Return (title, main text) for a URL using trafilatura extraction."""
    async with httpx.AsyncClient(timeout=45, follow_redirects=True,
                                 headers={"User-Agent": "knowledge-pipeline/0.1"}) as client:
        r = await client.get(url)
        r.raise_for_status()
        html = r.text
    text = trafilatura.extract(html, include_comments=False, include_tables=True) or ""
    meta = trafilatura.extract_metadata(html)
    title = (meta.title if meta and meta.title else url.rstrip("/").rsplit("/", 1)[-1]) or "untitled"
    return title, text


async def ingest_url(url: str, mode: str = "article", atomic: bool = True,
                     tags: list[str] | None = None) -> dict:
    title, text = await fetch_text(url)
    if not text.strip():
        raise ValueError(f"no extractable text at {url}")

    written: list[str] = []
    base_meta = {"source_url": url, "type": mode, "tags": tags or []}

    if mode == "paper":
        system = _env.get_template("paper_summary.system.jinja2").render()
        summary = await chat(system, text[:60000])
        path = write_note(settings.vault_path, settings.research_folder, f"{title} (paper summary)",
                          summary, meta=base_meta)
        written.append(str(path))
        return {"url": url, "title": title, "mode": mode, "notes": written}

    # article: container note holds the extracted text + provenance
    path = write_note(settings.vault_path, settings.research_folder, title, text, meta=base_meta)
    written.append(str(path))

    if atomic:
        system = _env.get_template("note_extract.system.jinja2").render()
        raw = await chat(system, text[:60000])
        try:
            start, end = raw.find("["), raw.rfind("]")
            atoms = json.loads(raw[start : end + 1]) if start != -1 else []
        except (json.JSONDecodeError, ValueError):
            logger.warning("atomic extraction returned unparseable JSON for %s", url)
            atoms = []
        titles = {a.get("title", "") for a in atoms}
        for a in atoms:
            if not a.get("title") or not a.get("body"):
                continue
            body = a["body"].strip()
            links = [t for t in a.get("links", []) if t in titles and t != a["title"]]
            if links:
                body += "\n\nRelated: " + " ".join(f"[[{t}]]" for t in links)
            body += f"\n\nSource: [[{Path(path).stem}]]"
            p = write_note(settings.vault_path, settings.zettel_folder, a["title"], body,
                           meta={"source_url": url, "type": "zettel", "tags": a.get("tags", [])})
            written.append(str(p))

    return {"url": url, "title": title, "mode": mode, "notes": written}
