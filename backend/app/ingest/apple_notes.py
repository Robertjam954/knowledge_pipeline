"""Apple Notes ingestion.

v1 (current): bulk import via the Obsidian Importer plugin - zero code, handles the
full format (attachments, tables, links). Open Obsidian -> Importer -> Apple Notes,
point it at ~/Library/Group Containers/group.com.apple.notes, output into the vault.

v2 (only if scheduled/incremental sync is needed): port the plugin's recipe to Python -
read NoteStore.sqlite, decode hex + zlib + protobuf note payloads
(ciofecaforensics.Document), convert timestamps with the +978307200s Core Time offset,
and apply skip-if-not-newer dedup. See the importer template's
src/formats/apple-notes/ for the reference implementation.
"""
from __future__ import annotations

APPLE_NOTES_DB = "~/Library/Group Containers/group.com.apple.notes/NoteStore.sqlite"


async def ingest_apple_notes() -> dict:
    raise NotImplementedError(
        "Programmatic Apple Notes import is deferred (v2). For now run the Obsidian "
        f"Importer plugin against {APPLE_NOTES_DB} - see this module's docstring."
    )
