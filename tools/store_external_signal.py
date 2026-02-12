"""Tool: Store External Signal
Persist structured signals into the `external_signals` table so agents can treat saved conversations as shared knowledge."""

import os
from datetime import datetime
from typing import Iterable, List, Mapping

from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)

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


def _build_payload(entry: Mapping[str, object], source: str, category: str, now: str):
    payload = {
        "source": source,
        "category": category,
        "title": entry.get("title") or entry.get("text") or "",
        "content": entry.get("content") or entry.get("text") or "",
        "url": entry.get("url") or entry.get("link") or "",
        "author": entry.get("author") or entry.get("handle") or "",
        "metrics": entry.get("metrics") or {},
        "raw_data": entry.get("raw_data") or {},
        "tags": entry.get("tags") or [],
        "ingested_at": entry.get("ingested_at") or now
    }
    return payload


def _execute_insert(signals: Iterable[Mapping[str, object]], source: str, category: str) -> List[int]:
    now = datetime.utcnow().isoformat()
    stored_ids: List[int] = []

    for entry in signals:
        payload = _build_payload(entry, source, category, now)
        result = supabase.table("external_signals").insert(payload).execute()
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
