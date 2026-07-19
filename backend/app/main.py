"""FastAPI app: localhost-only API over the vault pipeline.

Run: uvicorn app.main:app --reload --port 8600  (from backend/)
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.agents import tools as tool_registry
from app.agents.client import embed_texts
from app.agents.service import run_agent
from app.core.config import settings
from app.memory import store as memory_store
from app.publish.blog_export import draft_post, validate_post
from app.publish.webhook import publish_post
from app.rag import qa
from app.rag.retriever import HybridRetriever

retriever = HybridRetriever(embed=embed_texts)


@asynccontextmanager
async def lifespan(app: FastAPI):
    tool_registry.set_retriever(retriever)
    settings.vault_path.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(title="knowledge-pipeline", lifespan=lifespan)


class AskBody(BaseModel):
    question: str
    k: int | None = None


class IngestUrlBody(BaseModel):
    url: str
    mode: str = "article"
    atomic: bool = True


class RememberBody(BaseModel):
    text: str
    topic: str
    tags: list[str] = []


class DraftBody(BaseModel):
    source_notes: list[str]
    angle: str | None = None
    length: str = "standard"


class AgentBody(BaseModel):
    message: str


@app.get("/health")
async def health() -> dict:
    return {"ok": True, "vault": str(settings.vault_path),
            "chunks_indexed": len(retriever.cache.records)}


@app.post("/index/refresh")
async def refresh() -> dict:
    n = await retriever.refresh()
    return {"chunks": n}


@app.get("/search")
async def search(q: str, k: int = 8, folder: str | None = None) -> list[dict]:
    hits = await retriever.search(q, k=k, folder=folder)
    return [{"note_title": h.note_title, "note_path": h.note_path, "chunk_index": h.chunk_index,
             "text": h.text, "score": h.score, "via": h.via, "detail": h.detail} for h in hits]


@app.post("/ask")
async def ask(body: AskBody) -> dict:
    return await qa.answer(retriever, body.question, k=body.k)


@app.post("/ingest/url")
async def ingest_url_route(body: IngestUrlBody) -> dict:
    from app.ingest.web import ingest_url

    result = await ingest_url(body.url, mode=body.mode, atomic=body.atomic)
    await retriever.refresh()
    return result


@app.post("/ingest/youtube")
async def ingest_youtube_route(url: str) -> dict:
    from app.ingest.youtube import ingest_youtube

    result = await ingest_youtube(url)
    await retriever.refresh()
    return result


@app.post("/memory")
async def remember_route(body: RememberBody) -> dict:
    return {"path": memory_store.remember(body.text, body.topic, body.tags)}


@app.get("/memory")
async def recall_route(q: str, k: int = 5) -> list[dict]:
    return await memory_store.recall(retriever, q, k=k)


@app.post("/blog/draft")
async def blog_draft(body: DraftBody) -> dict:
    try:
        return await draft_post(body.source_notes, angle=body.angle, length=body.length)
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/blog/posts")
async def blog_posts() -> list[dict]:
    from app.vault import parse_frontmatter

    out = []
    if settings.blog_posts_dir.exists():
        for p in sorted(settings.blog_posts_dir.glob("*.md")):
            text = p.read_text(encoding="utf-8")
            meta, _ = parse_frontmatter(text)
            out.append({"file": p.name, "published": bool(meta.get("published")),
                        "date": str(meta.get("date", "")), "tags": meta.get("tags", []),
                        "violations": validate_post(text) if not meta.get("published") else []})
    return out


@app.post("/blog/publish")
async def blog_publish(post_path: str) -> dict:
    try:
        return await publish_post(post_path)
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/agent/chat")
async def agent_chat(body: AgentBody) -> dict:
    return await run_agent(body.message)
