"""Central settings. Everything configurable lives here; env vars use the KP_ prefix
(e.g. KP_VAULT_PATH). The vault is the only source of truth - cache_dir holds only
rebuildable derived data (embeddings, manifests).
"""
from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="KP_", extra="ignore")

    # Stores (all local; no database anywhere)
    vault_path: Path = Path.home() / "loc" / "vault"
    cache_dir: Path = PROJECT_ROOT / ".cache"
    blog_posts_dir: Path = PROJECT_ROOT / "blog" / "posts"
    blog_rules_path: Path = PROJECT_ROOT / "blog" / "RULES.md"

    # Local models via LM Studio's OpenAI-compatible server
    lmstudio_base_url: str = "http://localhost:1234/v1"
    lmstudio_api_key: str = "lm-studio"  # LM Studio ignores the value but the client requires one
    chat_model: str = "gemma-3-270m-it-qat"
    embed_model: str = "text-embedding-nomic-embed-text-v1.5-embedding"

    # Optional Claude for drafting/extraction quality (pipeline model per user standard)
    llm_provider: str = "lmstudio"  # "lmstudio" | "anthropic"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-5"

    # Retrieval
    chunk_chars: int = 1000
    chunk_overlap_chars: int = 100
    # Max chars of page text sent to the chat model for extraction/summary; keep well
    # under the model's context window (a 270M/4096-token model overflows past ~16k chars).
    ingest_max_chars: int = 12000
    top_k: int = 8
    vector_weight: float = 0.6  # BM25 gets the remainder
    graph_expansion: bool = True
    graph_neighbor_discount: float = 0.5

    # Vault layout
    research_folder: str = "Research"
    zettel_folder: str = "Zettelkasten"
    memory_folder: str = "Memory"

    # Publishing
    vercel_deploy_hook_url: str = ""
    medium_token: str = ""  # legacy Medium integration token; drafts only
    auto_git_publish: bool = False  # when true, publish_post commits + pushes the blog repo

    max_agent_steps: int = 6


settings = Settings()
