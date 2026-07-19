"""In-memory wikilink graph over the vault. No graph database - adjacency is
rebuilt from markdown on demand and lives for the process lifetime.
"""
from __future__ import annotations

from collections import defaultdict

from app.vault import Note


class VaultGraph:
    def __init__(self) -> None:
        self._adj: dict[str, set[str]] = defaultdict(set)

    @classmethod
    def build(cls, notes: list[Note]) -> "VaultGraph":
        g = cls()
        titles = {n.title for n in notes}
        for n in notes:
            for target in n.links:
                target = target.strip()
                # Obsidian links may include a path; the last segment is the note title
                target_title = target.split("/")[-1]
                if target_title in titles:
                    g._adj[n.title].add(target_title)
                    g._adj[target_title].add(n.title)  # treat links as undirected for retrieval
        return g

    def neighbors(self, title: str, hops: int = 1) -> set[str]:
        seen: set[str] = {title}
        frontier = {title}
        for _ in range(max(0, hops)):
            nxt: set[str] = set()
            for t in frontier:
                nxt |= self._adj.get(t, set())
            frontier = nxt - seen
            seen |= frontier
        seen.discard(title)
        return seen

    def degree(self, title: str) -> int:
        return len(self._adj.get(title, ()))
