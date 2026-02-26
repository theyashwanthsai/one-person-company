"""Tool: ingest_youtube_knowledge
Fetch YouTube transcript + metadata and persist full content into the markdown knowledge base.
"""

from __future__ import annotations

import re
from typing import Iterable, List, Optional
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
                },
                "language": {
                    "type": "string",
                    "description": "Preferred transcript language code (default: en)."
                }
            },
            "required": ["url"]
        },
    },
}


def _extract_video_id(url):
    """Extract video ID from various YouTube URL formats."""
    if "youtu.be" in url:
        return url.split("youtu.be/")[1].split("?")[0]
    parsed = urlparse(url)
    if "youtube.com" in parsed.netloc:
        return parse_qs(parsed.query).get("v", [None])[0]
    return None

def _fetch_title(url: str, video_id: str) -> str:
    print(f"Fetching title for video ID: {video_id}")
    
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
                print(f"Successfully fetched title: {title}")
                return title
        else:
            print(f"Failed to fetch title, status code: {response.status_code}")
    except Exception as e:
        print(f"Exception while fetching title: {e}")
    
    fallback_title = f"YouTube Video {video_id}"
    print(f"Using fallback title: {fallback_title}")
    return fallback_title


def _fetch_transcript(url: str, language: str = "en"):
    """Fetch transcript for a YouTube video."""
    video_id = _extract_video_id(url)

    if not video_id:
        raise ValueError("Could not extract video ID from URL.")

    print(f"Fetching transcript for video ID: {video_id}\n")

    ytt_api = YouTubeTranscriptApi()
    fetched = ytt_api.fetch(video_id, languages=[language])

    return video_id, fetched 

def _format_transcript(lines: Iterable[object], include_timestamps: bool = True) -> str:
    print(f"Formatting transcript with timestamps: {include_timestamps}")
    
    out = []
    for item in lines:
        if isinstance(item, dict):
            text = (item.get("text") or "").replace("\n", " ").strip()
            start = float(item.get("start", 0.0))
        else:
            text = (getattr(item, "text", "") or "").replace("\n", " ").strip()
            start = float(getattr(item, "start", 0.0))
        if not text:
            continue
        if include_timestamps:
            mm = int(start // 60)
            ss = int(start % 60)
            out.append(f"[{mm:02d}:{ss:02d}] {text}")
        else:
            out.append(text)
    
    formatted_text = "\n".join(out)
    print(f"Formatted transcript: {len(out)} lines, {len(formatted_text)} characters")
    return formatted_text


def execute(agent_id: str, **kwargs):
    print(f"Starting YouTube knowledge ingestion for agent: {agent_id}")
    print(f"Parameters: {kwargs}")
    
    url = (kwargs.get("url") or "").strip()
    tags = kwargs.get("tags") or []
    folder = (kwargs.get("folder") or "sources/youtube").strip()
    language = (kwargs.get("language") or "en").strip() or "en"
    
    if not url:
        print("Error: No URL provided")
        return "Error: url is required."

    try:
        video_id, transcript_lines = _fetch_transcript(url=url, language=language)
    except Exception as exc:
        print(f"Failed to fetch transcript: {exc}")
        return f"Error fetching transcript: {exc}"

    transcript_text = _format_transcript(transcript_lines)
    if not transcript_text.strip():
        print(f"No transcript content found for video_id: {video_id}")
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
    
    print(f"Writing markdown note with title: {title}")
    print(f"Note will be saved to folder: {folder}")
    print(f"Tags: {['youtube', 'knowledge', *tags]}")
    
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
    
    success_message = (
        f"Stored YouTube knowledge note.\n"
        f"- title: {title}\n"
        f"- video_id: {video_id}\n"
        f"- path: {result['path']}"
    )
    print(f"Successfully completed ingestion: {success_message}")
    return success_message
