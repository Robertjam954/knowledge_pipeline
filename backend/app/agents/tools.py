"""Agent tool registry (template pattern): each tool is an OpenAI-style function
schema plus an async handler. The registry is the single place tools are defined;
the service loop and the FastAPI routes both read from it.
"""
from __future__ import annotations

from typing import Any, Awaitable, Callable

from app.core.config import settings
from app.memory import store as memory_store
from app.publish.blog_export import draft_post
from app.publish.webhook import publish_post
from app.rag import qa
from app.rag.retriever import HybridRetriever
from app.vault import read_note

Handler = Callable[..., Awaitable[Any]]
_retriever: HybridRetriever | None = None


def set_retriever(r: HybridRetriever) -> None:
    global _retriever
    _retriever = r


def retriever() -> HybridRetriever:
    if _retriever is None:
        raise RuntimeError("retriever not initialized (app startup not run)")
    return _retriever


async def search_notes(query: str, k: int = 8, folder: str | None = None) -> list[dict]:
    hits = await retriever().search(query, k=k, folder=folder)
    return [{"note_title": h.note_title, "note_path": h.note_path, "text": h.text[:600],
             "score": round(h.score, 4), "via": h.via} for h in hits]


async def ask_notes(question: str) -> dict:
    return await qa.answer(retriever(), question)


async def read_note_tool(note_path: str) -> dict:
    from pathlib import Path

    p = Path(note_path)
    if not p.is_absolute():
        p = settings.vault_path / note_path
    n = read_note(p)
    return {"title": n.title, "meta": n.meta, "body": n.body, "links": n.links, "tags": n.tags}


async def graph_neighbors(note_title: str, hops: int = 1) -> list[str]:
    return sorted(retriever().graph.neighbors(note_title, hops=hops))


async def remember(text: str, topic: str, tags: list[str] | None = None) -> dict:
    return {"path": memory_store.remember(text, topic, tags)}


async def recall(query: str, k: int = 5) -> list[dict]:
    return await memory_store.recall(retriever(), query, k=k)


async def ingest_url_tool(url: str, mode: str = "article", atomic: bool = True) -> dict:
    from app.ingest.web import ingest_url

    result = await ingest_url(url, mode=mode, atomic=atomic)
    await retriever().refresh()
    return result


async def draft_blog_post(source_notes: list[str], angle: str | None = None,
                          length: str = "standard") -> dict:
    return await draft_post(source_notes, angle=angle, length=length)


async def publish_post_tool(post_path: str) -> dict:
    return await publish_post(post_path)


async def post_to_medium(post_path: str) -> dict:
    from app.publish import medium

    try:
        return await medium.post_draft(post_path)
    except ValueError:
        # no token (Medium stopped issuing them) - return paste-ready export instead
        return {"fallback": "paste", **medium.export_for_paste(post_path)}


def _schema(name: str, description: str, properties: dict, required: list[str]) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {"type": "object", "properties": properties, "required": required},
        },
    }


TOOLS: dict[str, dict] = {
    "search_notes": {
        "schema": _schema("search_notes", "Hybrid search over the Obsidian vault.",
                          {"query": {"type": "string"}, "k": {"type": "integer"},
                           "folder": {"type": "string"}}, ["query"]),
        "handler": search_notes,
    },
    "ask_notes": {
        "schema": _schema("ask_notes", "Answer a question from the vault with citations.",
                          {"question": {"type": "string"}}, ["question"]),
        "handler": ask_notes,
    },
    "read_note": {
        "schema": _schema("read_note", "Read a full note by vault-relative path.",
                          {"note_path": {"type": "string"}}, ["note_path"]),
        "handler": read_note_tool,
    },
    "graph_neighbors": {
        "schema": _schema("graph_neighbors", "Titles of notes linked to a note via [[wikilinks]].",
                          {"note_title": {"type": "string"}, "hops": {"type": "integer"}},
                          ["note_title"]),
        "handler": graph_neighbors,
    },
    "remember": {
        "schema": _schema("remember", "Store a durable memory as a vault note in Memory/.",
                          {"text": {"type": "string"}, "topic": {"type": "string"},
                           "tags": {"type": "array", "items": {"type": "string"}}},
                          ["text", "topic"]),
        "handler": remember,
    },
    "recall": {
        "schema": _schema("recall", "Retrieve stored memories relevant to a query.",
                          {"query": {"type": "string"}, "k": {"type": "integer"}}, ["query"]),
        "handler": recall,
    },
    "ingest_url": {
        "schema": _schema("ingest_url", "Extract a web page (or paper) into vault notes.",
                          {"url": {"type": "string"},
                           "mode": {"type": "string", "enum": ["article", "paper"]},
                           "atomic": {"type": "boolean"}}, ["url"]),
        "handler": ingest_url_tool,
    },
    "draft_blog_post": {
        "schema": _schema("draft_blog_post", "Draft a blog post from vault notes (never publishes).",
                          {"source_notes": {"type": "array", "items": {"type": "string"}},
                           "angle": {"type": "string"},
                           "length": {"type": "string", "enum": ["short", "standard", "deep"]}},
                          ["source_notes"]),
        "handler": draft_blog_post,
    },
    "publish_post": {
        "schema": _schema("publish_post", "Publish an approved post: flip frontmatter, fire deploy hook.",
                          {"post_path": {"type": "string"}}, ["post_path"]),
        "handler": publish_post_tool,
    },
    "post_to_medium": {
        "schema": _schema("post_to_medium", "Send a blog post to Medium as a DRAFT (never publishes).",
                          {"post_path": {"type": "string"}}, ["post_path"]),
        "handler": post_to_medium,
    },
}
