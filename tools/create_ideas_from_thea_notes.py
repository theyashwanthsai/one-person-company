"""
Tool: create_ideas_from_thea_notes

Reads Thea's scan notes from the knowledge base and converts each per-post section
into a content idea stored in the Supabase content_pipeline table.
"""

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable, List, Optional, Tuple

from lib.knowledge_base import get_kb_root
from lib.llm import chat_completion_json
from lib.supabase_client import get_supabase


SCHEMA = {
    "type": "function",
    "function": {
        "name": "create_ideas_from_thea_notes",
        "description": "Read knowledgebase/thea scan notes and create content_pipeline ideas (1 idea per post section).",
        "parameters": {
            "type": "object",
            "properties": {
                "folder": {
                    "type": "string",
                    "description": "Knowledgebase folder to read from. Default: thea",
                },
                "note_limit": {
                    "type": "integer",
                    "description": "Max number of recent notes to scan. 0 or omitted = all notes within since_hours.",
                },
                "since_hours": {
                    "type": "integer",
                    "description": "Only consider notes modified in the last N hours. Default: 6",
                },
                "max_ideas": {
                    "type": "integer",
                    "description": "Optional cap on ideas created this run. Default: no cap",
                },
                "dry_run": {
                    "type": "boolean",
                    "description": "If true, do not insert into DB; just preview titles. Default: false",
                },
            },
            "required": [],
        },
    },
}


@dataclass
class PostSection:
    note_path: str
    note_title: str
    post_title: str
    url: str
    bullets: List[str]
    why_matters: str
    tags: List[str]


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _parse_frontmatter_title_and_tags(text: str) -> Tuple[str, List[str]]:
    title = ""
    tags: List[str] = []
    if not text.startswith("---"):
        return title, tags
    try:
        end = text.find("\n---", 3)
        if end == -1:
            return title, tags
        fm = text[: end + 4]
        m_title = re.search(r'^\s*title:\s*"(.*)"\s*$', fm, re.MULTILINE)
        if m_title:
            title = m_title.group(1).strip()
        m_tags = re.search(r"^\s*tags:\s*\[(.*)\]\s*$", fm, re.MULTILINE)
        if m_tags:
            raw = m_tags.group(1)
            tags = [t.strip().strip('"').strip("'") for t in raw.split(",") if t.strip()]
    except Exception:
        return title, tags
    return title, tags


def _extract_post_sections(note_path: str, note_text: str) -> List[PostSection]:
    note_title, note_tags = _parse_frontmatter_title_and_tags(note_text)

    # Split on markdown headings for per-post sections.
    # Expected shape:
    # ### <Post title>
    # [Link](url)
    # - bullets...
    # - **Why this matters for us**: ...
    sections: List[PostSection] = []
    lines = note_text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        # Treat both level-3 and level-4 headings as potential per-post sections.
        # This supports patterns like:
        #   ### Reddit Scan Highlights
        #   #### Hot take: ...
        if not (line.startswith("### ") or line.startswith("#### ")):
            i += 1
            continue

        post_title = line.replace("### ", "", 1).replace("#### ", "", 1).strip()
        url = ""
        bullets: List[str] = []
        why_matters = ""

        i += 1
        # Read until next heading or EOF
        while i < len(lines):
            cur = lines[i].strip()
            if cur.startswith("### ") or cur.startswith("#### "):
                break
            link_match = re.search(r"\[Link\]\((https?://[^)]+)\)", cur)
            if link_match and not url:
                url = link_match.group(1).strip()
            if cur.startswith("- "):
                bullet = cur[2:].strip()
                if bullet.lower().startswith("**why this matters for us**"):
                    why_matters = re.sub(r"^\*\*why this matters for us\*\*:\s*", "", bullet, flags=re.I)
                else:
                    bullets.append(bullet)
            i += 1

        if post_title and url:
            sections.append(
                PostSection(
                    note_path=note_path,
                    note_title=note_title or os.path.basename(note_path),
                    post_title=post_title,
                    url=url,
                    bullets=bullets[:8],
                    why_matters=why_matters,
                    tags=note_tags,
                )
            )
        # Don't increment i here; loop continues with current i (either next ### or EOF)
    return sections


def _list_recent_note_paths(folder: str, note_limit: int, since_hours: int) -> List[str]:
    kb_root = get_kb_root()
    dir_path = kb_root / folder.strip("/").strip()
    if not dir_path.is_dir():
        return []

    threshold = _now_utc() - timedelta(hours=max(0, int(since_hours)))
    candidates = []
    for path in dir_path.glob("*.md"):
        try:
            mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        except Exception:
            continue
        if since_hours and mtime < threshold:
            continue
        candidates.append((mtime, path))
    candidates.sort(key=lambda x: x[0], reverse=True)

    # note_limit <= 0 means no cap (use all notes within the time window)
    if note_limit and note_limit > 0:
        candidates = candidates[: int(note_limit)]
    return [str(p) for _, p in candidates]


def _safe_trim(text: str, max_len: int) -> str:
    text = (text or "").strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rstrip() + "..."


def _normalize_tags(tags: Iterable[str]) -> List[str]:
    out: List[str] = []
    for tag in tags or []:
        t = (tag or "").strip()
        if not t:
            continue
        out.append(t.replace(" ", "_"))
    # stable unique
    seen = set()
    uniq: List[str] = []
    for t in out:
        if t not in seen:
            seen.add(t)
            uniq.append(t)
    return uniq[:25]


