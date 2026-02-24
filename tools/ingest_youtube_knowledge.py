"""Tool: ingest_youtube_knowledge
Fetch YouTube transcript + metadata and persist full content into the markdown knowledge base.
"""

from __future__ import annotations

import re
from typing import List, Optional
from urllib.parse import parse_qs, urlparse

import requests
from youtube_transcript_api import YouTubeTranscriptApi

from lib.knowledge_base import write_markdown_note


SCHEMA = {
    "type": "function",
    "function": {
        "name": "ingest_youtube_knowledge",
        "description": "Ingest a YouTube video's full transcript into the markdown knowledge base.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "YouTube video URL."
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional tags for the knowledge note."
                },
                "folder": {
                    "type": "string",
                    "description": "Optional vault subfolder. Default: sources/youtube"
                }
            },
            "required": ["url"]
        },
    },
}


def _extract_video_id(url: str) -> Optional[str]:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if "youtu.be" in host:
        return parsed.path.strip("/").split("/")[0]
    if "youtube.com" in host:
        qs = parse_qs(parsed.query)
        if "v" in qs and qs["v"]:
            return qs["v"][0]
        # /shorts/<id> or /embed/<id>
        m = re.search(r"/(shorts|embed)/([a-zA-Z0-9_-]{6,})", parsed.path)
        if m:
            return m.group(2)
    return None


def _fetch_title(url: str, video_id: str) -> str:
    try:
        response = requests.get(
            "https://www.youtube.com/oembed",
            params={"url": url, "format": "json"},
            timeout=15,
        )
        if response.status_code < 400:
            data = response.json()
            title = (data.get("title") or "").strip()
            if title:
                return title
    except Exception:
        pass
    return f"YouTube Video {video_id}"


def _format_transcript(lines: List[dict]) -> str:
    out = []
    for item in lines:
        text = (item.get("text") or "").replace("\n", " ").strip()
        if not text:
            continue
        start = float(item.get("start", 0.0))
        mm = int(start // 60)
        ss = int(start % 60)
        out.append(f"[{mm:02d}:{ss:02d}] {text}")
    return "\n".join(out)


def execute(agent_id: str, **kwargs):
    url = (kwargs.get("url") or "").strip()
    tags = kwargs.get("tags") or []
    folder = (kwargs.get("folder") or "sources/youtube").strip()
    if not url:
        return "Error: url is required."

    video_id = _extract_video_id(url)
    if not video_id:
        return "Error: Could not parse YouTube video id from URL."

    try:
        transcript_lines = YouTubeTranscriptApi.get_transcript(video_id)
    except Exception as exc:
        return f"Error fetching transcript for video_id={video_id}: {exc}"

    transcript_text = _format_transcript(transcript_lines)
    if not transcript_text.strip():
        return f"No transcript lines found for video_id={video_id}."

    title = _fetch_title(url, video_id)
    body = (
        f"## Source\n"
        f"- URL: {url}\n"
        f"- Video ID: {video_id}\n"
        f"- Captured By: {agent_id}\n\n"
        f"## Full Transcript\n\n"
        f"{transcript_text}\n"
    )

    result = write_markdown_note(
        title=title,
        body=body,
        folder=folder,
        tags=["youtube", "knowledge", *tags],
        source_url=url,
        note_type="source_youtube",
        aliases=[video_id],
        filename_hint=title,
    )
    return (
        f"Stored YouTube knowledge note.\n"
        f"- title: {title}\n"
        f"- video_id: {video_id}\n"
        f"- path: {result['path']}"
    )

