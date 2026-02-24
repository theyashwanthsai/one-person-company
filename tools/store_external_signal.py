"""Tool: Store External Signal
Persist structured signals into the `external_signals` table so agents can treat saved conversations as shared knowledge."""

import os
import hashlib
from datetime import datetime
from typing import Iterable, List, Mapping, Optional, Tuple

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


def _build_source_id(entry: Mapping[str, object], source: str) -> str:
    raw_data = entry.get("raw_data")
    if isinstance(raw_data, Mapping):
        candidate = (
            raw_data.get("id")
            or raw_data.get("objectID")
            or raw_data.get("name")
            or raw_data.get("permalink")
        )
        if candidate is not None:
            return str(candidate)

    candidate = entry.get("id")
    if candidate is not None:
        return str(candidate)

    url = entry.get("url") or entry.get("link") or ""
    if isinstance(url, str) and url.strip():
        digest = hashlib.sha1(url.strip().encode("utf-8")).hexdigest()[:20]
        return f"url_{digest}"

    # Last-resort stable fallback from source + textual content.
    seed = f"{source}|{entry.get('title', '')}|{entry.get('content', '')}|{entry.get('text', '')}"
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:20]
    return f"content_{digest}"


def _build_payload(entry: Mapping[str, object], source: str, now: str):
    content = entry.get("content") or entry.get("text") or entry.get("title") or ""
    payload = {
        "source": source,
        "source_id": _build_source_id(entry, source),
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
        "ingested_at": entry.get("ingested_at") or now,
    }
    return payload


def _find_existing_signal(client, source: str, source_id: str) -> Optional[Mapping[str, object]]:
    result = (
        client.table("external_signals")
        .select("id, seen_count")
        .eq("source", source)
        .eq("source_id", source_id)
        .limit(1)
        .execute()
    )
    if result.data and isinstance(result.data, list):
        return result.data[0]
    return None


def _store_or_update_signal(
    client,
    entry: Mapping[str, object],
    source: str,
    now: str,
) -> Tuple[Optional[str], bool]:
    payload = _build_payload(entry, source, now)
    source_id = payload["source_id"]
    existing = _find_existing_signal(client, source=source, source_id=source_id)

    if existing:
        seen_count = int(existing.get("seen_count") or 1) + 1
        update_payload = {
            "content": payload["content"],
            "url": payload["url"],
            "author": payload["author"],
            "metrics": payload["metrics"],
            "tags": payload["tags"],
            "last_seen_at": now,
            "seen_count": seen_count,
        }
        (
            client.table("external_signals")
            .update(update_payload)
            .eq("id", existing["id"])
            .execute()
        )
        return str(existing["id"]), False

    insert_payload = {
        **payload,
        "first_seen_at": now,
        "last_seen_at": now,
        "seen_count": 1,
    }
    result = client.table("external_signals").insert(insert_payload).execute()
    if result.data and isinstance(result.data, list):
        return str(result.data[0]["id"]), True
    return None, True


def _execute_insert(signals: Iterable[Mapping[str, object]], source: str, category: str):
    client = _get_supabase()
    now = datetime.utcnow().isoformat()
    stored_ids: List[str] = []
    inserted_count = 0
    updated_count = 0

    for entry in signals:
        signal_id, inserted = _store_or_update_signal(client, entry, source, now)
        if signal_id:
            stored_ids.append(signal_id)
            if inserted:
                inserted_count += 1
            else:
                updated_count += 1
    return stored_ids, inserted_count, updated_count


async def execute(
    agent_id: Optional[str] = None,
    signals: List[Mapping[str, object]] = None,
    source: str = "",
    category: str = "external_scan",
) -> dict:
    del agent_id
    signals = signals or []
    source = (source or "").strip()

    if not source:
        return {
            "success": False,
            "error": "Missing required field: source"
        }

    if not signals:
        return {
            "success": True,
            "signals_stored": 0,
            "inserted_count": 0,
            "updated_count": 0,
            "source": source,
            "category": category,
            "message": "No signals provided"
        }

    try:
        stored_ids, inserted_count, updated_count = _execute_insert(signals, source, category)
        return {
            "success": True,
            "signals_stored": len(stored_ids),
            "inserted_count": inserted_count,
            "updated_count": updated_count,
            "source": source,
            "category": category,
            "signal_ids": stored_ids
        }
    except Exception as exc:
        return {
            "success": False,
            "error": f"Failed to store signals: {exc}"
        }
