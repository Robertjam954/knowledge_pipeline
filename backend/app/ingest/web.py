"""Web ingestion: URL -> extracted text -> vault markdown.

Modes:
  article (default) - container note in Research/ + optional atomic Zettelkasten notes
  paper             - academic paper: structured summary note using the paper-summary format
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
import trafilatura
from jinja2 import Environment, FileSystemLoader

from app.agents.client import chat
from app.core.config import settings
from app.vault import write_note

logger = logging.getLogger(__name__)

_env = Environment(loader=FileSystemLoader(Path(__file__).parent / "prompts"), autoescape=False)

# Non-document targets we never treat as ingestable "resources".
_ASSET_SUFFIXES = (
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico", ".css", ".js",
    ".zip", ".gz", ".mp4", ".mp3", ".woff", ".woff2", ".ttf", ".xml", ".json",
)
_ANCHOR_RE = re.compile(r'<a\b[^>]*\bhref="([^"]+)"[^>]*>(.*?)</a>', re.DOTALL | re.IGNORECASE)
_MAIN_RE = re.compile(r"<main\b[^>]*>(.*?)</main>", re.DOTALL | re.IGNORECASE)


async def fetch_html(url: str) -> str:
    """Fetch raw HTML for a URL (follows redirects)."""
    async with httpx.AsyncClient(timeout=45, follow_redirects=True,
                                 headers={"User-Agent": "knowledge-pipeline/0.1"}) as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.text


def _extract_from_html(html: str, url: str) -> tuple[str, str]:
    text = trafilatura.extract(html, include_comments=False, include_tables=True) or ""
    meta = trafilatura.extract_metadata(html)
    title = (meta.title if meta and meta.title else url.rstrip("/").rsplit("/", 1)[-1]) or "untitled"
    return title, text


async def fetch_text(url: str) -> tuple[str, str]:
    """Return (title, main text) for a URL using trafilatura extraction."""
    return _extract_from_html(await fetch_html(url), url)


def _norm(url: str) -> str:
    return url.split("#")[0].rstrip("/")


def extract_links(
    html: str,
    base_url: str,
    same_domain: bool = True,
    path_contains: str | None = None,
) -> list[dict]:
    """Resource links from a hub page's main content, resolved and de-duplicated.

    Scans anchors inside <main> (falling back to the whole document), resolves
    relative hrefs against base_url, and drops fragments, non-HTTP schemes, static
    assets, and the hub page itself. Order is preserved (first occurrence wins).
    """
    region_match = _MAIN_RE.search(html)
    region = region_match.group(1) if region_match else html
    base_host = urlparse(base_url).netloc
    hub = _norm(base_url)
    out: list[dict] = []
    seen: set[str] = set()
    for href, inner in _ANCHOR_RE.findall(region):
        if href.startswith(("#", "mailto:", "javascript:", "tel:", "data:")):
            continue
        full = _norm(urljoin(base_url, href))
        parsed = urlparse(full)
        if parsed.scheme not in ("http", "https"):
            continue
        if same_domain and parsed.netloc != base_host:
            continue
        if parsed.path.lower().endswith(_ASSET_SUFFIXES):
            continue
        if path_contains and path_contains not in full:
            continue
        if full == hub or full in seen:
            continue
        text = re.sub(r"<[^>]+>", " ", inner)
        text = re.sub(r"\s+", " ", text).strip()
        seen.add(full)
        out.append({"url": full, "text": text})
    return out


async def ingest_url(url: str, mode: str = "article", atomic: bool = True,
                     tags: list[str] | None = None) -> dict:
    title, text = await fetch_text(url)
    if not text.strip():
        raise ValueError(f"no extractable text at {url}")

    written: list[str] = []
    base_meta = {"source_url": url, "type": mode, "tags": tags or []}

    if mode == "paper":
        system = _env.get_template("paper_summary.system.jinja2").render()
        summary = await chat(system, text[:settings.ingest_max_chars])
        path = write_note(settings.vault_path, settings.research_folder, f"{title} (paper summary)",
                          summary, meta=base_meta)
        written.append(str(path))
        return {"url": url, "title": title, "mode": mode, "notes": written}

    # article: container note holds the extracted text + provenance
    path = write_note(settings.vault_path, settings.research_folder, title, text, meta=base_meta)
    written.append(str(path))

    if atomic:
        system = _env.get_template("note_extract.system.jinja2").render()
        raw = await chat(system, text[:settings.ingest_max_chars])
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


async def crawl_resources(
    url: str,
    mode: str = "article",
    atomic: bool = True,
    limit: int = 50,
    same_domain: bool = True,
    path_contains: str | None = None,
    tags: list[str] | None = None,
) -> dict:
    """Ingest every resource linked from a hub page.

    Fetches ``url`` once, extracts the linked resources (see :func:`extract_links`),
    and ingests each through :func:`ingest_url`. Failures on individual links are
    captured per-result rather than aborting the whole crawl. Returns a summary with
    counts, the flat list of written note paths, and a per-link result list.
    """
    html = await fetch_html(url)
    links = extract_links(html, url, same_domain=same_domain, path_contains=path_contains)
    if limit and limit > 0:
        links = links[:limit]

    results: list[dict] = []
    notes: list[str] = []
    for link in links:
        target = link["url"]
        try:
            res = await ingest_url(target, mode=mode, atomic=atomic, tags=tags)
            notes.extend(res["notes"])
            results.append({"url": target, "status": "ok", "title": res["title"],
                            "notes": res["notes"]})
        except Exception as exc:  # one bad link must not sink the crawl
            logger.warning("crawl: failed to ingest %s: %s", target, exc)
            results.append({"url": target, "status": "error", "error": str(exc)})

    ingested = sum(1 for r in results if r["status"] == "ok")
    return {
        "hub_url": url,
        "found": len(links),
        "ingested": ingested,
        "failed": len(results) - ingested,
        "notes": notes,
        "results": results,
    }
