"""Publishing: flip frontmatter, optionally git commit+push, fire the Vercel deploy hook."""
from __future__ import annotations

import logging
import subprocess
from pathlib import Path

import httpx

from app.core.config import settings
from app.vault import compose_note, parse_frontmatter

logger = logging.getLogger(__name__)


async def publish_post(post_path: str) -> dict:
    path = Path(post_path)
    if not path.is_absolute():
        path = settings.blog_posts_dir / post_path
    if not path.exists():
        raise FileNotFoundError(str(path))
    if "NEEDS-REVIEW" in path.name:
        raise ValueError("post is marked NEEDS-REVIEW; fix violations and rename before publishing")

    meta, body = parse_frontmatter(path.read_text(encoding="utf-8"))
    meta["published"] = True
    path.write_text(compose_note(meta, body), encoding="utf-8")

    pushed = False
    if settings.auto_git_publish:
        repo = path.parent.parent  # blog/
        for cmd in (["git", "add", str(path)],
                    ["git", "commit", "-m", f"publish: {path.stem}"],
                    ["git", "push"]):
            subprocess.run(cmd, cwd=repo, check=True, capture_output=True)
        pushed = True

    hook_fired = False
    if settings.vercel_deploy_hook_url:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(settings.vercel_deploy_hook_url)
            r.raise_for_status()
        hook_fired = True

    return {"path": str(path), "published": True, "git_pushed": pushed, "deploy_hook_fired": hook_fired}
