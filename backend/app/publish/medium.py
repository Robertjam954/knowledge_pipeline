"""Medium draft publishing (post-medium-draft pattern, legacy v1 API).

CAVEAT: Medium stopped issuing new integration tokens; api.medium.com/v1 still works
for accounts that already have one. Configure KP_MEDIUM_TOKEN (Medium -> Settings ->
Security and apps -> Integration tokens). Posts always go up as DRAFTS - review and
publish inside Medium, mirroring the local blog's human-gated flow.

If no token is available, export_for_paste() returns clean markdown to paste into
Medium's editor by hand.
"""
from __future__ import annotations

import logging
from pathlib import Path

import httpx

from app.core.config import settings
from app.vault import parse_frontmatter

logger = logging.getLogger(__name__)

API = "https://api.medium.com/v1"


def _load_post(post_path: str) -> tuple[str, dict, str]:
    path = Path(post_path)
    if not path.is_absolute():
        path = settings.blog_posts_dir / post_path
    if not path.exists():
        raise FileNotFoundError(str(path))
    meta, body = parse_frontmatter(path.read_text(encoding="utf-8"))
    title = path.stem.replace("-NEEDS-REVIEW", "").replace("-", " ").title()
    return title, meta, body


def export_for_paste(post_path: str) -> dict:
    """Token-free fallback: markdown ready to paste into Medium's editor."""
    title, meta, body = _load_post(post_path)
    return {"title": title, "markdown": f"# {title}\n\n{body}", "tags": meta.get("tags", [])}


async def post_draft(post_path: str) -> dict:
    if not settings.medium_token:
        raise ValueError(
            "KP_MEDIUM_TOKEN not set. Note: Medium no longer issues new integration "
            "tokens; if you cannot generate one, use export_for_paste instead."
        )
    title, meta, body = _load_post(post_path)
    headers = {"Authorization": f"Bearer {settings.medium_token}",
               "Content-Type": "application/json", "Accept": "application/json"}
    async with httpx.AsyncClient(timeout=30, headers=headers) as client:
        me = await client.get(f"{API}/me")
        me.raise_for_status()
        user_id = me.json()["data"]["id"]
        r = await client.post(
            f"{API}/users/{user_id}/posts",
            json={
                "title": title,
                "contentFormat": "markdown",
                "content": f"# {title}\n\n{body}",
                "tags": (meta.get("tags") or [])[:5],  # Medium caps at 5
                "publishStatus": "draft",
            },
        )
        r.raise_for_status()
        data = r.json()["data"]
    return {"medium_id": data.get("id"), "url": data.get("url"), "publishStatus": "draft"}
