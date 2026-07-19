from pathlib import Path

from app.rag.graph import VaultGraph
from app.vault import Note


def n(title: str, links: list[str]) -> Note:
    return Note(path=Path(f"/x/{title}.md"), title=title, links=links)


def test_undirected_adjacency():
    g = VaultGraph.build([n("A", ["B"]), n("B", []), n("C", ["A"])])
    assert g.neighbors("A") == {"B", "C"}
    assert g.neighbors("B") == {"A"}


def test_two_hops():
    g = VaultGraph.build([n("A", ["B"]), n("B", ["C"]), n("C", ["D"]), n("D", [])])
    assert g.neighbors("A", hops=2) == {"B", "C"}


def test_link_to_missing_note_ignored():
    g = VaultGraph.build([n("A", ["Ghost"]), n("B", [])])
    assert g.neighbors("A") == set()


def test_path_style_links_resolve_to_title():
    g = VaultGraph.build([n("A", ["Folder/B"]), n("B", [])])
    assert g.neighbors("A") == {"B"}
