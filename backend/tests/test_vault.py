from app.vault import compose_note, parse_frontmatter, parse_note, safe_filename, write_note
from pathlib import Path


def test_frontmatter_roundtrip():
    meta = {"date": "2026-07-17", "tags": ["a", "b"], "published": False}
    text = compose_note(meta, "Body here.")
    parsed_meta, body = parse_frontmatter(text)
    assert parsed_meta == meta
    assert body.strip() == "Body here."


def test_no_frontmatter():
    meta, body = parse_frontmatter("Just text.")
    assert meta == {} and body == "Just text."


def test_parse_note_links_and_tags(tmp_path: Path):
    p = tmp_path / "My Note.md"
    text = "---\ntags: [ai]\n---\nSee [[Other Note]] and [[Third|alias]] about #rag stuff."
    p.write_text(text)
    from app.vault import read_note

    n = read_note(p)
    assert n.title == "My Note"
    assert n.links == ["Other Note", "Third"]
    assert n.tags == ["ai", "rag"]


def test_write_note_collision_and_sanitize(tmp_path: Path):
    p1 = write_note(tmp_path, "Zettel", 'bad/name: "quoted"', "one", date_prefix=False)
    p2 = write_note(tmp_path, "Zettel", 'bad/name: "quoted"', "two", date_prefix=False)
    assert p1.exists() and p2.exists() and p1 != p2
    assert "/" not in p1.stem and '"' not in p1.name


def test_safe_filename_empty():
    assert safe_filename("###") == "untitled"
