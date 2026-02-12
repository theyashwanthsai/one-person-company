"""Tool: Store External Signal
Persist structured signals into the `external_signals` table so agents can treat saved conversations as shared knowledge."""

import os
from datetime import datetime
from typing import Iterable, List, Mapping

from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

supabase = None


def _get_supabase():
    global supabase
    if supabase is not None:
        return supabase

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")

    supabase = create_client(url, key)
    return supabase

SCHEMA = {
    "type": "function",
    "function": {
        "name": "store_external_signal",
        "description": "Persist signals fetched from surf_ tools into the shared external_signals table.",
        "parameters": {
            "type": "object",
            "properties": {
                "signals": {
                    "type": "array",
                    "items": {
                        "type": "object",
        "description": "Structured signal payload (title, content, url, author, metrics, raw_data, ingested_at)."
                    },
                    "description": "List of signals to persist."
                },
                "source": {
                    "type": "string",
                    "description": "Source name (e.g. 'hackernews', 'reddit', 'twitter')."
                },
                "category": {
                    "type": "string",
                    "description": "Category tag for these signals.",
                    "default": "external_scan"
                }
            },
            "required": ["signals", "source"]
        }
    }
}


def _normalize_tags(value: object) -> List[str]:
    if isinstance(value, list):
        return [str(item) for item in value if item is not None]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _build_source_id(entry: Mapping[str, object]) -> str:
    raw_data = entry.get("raw_data")
    if isinstance(raw_data, Mapping):
        candidate = raw_data.get("id") or raw_data.get("objectID")
        if candidate is not None:
            return str(candidate)
    candidate = entry.get("id")
    return str(candidate) if candidate is not None else ""


def _build_payload(entry: Mapping[str, object], source: str, now: str):
    content = entry.get("content") or entry.get("text") or entry.get("title") or ""
    payload = {
        "source": source,
        "source_id": _build_source_id(entry),
        "content": content,
        "url": entry.get("url") or entry.get("link") or "",
        "author": entry.get("author") or entry.get("handle") or "",
        "metrics": entry.get("metrics") or {
            "score": entry.get("score", 0),
            "comments": entry.get("comments", 0),
            "engagement_score": entry.get("engagement_score", 0),
            "created_at": entry.get("created_at")
        },
        "tags": _normalize_tags(entry.get("tags")),
        "ingested_at": entry.get("ingested_at") or now
    }
    return payload


def _execute_insert(signals: Iterable[Mapping[str, object]], source: str, category: str) -> List[str]:
    client = _get_supabase()
    now = datetime.utcnow().isoformat()
    stored_ids: List[str] = []

    for entry in signals:
        payload = _build_payload(entry, source, now)
        result = client.table("external_signals").insert(payload).execute()
        if result.data and isinstance(result.data, list):
            stored_ids.append(result.data[0]["id"])
    return stored_ids


async def execute(signals: List[Mapping[str, object]], source: str, category: str = "external_scan") -> dict:
    if not signals:
        return {
            "success": True,
            "signals_stored": 0,
            "source": source,
            "category": category,
            "message": "No signals provided"
        }

    try:
        stored_ids = _execute_insert(signals, source, category)
        return {
            "success": True,
            "signals_stored": len(stored_ids),
            "source": source,
            "category": category,
            "signal_ids": stored_ids
        }
    except Exception as exc:
        return {
            "success": False,
            "error": f"Failed to store signals: {exc}"
        }
