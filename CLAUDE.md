# Knowledge Pipeline

Local-first personal knowledge system: extract from web sources and Apple Notes into an Obsidian vault, ask questions over it with local AI (LM Studio + Gemma), and turn notes into artifacts.

## Quick Facts
- **Type**: Full-stack app (FastAPI backend + React frontend), local-first
- **Backend**: Python >= 3.11, package `knowledge-pipeline` (`uv`, `backend/pyproject.toml`)
- **Frontend**: React (`frontend/`, scripts: `dev`, `build`, `preview`)
- **AI**: local via LM Studio + Gemma (no cloud key required by default)

## Commands
- Backend deps: `cd backend && uv sync` · run: `uv run fastapi dev` (see `backend/`)
- Frontend: `cd frontend && npm install && npm run dev`
- Build frontend: `npm run build`

## Key Directories
- `backend/` - FastAPI service + extraction/RAG logic
- `frontend/` - React UI
- `blog/`, `site/` - published content (GitHub Pages)
- `docs/` - project docs · `STATUS.md` - rolls up to the portfolio board

## Working Rules
- **Local-first**: do not add cloud dependencies or send personal notes to external services without explicit intent.
- **Structure**: this is an AI app - keep it aligned with the `agentic-ai-app-template` layout.
- **Prose**: single hyphen (-), never em dashes.
- **Workflow**: follow `context-engineering-workflow` (curate context -> plan -> implement).
- **Models**: LLM/pipeline work defaults to local (LM Studio + Gemma); for hosted Claude use `claude-sonnet-5`.
- A `settings.json` hook blocks edits on `main`/`master` - branch first.
