"""Tests for hub-page link extraction and multi-resource crawl (no network, no LLM)."""
from __future__ import annotations

from app.ingest import web

HUB_HTML = """
<html><body>
  <header><a href="/login">Sign in</a></header>
  <main>
    <a href="/en-us/azure/architecture/ai-ml/guide/rag">Design a RAG solution</a>
    <a href="guide/mlops">MLOps guide</a>
    <a href="guide/rag#section">Design a RAG solution</a>  <!-- dup after fragment strip -->
    <a href="/_images/diagram.svg">diagram</a>              <!-- asset, skipped -->
    <a href="https://external.example.com/thing">Offsite</a> <!-- other domain -->
    <a href="#top">Back to top</a>                          <!-- fragment, skipped -->
    <a href="mailto:x@y.com">mail</a>                        <!-- scheme, skipped -->
    <a href="/en-us/azure/architecture/ai-ml/ai-get-started">Self link</a> <!-- hub itself -->
  </main>
  <footer><a href="/legal/privacy">Privacy</a></footer>
</body></html>
"""

BASE = "https://learn.microsoft.com/en-us/azure/architecture/ai-ml/ai-get-started"


def test_extract_links_same_domain_dedup_and_filtering():
    links = web.extract_links(HUB_HTML, BASE, same_domain=True)
    urls = [l["url"] for l in links]
    # only in-content, same-domain, non-asset, non-fragment, non-self links, de-duplicated
    assert urls == [
        "https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/rag",
        "https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/mlops",
    ]
    assert links[0]["text"] == "Design a RAG solution"


def test_extract_links_path_filter_and_cross_domain():
    links = web.extract_links(HUB_HTML, BASE, same_domain=False, path_contains="/architecture/")
    urls = [l["url"] for l in links]
    assert "https://external.example.com/thing" not in urls  # filtered by path_contains
    assert all("/architecture/" in u for u in urls)


def test_extract_links_falls_back_to_whole_doc_without_main():
    html = '<html><body><a href="/en-us/azure/architecture/x">X</a></body></html>'
    links = web.extract_links(html, BASE)
    assert [l["url"] for l in links] == ["https://learn.microsoft.com/en-us/azure/architecture/x"]


async def test_crawl_resources_ingests_each_link(monkeypatch):
    async def fake_fetch_html(url):
        return HUB_HTML

    ingested: list[str] = []

    async def fake_ingest_url(url, mode="article", atomic=True, tags=None):
        ingested.append(url)
        return {"url": url, "title": url.rsplit("/", 1)[-1], "mode": mode,
                "notes": [f"{url}#note"]}

    monkeypatch.setattr(web, "fetch_html", fake_fetch_html)
    monkeypatch.setattr(web, "ingest_url", fake_ingest_url)

    result = await web.crawl_resources(BASE, atomic=False)
    assert result["found"] == 2
    assert result["ingested"] == 2
    assert result["failed"] == 0
    assert len(result["notes"]) == 2
    assert len(ingested) == 2
    assert all(r["status"] == "ok" for r in result["results"])


async def test_crawl_resources_limit_and_error_isolation(monkeypatch):
    async def fake_fetch_html(url):
        return HUB_HTML

    async def flaky_ingest_url(url, mode="article", atomic=True, tags=None):
        if url.endswith("rag"):
            raise ValueError("no extractable text")
        return {"url": url, "title": "ok", "mode": mode, "notes": [f"{url}#n"]}

    monkeypatch.setattr(web, "fetch_html", fake_fetch_html)
    monkeypatch.setattr(web, "ingest_url", flaky_ingest_url)

    result = await web.crawl_resources(BASE, atomic=False, limit=5)
    assert result["found"] == 2
    assert result["ingested"] == 1
    assert result["failed"] == 1
    errored = [r for r in result["results"] if r["status"] == "error"]
    assert errored and "no extractable text" in errored[0]["error"]

    limited = await web.crawl_resources(BASE, atomic=False, limit=1)
    assert limited["found"] == 1
