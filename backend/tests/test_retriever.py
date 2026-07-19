import pytest

from app.rag.retriever import HybridRetriever
from tests.conftest import fake_embed, make_note


@pytest.fixture()
async def indexed(vault):
    make_note(vault, "Zettelkasten", "Embedding Cache",
              "Embeddings live in a numpy npz cache keyed by chunk sha. See [[Hybrid Retrieval]].")
    make_note(vault, "Zettelkasten", "Hybrid Retrieval",
              "Hybrid retrieval fuses cosine vector scores with BM25 keyword scores.")
    make_note(vault, "Research", "Sourdough Starter",
              "Feed the sourdough starter flour and water twice daily.")
    make_note(vault, "Memory", "Private Thing", "---\nprivate: true\n---\nsecret content")
    r = HybridRetriever(embed=fake_embed)
    await r.refresh()
    return r


async def test_relevant_note_ranks_first(indexed):
    hits = await indexed.search("how does hybrid retrieval fuse bm25 and vector scores", k=3)
    assert hits, "expected hits"
    assert hits[0].note_title == "Hybrid Retrieval"


async def test_graph_expansion_pulls_linked_note(indexed):
    hits = await indexed.search("numpy npz embeddings cache chunk sha", k=1)
    assert hits[0].note_title == "Embedding Cache"
    assert any(h.via == "graph" and h.note_title == "Hybrid Retrieval" for h in hits)


async def test_private_notes_excluded(indexed):
    hits = await indexed.search("secret content private thing", k=5)
    assert all(h.note_title != "Private Thing" for h in hits)


async def test_folder_filter(indexed):
    hits = await indexed.search("feed the starter flour water", k=5, folder="Zettelkasten")
    assert all("Zettelkasten" in h.note_path for h in hits)


async def test_incremental_sync_reuses_vectors(indexed, vault):
    calls = []

    async def counting_embed(texts):
        calls.append(len(texts))
        return await fake_embed(texts)

    indexed._embed = counting_embed
    await indexed.refresh()  # nothing changed except the query-free resync
    assert sum(calls) == 0, "unchanged chunks must not re-embed"
    make_note(vault, "Zettelkasten", "New Note", "Fresh content about rank fusion.")
    await indexed.refresh()
    assert sum(calls) >= 1
