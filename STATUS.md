# Status

Live checklist of what is left to complete on this project, in the same checkbox
format the portfolio tracking dashboard reads. Check a box (`[ ]` -> `[x]`) as
you finish. The self-documenter agent (.claude/agents/self-documenter.md) keeps
this file honest.

> Project: **Knowledge Pipeline** · Stage: **scaffold complete, ingestion next**
> Local-first: Obsidian vault is the only source of truth, no external database.
> Stack: FastAPI + numpy/BM25 RAG + LM Studio (Gemma) + React shell + blog kit.
> Last doc sync: 2026-07-17

## 1. Scaffold
- [x] Backend: config, vault IO, chunker, wikilink graph, file-based embedding cache (npz + manifest, no ChromaDB), hybrid retriever (RRF + graph expansion), QA with citations
- [x] Ingestion: web (trafilatura + atomic Zettelkasten extraction), YouTube transcripts, paper-summary mode (structured format), Apple Notes documented as plugin-based v1
- [x] Publish: 3-pass blog drafting (draft -> rules edit -> clarity edit), hard-rule validator, Vercel deploy hook, Medium draft publisher (legacy API + paste fallback)
- [x] Agents: tool registry (search/ask/read/graph/memory/ingest/draft/publish/medium), LM Studio tool loop
- [x] Memory: vault-backed Memory/ notes via remember/recall
- [x] Tests: 24 passing (vault, chunker, graph, retriever incl. incremental re-embed, blog validator)
- [x] Frontend shell: Vite + React 19 + TanStack Query, tab shell wired to /health
- [x] Self-documenter agent + ADR template; guidelines artifact published for reuse

## 2. Make it run end-to-end
- [ ] Install LM Studio models: Gemma 3 chat + an embedding model; verify /index/refresh and /ask against the real vault
- [ ] Create the working vault at ~/loc/vault (outside iCloud) and set KP_VAULT_PATH
- [ ] First real ingestion: 3-5 web sources + 1 paper via /ingest/url
- [x] Bulk ingestion: crawl a hub/index page and ingest every linked resource (/ingest/crawl, `crawl_resources` agent tool)
- [ ] Apple Notes bulk import via Obsidian Importer plugin
- [ ] npm install + verify frontend shell against running backend

## 3. Frontend build-out
- [ ] Ask panel with streaming answer + citation pills
- [ ] Search view with score breakdown (vector/bm25/graph)
- [ ] Graph view of wikilink neighborhood
- [x] Ingest dashboard: single-URL + hub-crawl forms with per-link results (note preview before write still TODO)
- [ ] Blog manager (list, violations, publish button, deploy status)
- [ ] Settings panel

## 4. Blog
- [ ] Instantiate nextjs-obsidian-blog-kit, point at blog/posts/, link Vercel + deploy hook
- [ ] First draft through the 3-pass pipeline; tune blog/RULES.md
- [ ] Medium token (KP_MEDIUM_TOKEN) or confirm paste-fallback flow

## 5. Hardening & docs
- [ ] Retrieval quality golden set (question -> expected note) as pytest marker
- [ ] Agent-loop integration test with mocked OpenAI-compatible server (respx)
- [ ] Push to GitHub; enable .github/workflows/doc-sync.yml (durable daily doc sync; local cron is session-bound and expires in 7 days)
- [ ] Apple Notes v2: Python incremental importer (only if scheduled sync proves needed)
