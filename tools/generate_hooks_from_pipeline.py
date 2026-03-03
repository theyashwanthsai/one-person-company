"""
Tool: generate_hooks_from_pipeline

For each idea in the content_pipeline table, generate a short-form post and a
scroll-stopping hook, store the draft back into the pipeline, and optionally
send all hooks to the Discord #content channel.
"""

import json
from typing import List, Optional

from dotenv import load_dotenv

from lib.llm import chat_completion_json
from lib.supabase_client import get_supabase

load_dotenv()


SCHEMA = {
    "type": "function",
    "function": {
        "name": "generate_hooks_from_pipeline",
        "description": (
            "Generate short-form drafts and hooks for ideas in the content_pipeline table, "
            "update them as drafted, and optionally send the hooks to Discord #content."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["idea", "approved", "drafted", "all"],
                    "description": "Which status to pull from. Default: idea",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max number of ideas to process. Default: 10",
                },
                "send_to_discord": {
                    "type": "boolean",
                    "description": "If true, send the generated hooks to Discord #content. Default: true",
                },
                "dry_run": {
                    "type": "boolean",
                    "description": "If true, do not write back to the database. Default: false",
                },
            },
            "required": [],
        },
    },
}


def _safe_trim(text: str, max_len: int) -> str:
    text = (text or "").strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rstrip() + "..."


def _build_prompt(theme: str, angle: str, draft_text: Optional[str]) -> str:
    base = f"""You are Kavi, a short-form content writer.

You are creating ONE short-form post based on this idea:
- Theme: {theme}
- Angle: {angle or "(none provided)"}

Existing draft (if any):
{draft_text or "(none)"}"""
    return base


def _call_llm_for_idea(theme: str, angle: str, draft_text: Optional[str]) -> dict:
    system = (
        "You write short-form content (Twitter-style posts). "
        "You MUST follow the structure: Hook → Problem → Answer. "
        "The hook must be 1–2 sentences (<=140 characters), no emojis, no 'thread' labels, "
        "and must work as a standalone post."
    )
    user = _build_prompt(theme, angle, draft_text)
    user += """

Task:
Return JSON with keys:
- hook: string (<= 140 chars, no emojis, no hashtags)
- body: string (the full short-form post, with clear Hook / Problem / Answer sections)
"""
    raw = chat_completion_json(system=system, user=user, model="gpt-4o-mini")
    try:
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError("Non-object JSON")
    except Exception:
        data = {
            "hook": _safe_trim(theme, 120),
            "body": f"{_safe_trim(theme, 200)}\n\nProblem: {angle or 'audience is confused about this topic.'}\n\nAnswer: Provide a clear, practical walkthrough.",
        }
    hook = _safe_trim(str(data.get("hook") or theme), 140)
    body = _safe_trim(str(data.get("body") or ""), 4000)
    return {"hook": hook, "body": body}


def _fetch_ideas(status: str, limit: int) -> List[dict]:
    supabase = get_supabase()
    q = supabase.table("content_pipeline").select("*")
    if status != "all":
        q = q.eq("status", status)
    return q.order("created_at", desc=True).limit(limit).execute().data or []


def _update_idea(row_id: str, draft_text: str, hook: str):
    supabase = get_supabase()
    # Merge hook into draft_metadata, preserving any existing keys if possible.
    existing = supabase.table("content_pipeline").select("draft_metadata").eq("id", row_id).limit(1).execute()
    meta = {}
    try:
        if existing.data and isinstance(existing.data[0].get("draft_metadata"), dict):
            meta = existing.data[0]["draft_metadata"] or {}
    except Exception:
        meta = {}
    meta["hook"] = hook
    supabase.table("content_pipeline").update(
        {"draft_text": draft_text, "draft_metadata": meta, "status": "drafted"}
    ).eq("id", row_id).execute()


def _send_hooks_to_discord(agent_id: str, hooks: List[tuple[str, str]]) -> str:
    if not hooks:
        return "No hooks to send."
    try:
        from lib.discord.client import DiscordClient

        client = DiscordClient()
    except Exception as exc:
        return f"Discord not configured: {exc}"

    lines = ["Daily hooks from content_pipeline ideas:"]
    for idx, (theme, hook) in enumerate(hooks, start=1):
        lines.append(f"{idx}. {theme}\n   Hook: {hook}")
    message = "\n\n".join(lines)

    ok = client.send_to_ceo(
        agent_id=agent_id,
        subject="Daily hooks from pipeline",
        message=message,
        urgency="medium",
        channel="content",
    )
    return "Hooks sent to Discord #content." if ok else "Failed to send hooks to Discord."


def execute(agent_id: str, **kwargs) -> str:
    status = kwargs.get("status", "idea")
    if status not in {"idea", "approved", "drafted", "all"}:
        status = "idea"
    limit = int(kwargs.get("limit", 10) or 10)
    send_to_discord = bool(kwargs.get("send_to_discord", True))
    dry_run = bool(kwargs.get("dry_run", False))

    ideas = _fetch_ideas(status=status, limit=limit)
    if not ideas:
        return f"No content_pipeline rows found with status={status}."

    hooks: List[tuple[str, str]] = []
    processed = 0
    skipped = 0

    for row in ideas:
        row_id = row.get("id")
        theme = row.get("theme") or row.get("angle") or "Untitled idea"
        angle = row.get("angle") or ""
        draft_text = row.get("draft_text") or ""

        gen = _call_llm_for_idea(theme, angle, draft_text)
        hook = gen["hook"]
        body = gen["body"]
        hooks.append((theme, hook))

        if dry_run:
            continue

        try:
            if row_id:
                _update_idea(row_id, draft_text=body, hook=hook)
                processed += 1
            else:
                skipped += 1
        except Exception:
            skipped += 1

    discord_msg = ""
    if send_to_discord and not dry_run:
        discord_msg = _send_hooks_to_discord(agent_id, hooks)

    summary_lines = [
        f"Processed {processed if not dry_run else len(ideas)} ideas (status={status}), skipped {skipped}.",
    ]
    summary_lines.extend([f"- {t}: {h}" for t, h in hooks[:15]])
    if len(hooks) > 15:
        summary_lines.append("- ...")
    if discord_msg:
        summary_lines.append(discord_msg)
    if dry_run and send_to_discord:
        summary_lines.append("(dry_run: no DB writes, no Discord message sent)")

    return "\n".join(summary_lines)

