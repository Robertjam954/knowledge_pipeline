from app.publish.blog_export import validate_post

GOOD = """---
date: 2026-07-17
published: false
tags: [rag]
slug: local-rag-notes
sources:
  - Zettelkasten/2026-07-10 embedding caches.md
---
Opening paragraph that stands alone as a description.

## Section

```python
print("hi")
```
"""


def test_valid_post_passes():
    assert validate_post(GOOD) == []


def test_missing_frontmatter():
    assert validate_post("no frontmatter body") == ["missing YAML frontmatter"]


def test_published_true_rejected():
    bad = GOOD.replace("published: false", "published: true")
    assert "published must be false on creation" in validate_post(bad)


def test_bad_date_and_slug():
    bad = GOOD.replace("2026-07-17", "July 17").replace("local-rag-notes", "Not A Slug!")
    v = validate_post(bad)
    assert any("date" in x for x in v) and any("slug" in x for x in v)


def test_wikilink_and_emdash_and_bare_fence():
    bad = GOOD.replace("Opening paragraph", "See [[Other Note]] - em dash — here. Opening")
    bad = bad.replace("```python", "```")
    v = validate_post(bad)
    assert "unresolved [[wikilinks]] in body" in v
    assert "em/en dashes present; use hyphens" in v
    assert "code fence without language tag" in v


def test_memory_source_rejected():
    bad = GOOD.replace("Zettelkasten/2026-07-10 embedding caches.md", "Memory/some memory.md")
    assert any("memory note" in x for x in validate_post(bad))
