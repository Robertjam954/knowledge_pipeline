"""Blog drafting + hard-rule validation.

Three-pass pipeline: draft -> rules edit -> clarity edit (the user's plain-language
editor persona), then code-level validation of the hard rules before anything is
written to blog/posts/. Style rules live in blog/RULES.md and are injected into
every prompt, so tuning style means editing markdown, not code.
"""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from app.agents.client import chat
from app.core.config import settings
from app.vault import WIKILINK_RE, parse_frontmatter, read_note

_env = Environment(loader=FileSystemLoader(Path(__file__).parent / "prompts"), autoescape=False)

LENGTH_WORDS = {"short": 400, "standard": 900, "deep": 1800}
SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
BARE_FENCE_RE = re.compile(r"^```\s*$", re.MULTILINE)


def validate_post(md_text: str) -> list[str]:
    """Hard rules enforced in code. Returns a list of violations (empty = valid)."""
    violations: list[str] = []
    meta, body = parse_frontmatter(md_text)
    if not meta:
        return ["missing YAML frontmatter"]
    if meta.get("published") is not False:
        violations.append("published must be false on creation")
    if not DATE_RE.match(str(meta.get("date", ""))):
        violations.append("date must be YYYY-MM-DD")
    slug = meta.get("slug")
    if slug and not SLUG_RE.match(str(slug)):
        violations.append(f"slug not kebab-case: {slug!r}")
    if WIKILINK_RE.search(body):
        violations.append("unresolved [[wikilinks]] in body")
    if "—" in md_text or "–" in md_text:
        violations.append("em/en dashes present; use hyphens")
    # every opening fence must carry a language; count fences pairwise
    fences = re.findall(r"^```(\S*)\s*$", body, re.MULTILINE)
    openers = fences[::2]
    if any(not lang for lang in openers):
        violations.append("code fence without language tag")
    for src in meta.get("sources") or []:
        if str(src).startswith(f"{settings.memory_folder}/"):
            violations.append(f"memory note used as source: {src}")
    return violations


def _load_rules() -> str:
    p = settings.blog_rules_path
    return p.read_text(encoding="utf-8") if p.exists() else ""


def _published_posts() -> list[dict]:
    posts = []
    if settings.blog_posts_dir.exists():
        for p in sorted(settings.blog_posts_dir.glob("*.md")):
            meta, _ = parse_frontmatter(p.read_text(encoding="utf-8"))
            if meta.get("published"):
                posts.append({"title": p.stem, "slug": meta.get("slug") or p.stem.lower().replace(" ", "-")})
    return posts


async def draft_post(
    source_notes: list[str],
    angle: str | None = None,
    length: str = "standard",
) -> dict:
    """Run the three-pass draft pipeline and write blog/posts/<slug>.md.

    source_notes are vault-relative or absolute paths to markdown notes.
    Returns {path, violations} - violations non-empty means the draft was written
    with `-NEEDS-REVIEW` suffixed to the filename instead of being silently fixed.
    """
    notes = []
    for raw in source_notes:
        p = Path(raw)
        if not p.is_absolute():
            p = settings.vault_path / raw
        n = read_note(p)
        if n.is_private or n.path.is_relative_to(settings.vault_path / settings.memory_folder):
            continue  # hard rule: never expose private or memory notes
        notes.append({"path": str(n.path.relative_to(settings.vault_path)), "title": n.title,
                      "tags": n.tags, "body": n.body})
    if not notes:
        raise ValueError("no usable source notes (all private/memory or missing)")

    rules_md = _load_rules()
    user = _env.get_template("blog_draft.user.jinja2").render(
        angle=angle, length=length, length_words=LENGTH_WORDS.get(length, 900),
        today=date.today().isoformat(), notes=notes, published_posts=_published_posts(),
    )
    draft = await chat(_env.get_template("blog_draft.system.jinja2").render(rules_md=rules_md), user)
    draft = await chat(_env.get_template("blog_edit.system.jinja2").render(rules_md=rules_md), draft)
    draft = await chat(_env.get_template("clarity_edit.system.jinja2").render(), draft)

    # Normalize the one rule we never trust a model with
    meta, body = parse_frontmatter(draft)
    meta["published"] = False
    meta.setdefault("date", date.today().isoformat())
    meta.setdefault("sources", [n["path"] for n in notes])
    from app.vault import compose_note

    draft = compose_note(meta, body)
    violations = validate_post(draft)

    slug = meta.get("slug") or (notes[0]["title"].lower().replace(" ", "-"))
    slug = re.sub(r"[^a-z0-9-]", "", slug) or "untitled-post"
    settings.blog_posts_dir.mkdir(parents=True, exist_ok=True)
    name = f"{slug}-NEEDS-REVIEW.md" if violations else f"{slug}.md"
    path = settings.blog_posts_dir / name
    path.write_text(draft, encoding="utf-8")
    return {"path": str(path), "violations": violations}
