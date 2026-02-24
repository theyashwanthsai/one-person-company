"""Helpers for Obsidian-style markdown knowledge base files."""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional


DEFAULT_KB_ROOT = "knowledgebase"


def _slugify(value: str) -> str:
    text = (value or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    return text or "note"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def get_kb_root() -> Path:
    configured = os.getenv("KNOWLEDGE_BASE_DIR", DEFAULT_KB_ROOT).strip()
    root = Path(configured)
    if not root.is_absolute():
        root = Path(__file__).resolve().parent.parent / configured
    return root


def ensure_kb_dirs() -> Path:
    root = get_kb_root()
    for rel in ("inbox", "sources/youtube", "sources/web", "notes"):
        (root / rel).mkdir(parents=True, exist_ok=True)
    return root


def _normalize_tags(tags: Optional[Iterable[str]]) -> List[str]:
    if not tags:
        return []
    out: List[str] = []
    for tag in tags:
        clean = (tag or "").strip().replace(" ", "_")
        if clean:
            out.append(clean)
    # Stable unique
    seen = set()
    unique = []
    for tag in out:
        if tag not in seen:
            seen.add(tag)
            unique.append(tag)
    return unique


def wiki_link(title: str) -> str:
    return f"[[{(title or '').strip()}]]"


def write_markdown_note(
    title: str,
    body: str,
    folder: str = "notes",
    tags: Optional[Iterable[str]] = None,
    source_url: Optional[str] = None,
    note_type: str = "note",
    aliases: Optional[Iterable[str]] = None,
    filename_hint: Optional[str] = None,
) -> dict:
    root = ensure_kb_dirs()
    safe_folder = folder.strip("/").strip() or "notes"
    dir_path = root / safe_folder
    dir_path.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    base = _slugify(filename_hint or title)
    file_path = dir_path / f"{ts}_{base}.md"

    clean_tags = _normalize_tags(tags)
    clean_aliases = [a.strip() for a in (aliases or []) if (a or "").strip()]

    frontmatter_lines = [
        "---",
        f'title: "{(title or "").replace(chr(34), chr(39))}"',
        f"type: {note_type}",
        f"created: {now_iso()}",
    ]
    if source_url:
        frontmatter_lines.append(f"source_url: {source_url}")
    if clean_tags:
        frontmatter_lines.append(f"tags: [{', '.join(clean_tags)}]")
    if clean_aliases:
        escaped_aliases = [f'"{a.replace(chr(34), chr(39))}"' for a in clean_aliases]
        frontmatter_lines.append(f"aliases: [{', '.join(escaped_aliases)}]")
    frontmatter_lines.append("---")
    frontmatter = "\n".join(frontmatter_lines)

    content = f"{frontmatter}\n\n# {title}\n\n{(body or '').strip()}\n"
    file_path.write_text(content, encoding="utf-8")

    return {
        "ok": True,
        "path": str(file_path),
        "root": str(root),
        "title": title,
    }

