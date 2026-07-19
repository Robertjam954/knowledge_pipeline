# Knowledge Pipeline

Local-first personal knowledge system: extract from web sources and Apple Notes into an
Obsidian vault, ask questions over it with local AI (LM Studio + Gemma), and turn notes
into blog posts published via Vercel (and Medium drafts).

**Design rule: no external database.** The vault's markdown is the only source of truth.
Vectors live in a rebuildable file cache (numpy npz + manifest); keyword search (BM25) and
the [[wikilink]] graph are rebuilt in memory. Delete `.cache/` any time.

```
web / YouTube / papers ──┐
Apple Notes (plugin) ────┼──> Obsidian vault (markdown + wikilinks)
agent "remember" ────────┘         │
                                   ├──> hybrid RAG (numpy cosine + BM25 + graph expansion)
                                   │        └──> QA with citations (Gemma via LM Studio)
                                   └──> blog drafts (3-pass: draft, rules edit, clarity edit)
                                            └──> Vercel deploy hook / Medium draft
```

## Run

```bash
# Backend (port 8600)
cd backend && python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
cp ../.env.example .env   # adjust vault path, models
.venv/bin/uvicorn app.main:app --reload --port 8600

# Index + ask
curl -X POST localhost:8600/index/refresh
curl -X POST localhost:8600/ask -H 'content-type: application/json' -d '{"question":"..."}'

# Frontend shell (port 5273, proxies /api -> 8600)
cd frontend && npm install && npm run dev

# Tests
cd backend && .venv/bin/python -m pytest -q
```

Requires [LM Studio](https://lmstudio.ai) serving on localhost:1234 with a Gemma 3 chat
model and an embedding model loaded (see .env.example for names).

## Layout

- `backend/app/` - FastAPI + agent tool loop; `rag/` (retrieval), `ingest/` (web, YouTube,
  papers, Apple Notes), `memory/` (vault-backed agent memory), `publish/` (blog + Medium)
- `blog/` - RULES.md (style + hard rules) and posts/; site is nextjs-obsidian-blog-kit
  (see blog/README.md)
- `frontend/` - Vite + React shell (Ask / Search / Graph / Ingest / Blog / Settings)
- `.claude/agents/self-documenter.md` - assigned doc-sync agent; ADRs in `docs/adr/`
- `STATUS.md` - live checklist the portfolio dashboard reads

Reference designs: chat-with-your-data accelerator (structure), ObsidianRAG (hybrid +
graph retrieval, minus ChromaDB), Obsidian Importer (Apple Notes), knowledge-manager
(Zettelkasten ingestion), nextjs-obsidian-blog-kit (publishing).