def _idea_prompt(section: PostSection) -> Tuple[str, str]:
    system = (
        "You are a sharp content strategist. "
        "Turn source notes into one concrete short-form post idea for a personal brand. "
        "Be specific, non-generic, and actionable."
    )

    bullets = "\n".join([f"- {b}" for b in section.bullets]) if section.bullets else "- (no bullets)"
    user = f"""Source post:
- Title: {section.post_title}
- URL: {section.url}
- Note: {section.note_title}

Notes:
{bullets}

Why this matters:
{section.why_matters or "(not provided)"}

Task:
Generate ONE content idea.
Return JSON with keys:
- theme (short, specific, not generic)
- angle (one-line angle / hook direction)
- draft_text (6-12 lines). Must include: Hook, Problem, Answer, and 2 concrete examples or claims.
- tags (array of short tags)
- confidence (number 0.0-1.0)
"""
    return system, user


def _generate_idea_json(section: PostSection) -> dict:
    system, user = _idea_prompt(section)
    raw = chat_completion_json(system=system, user=user, model="gpt-4o-mini")
    try:
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError("Non-object JSON")
    except Exception:
        # Fallback minimal idea if JSON fails
        data = {
            "theme": _safe_trim(section.post_title, 120),
            "angle": _safe_trim(section.why_matters or section.post_title, 140),
            "draft_text": (
                f"Hook: {_safe_trim(section.post_title, 120)}\n"
                "Problem: Teams ship AI demos but can’t operationalize them.\n"
                "Answer: Define success metrics + workflow first, then model.\n"
                "Example: Replace 'better prompts' with 'clear success metrics'.\n"
                f"Source: {section.url}"
            ),
            "tags": [],
            "confidence": 0.6,
        }

    theme = _safe_trim(str(data.get("theme") or section.post_title), 240)
    angle = _safe_trim(str(data.get("angle") or ""), 280)
    draft_text = _safe_trim(str(data.get("draft_text") or ""), 8000)
    tags = data.get("tags") or []
    if not isinstance(tags, list):
        tags = []
    merged_tags = _normalize_tags([*section.tags, *tags, "thea_scan", "idea"])
    confidence = data.get("confidence")
    try:
        confidence = float(confidence)
    except Exception:
        confidence = 0.6
    confidence = max(0.0, min(1.0, confidence))

    return {
        # IMPORTANT: DB schema uses migrations/005_create_content_pipeline.sql
        "status": "idea",
        "platform": "twitter",
        "content_type": "short_form",
        "theme": theme,
        "angle": angle,
        "draft_text": draft_text,
        "approval_notes": f"Source: {section.url}\nNote: {section.note_path}",
        "confidence": round(confidence, 2),
        "draft_metadata": {"tags": merged_tags},
    }


def execute(agent_id: str, **kwargs) -> str:
    folder = (kwargs.get("folder") or "thea").strip() or "thea"
    # 0 or omitted = no cap on number of notes (within since_hours window)
    note_limit = int(kwargs.get("note_limit", 0) or 0)
    since_hours = int(kwargs.get("since_hours", 6))
    max_ideas = kwargs.get("max_ideas")
    dry_run = bool(kwargs.get("dry_run", False))

    paths = _list_recent_note_paths(folder=folder, note_limit=note_limit, since_hours=since_hours)
    if not paths:
        return f"No notes found in knowledgebase/{folder} within the last {since_hours}h."

    all_sections: List[PostSection] = []
    seen_urls: set[str] = set()
    for p in paths:
        try:
            text = open(p, "r", encoding="utf-8").read()
        except Exception:
            continue
        for section in _extract_post_sections(p, text):
            # Deduplicate by URL so we don't create multiple ideas
            # for the same underlying Reddit/HN post across different notes.
            url_key = section.url.strip()
            if not url_key or url_key in seen_urls:
                continue
            seen_urls.add(url_key)
            all_sections.append(section)

    if not all_sections:
        return f"Found {len(paths)} notes but no per-post sections (### ...) with [Link](...) in knowledgebase/{folder}."

    if isinstance(max_ideas, int) and max_ideas > 0:
        all_sections = all_sections[: max_ideas]

    ideas_preview = []
    inserted = 0
    skipped = 0
    supabase = None if dry_run else get_supabase()

    for section in all_sections:
        idea = _generate_idea_json(section)
        ideas_preview.append(idea["theme"])

        if dry_run:
            continue

        # Simple de-dupe: skip exact (theme, angle) matches in last 7 days
        try:
            week_ago = (_now_utc() - timedelta(days=7)).isoformat()
            existing = (
                supabase.table("content_pipeline")
                .select("id,theme,angle,created_at")
                .eq("theme", idea.get("theme"))
                .eq("angle", idea.get("angle"))
                .gte("created_at", week_ago)
                .limit(1)
                .execute()
            )
            if existing.data:
                skipped += 1
                continue
        except Exception:
            pass

        try:
            supabase.table("content_pipeline").insert(idea).execute()
            inserted += 1
        except Exception:
            skipped += 1

    if dry_run:
        return (
            f"Dry run: would create {len(all_sections)} ideas from {len(paths)} notes in knowledgebase/{folder}.\n"
            + "\n".join(f"- {t}" for t in ideas_preview[:25])
            + ("\n- ..." if len(ideas_preview) > 25 else "")
        )

    return (
        f"Created {inserted} content_pipeline ideas from {len(all_sections)} post sections "
        f"across {len(paths)} notes (skipped {skipped} duplicates/errors).\n"
        + "\n".join(f"- {t}" for t in ideas_preview[:15])
        + ("\n- ..." if len(ideas_preview) > 15 else "")
    )

