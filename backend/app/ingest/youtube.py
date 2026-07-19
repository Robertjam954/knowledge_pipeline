"""YouTube ingestion: video URL/id -> transcript -> Research/ note."""
from __future__ import annotations

import re

from app.core.config import settings
from app.vault import write_note

VIDEO_ID_RE = re.compile(r"(?:v=|youtu\.be/|shorts/)([\w-]{11})")


def video_id(url_or_id: str) -> str:
    m = VIDEO_ID_RE.search(url_or_id)
    if m:
        return m.group(1)
    if re.fullmatch(r"[\w-]{11}", url_or_id):
        return url_or_id
    raise ValueError(f"could not parse a YouTube video id from {url_or_id!r}")


async def ingest_youtube(url_or_id: str, tags: list[str] | None = None) -> dict:
    from youtube_transcript_api import YouTubeTranscriptApi

    vid = video_id(url_or_id)
    segments = YouTubeTranscriptApi().fetch(vid)
    text = "\n".join(s.text for s in segments)
    if not text.strip():
        raise ValueError(f"empty transcript for {vid}")
    url = f"https://www.youtube.com/watch?v={vid}"
    path = write_note(
        settings.vault_path, settings.research_folder, f"YouTube {vid}", text,
        meta={"source_url": url, "type": "youtube-transcript", "tags": tags or []},
    )
    return {"url": url, "notes": [str(path)]}
