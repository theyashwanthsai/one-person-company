"""Tool: ingest_youtube_knowledge
Fetch YouTube transcript + metadata and persist full content into the markdown knowledge base.
"""

from __future__ import annotations

import re
from typing import Iterable, List, Optional
from urllib.parse import parse_qs, urlparse

import requests
import youtube_transcript_api as yta
from youtube_transcript_api import YouTubeTranscriptApi

from lib.knowledge_base import write_markdown_note


_TRANSCRIPT_EXCEPTIONS = tuple(
    exc
    for exc in (
        getattr(yta, "NoTranscriptAvailable", None),
        getattr(yta, "NoTranscriptFound", None),
        getattr(yta, "TranscriptsDisabled", None),
        getattr(yta, "CouldNotRetrieveTranscript", None),
    )
    if isinstance(exc, type) and issubclass(exc, Exception)
) or (Exception,)


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


def _extract_video_id(url: str) -> Optional[str]:
    """Extract video ID from common YouTube URL formats."""
    print(f"Extracting video ID from URL: {url}")
    
    if "youtu.be" in url:
        video_id = url.split("youtu.be/")[1].split("?")[0]
        print(f"Extracted video ID from youtu.be format: {video_id}")
        return video_id

    parsed = urlparse(url)
    if "youtube.com" in parsed.netloc:
        video_id = parse_qs(parsed.query).get("v", [None])[0]
        if video_id:
            print(f"Extracted video ID from youtube.com query param: {video_id}")
            return video_id
        # Keep support for /shorts/<id> and /embed/<id> URLs.
        match = re.search(r"/(shorts|embed)/([a-zA-Z0-9_-]{6,})", parsed.path)
        if match:
            video_id = match.group(2)
            print(f"Extracted video ID from {match.group(1)} format: {video_id}")
            return video_id
    
    print("Could not extract video ID from URL")
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


def _language_candidates(language: str) -> List[str]:
    base = (language or "en").strip() or "en"
    candidates = [base]
    if base.lower() != "en":
        candidates.extend(["en", "en-US", "en-GB"])
    else:
        candidates.extend(["en-US", "en-GB"])
    # preserve order and remove duplicates
    seen = set()
    ordered = []
    for lang in candidates:
        key = lang.lower()
        if key not in seen:
            seen.add(key)
            ordered.append(lang)
    
    print(f"Language candidates for '{language}': {ordered}")
    return ordered


def _fetch_transcript(url: str, language: str = "en"):
    """Fetch transcript across youtube_transcript_api versions with fallbacks."""
    print(f"Fetching transcript for URL: {url}, language: {language}")

    video_id = _extract_video_id(url)
    if not video_id:
        raise ValueError("Could not extract video ID from URL.")

    languages = _language_candidates(language)
    ytt_api = YouTubeTranscriptApi()

    # Attempt A: instance-level v1.0+ API (preferred)
    print("Attempting instance-level fetch() API (v1.0+)...")
    if hasattr(ytt_api, "fetch"):
        try:
            lines = list(ytt_api.fetch(video_id, languages=languages))
            print(f"Successfully fetched transcript using instance.fetch(), {len(lines)} entries")
            return video_id, lines
        except _TRANSCRIPT_EXCEPTIONS as e:
            print(f"instance.fetch() failed with transcript error: {e}")
        except Exception as e:
            print(f"instance.fetch() failed unexpectedly: {e}")

    # Attempt B: class-level v0 static API
    print("Attempting class-level get_transcript() API (v0)...")
    if hasattr(YouTubeTranscriptApi, "get_transcript"):
        try:
            lines = list(YouTubeTranscriptApi.get_transcript(video_id, languages=languages))
            print(f"Successfully fetched transcript using class-level API, {len(lines)} entries")
            return video_id, lines
        except _TRANSCRIPT_EXCEPTIONS as e:
            print(f"Class-level get_transcript() failed: {e}")
        except Exception as e:
            print(f"Class-level get_transcript() failed unexpectedly: {e}")

    # Attempt C: transcript-list fallback (manual → generated → any → translatable)
    # NOTE: Do NOT call list(transcript_list) before find_* methods — it exhausts the iterator.
    print("Attempting transcript-list fallback...")
    try:
        transcript = None

        # 1. Try preferred languages directly
        print("Trying find_transcript() in preferred languages...")
        try:
            transcript_list = ytt_api.list_transcripts(video_id)
            transcript = transcript_list.find_transcript(languages)
            print(f"Found transcript via find_transcript(): {transcript.language_code}")
        except Exception as e:
            print(f"find_transcript() failed: {e}")

        # 2. Try manually-created transcripts
        if transcript is None:
            print("Trying find_manually_created_transcript()...")
            try:
                transcript_list = ytt_api.list_transcripts(video_id)
                transcript = transcript_list.find_manually_created_transcript(languages)
                print(f"Found manually created transcript: {transcript.language_code}")
            except Exception as e:
                print(f"find_manually_created_transcript() failed: {e}")

        # 3. Try auto-generated transcripts
        if transcript is None:
            print("Trying find_generated_transcript()...")
            try:
                transcript_list = ytt_api.list_transcripts(video_id)
                transcript = transcript_list.find_generated_transcript(languages)
                print(f"Found generated transcript: {transcript.language_code}")
            except Exception as e:
                print(f"find_generated_transcript() failed: {e}")

        # 4. Accept any available transcript (first one wins)
        if transcript is None:
            print("Trying any available transcript...")
            try:
                transcript_list = ytt_api.list_transcripts(video_id)
                for t in transcript_list:
                    transcript = t
                    print(f"Using first available transcript: {t.language_code}")
                    break
            except Exception as e:
                print(f"Could not iterate transcript list: {e}")

        # 5. Translate as a last resort
        if transcript is None:
            print("No direct transcript found; trying translatable fallback...")
            try:
                transcript_list = ytt_api.list_transcripts(video_id)
                for t in transcript_list:
                    if getattr(t, "is_translatable", False):
                        try:
                            transcript = t.translate(languages[0])
                            print(f"Translated transcript to {languages[0]}")
                            break
                        except Exception as te:
                            print(f"Translation failed: {te}")
            except Exception as e:
                print(f"Translatable fallback failed: {e}")

        if transcript is None:
            raise RuntimeError("No matching or translatable transcript was found.")

        lines = list(transcript.fetch())
        print(f"Successfully fetched transcript via list fallback, {len(lines)} entries")
        return video_id, lines

    except RuntimeError:
        raise
    except Exception as exc:
        print(f"All transcript fetch attempts failed: {exc}")
        raise RuntimeError(
            f"No usable transcript found for video_id={video_id} "
            f"(requested={languages}). Root cause: {exc}"
        ) from exc

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
