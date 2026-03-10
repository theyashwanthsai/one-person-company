"""
Tool: send_daily_scan_digest

Summarize Thea's recent scan notes (knowledgebase/thea) into a single daily
digest message and send it to Discord #mails.
"""

import os
import re
from datetime import datetime, timedelta, timezone
from typing import List, Tuple

from dotenv import load_dotenv

from lib.knowledge_base import get_kb_root
from lib.discord.client import DiscordClient

load_dotenv()


SCHEMA = {
    "type": "function",
    "function": {
        "name": "send_daily_scan_digest",
        "description": "Summarize Thea's recent scan notes into a daily digest and send it to Discord #mails.",
        "parameters": {
            "type": "object",
            "properties": {
                "hours": {
                    "type": "integer",
                    "description": "Look back this many hours for thea notes. Default: 24",
                },
                "max_posts": {
                    "type": "integer",
                    "description": "Maximum number of posts/links to include. Default: 10",
                },
                "dry_run": {
                    "type": "boolean",
                    "description": "If true, don't send to Discord, just return the digest text.",
                },
            },
            "required": [],
        },
    },
}


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _list_recent_thea_notes(hours: int) -> List[str]:
    kb_root = get_kb_root()
    dir_path = kb_root / "thea"
    if not dir_path.is_dir():
        return []

    cutoff = _now_utc() - timedelta(hours=max(1, int(hours or 24)))
    items: List[Tuple[datetime, str]] = []
    for path in dir_path.glob("*.md"):
        try:
            mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        except Exception:
            continue
        if mtime >= cutoff:
            items.append((mtime, str(path)))
    items.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in items]


def _extract_sections(note_text: str) -> List[Tuple[str, str]]:
    """
    Extract (title, url) pairs from a thea note.
    Supports headings like:
      #### Hot take...
      - [Link](...)
    """
    sections: List[Tuple[str, str]] = []
    lines = note_text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not (line.startswith("### ") or line.startswith("#### ")):
            i += 1
            continue
        title = line.replace("### ", "", 1).replace("#### ", "", 1).strip()
        url = ""
        i += 1
        while i < len(lines):
            cur = lines[i].strip()
            if cur.startswith("### ") or cur.startswith("#### "):
                break
            m = re.search(r"\[Link\]\((https?://[^)]+)\)", cur)
            if m and not url:
                url = m.group(1).strip()
            i += 1
        if title and url:
            sections.append((title, url))
    return sections


def _build_digest(hours: int, max_posts: int) -> Tuple[str, int]:
    paths = _list_recent_thea_notes(hours)
    if not paths:
        return f"No thea notes found in the last {hours}h.", 0

    seen_urls = set()
    entries: List[Tuple[str, str]] = []

    for path in paths:
        try:
            text = open(path, "r", encoding="utf-8").read()
        except Exception:
            continue
        for title, url in _extract_sections(text):
            if url in seen_urls:
                continue
            seen_urls.add(url)
            entries.append((title, url))
            if len(entries) >= max_posts:
                break
        if len(entries) >= max_posts:
            break

    if not entries:
        return f"No per-post sections with links found in thea notes in the last {hours}h.", 0

    header = f"Daily scan digest (last {hours}h)\n\nThese are the most interesting discussions Thea found today:"
    lines = [header]
    for idx, (title, url) in enumerate(entries, start=1):
        lines.append(f"{idx}. **{title}**\n   {url}")
    return "\n\n".join(lines), len(entries)


def execute(agent_id: str, **kwargs) -> str:
    hours = int(kwargs.get("hours", 24) or 24)
    max_posts = int(kwargs.get("max_posts", 10) or 10)
    dry_run = bool(kwargs.get("dry_run", False))

    digest, count = _build_digest(hours=hours, max_posts=max_posts)
    if dry_run:
        return f"(dry_run) Digest would include {count} posts:\n\n{digest}"

    if count == 0:
        return digest

    try:
        client = DiscordClient()
    except Exception as exc:
        return f"Discord not configured: {exc}\n\n{digest}"

    ok = client.send_to_ceo(
        agent_id=agent_id,
        subject="Daily scan digest",
        message=digest,
        urgency="medium",
        channel="mails",
    )
    if ok:
        return f"Sent daily scan digest to #mails with {count} posts."
    return f"Failed to send daily scan digest to #mails.\n\n{digest}"

