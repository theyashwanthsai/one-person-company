import os
import time
from supabase import create_client
from typing import List, Optional
from uuid import UUID
from datetime import datetime

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)

MAX_DB_RETRIES = 3
RETRY_BASE_SECONDS = 0.5


def _execute_with_retry(op_name: str, fn):
    """Retry transient Supabase/PostgREST failures."""
    last_error = None
    for attempt in range(MAX_DB_RETRIES):
        try:
            return fn()
        except Exception as e:
            last_error = e
            if attempt == MAX_DB_RETRIES - 1:
                break
            sleep_for = RETRY_BASE_SECONDS * (2 ** attempt)
            print(f"  ⚠️ {op_name} failed (attempt {attempt + 1}/{MAX_DB_RETRIES}): {e}")
            time.sleep(sleep_for)
    raise last_error


def create_session(
    type: str,
    participants: List[str],
    initiator: Optional[str] = None,
    intent: Optional[str] = None
) -> UUID:
    session_data = {
        "type": type,
        "participants": participants,
        "initiator": initiator or "system",
        "status": "running",
        "intent": intent,
        "conversation": [],
        "artifacts": {},
        "started_at": datetime.utcnow().isoformat()
    }
    
    result = _execute_with_retry(
        "create_session",
        lambda: supabase.table("sessions").insert(session_data).execute(),
    )
    return result.data[0]['id'] if result.data else None


def get_session(session_id: UUID) -> Optional[dict]:
    result = _execute_with_retry(
        "get_session",
        lambda: supabase.table("sessions").select("*").eq("id", str(session_id)).execute(),
    )
    return result.data[0] if result.data else None


def update_session(session_id: UUID, updates: dict):
    _execute_with_retry(
        "update_session",
        lambda: supabase.table("sessions").update(updates).eq("id", str(session_id)).execute(),
    )


def append_turn(
    session_id: UUID,
    speaker: str,
    text: str,
    turn: Optional[int] = None
):
    session = get_session(session_id)
    if not session:
        return
    
    conversation = session.get('conversation', [])
    
    turn_data = {
        "speaker": speaker,
        "text": text,
        "turn": turn if turn is not None else len(conversation) + 1,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    conversation.append(turn_data)
    
    _execute_with_retry(
        "append_turn",
        lambda: supabase.table("sessions").update({
            "conversation": conversation
        }).eq("id", str(session_id)).execute(),
    )


def complete_session(session_id: UUID, artifacts: Optional[dict] = None):
    updates = {
        "status": "completed",
        "ended_at": datetime.utcnow().isoformat()
    }
    
    if artifacts:
        updates["artifacts"] = artifacts
    
    _execute_with_retry(
        "complete_session",
        lambda: supabase.table("sessions").update(updates).eq("id", str(session_id)).execute(),
    )


def fail_session(session_id: UUID, error: str):
    _execute_with_retry(
        "fail_session",
        lambda: supabase.table("sessions").update({
            "status": "failed",
            "error_log": error,
            "ended_at": datetime.utcnow().isoformat()
        }).eq("id", str(session_id)).execute(),
    )


def get_recent_sessions(
    type: Optional[str] = None,
    agent_id: Optional[str] = None,
    limit: int = 10
) -> List[dict]:
    query = supabase.table("sessions").select("*")
    
    if type:
        query = query.eq("type", type)
    
    if agent_id:
        query = query.contains("participants", [agent_id])
    
    query = query.order("created_at", desc=True)
    query = query.limit(limit)
    
    result = _execute_with_retry(
        "get_recent_sessions",
        lambda: query.execute(),
    )
    return result.data


def add_learning_to_session(session_id: UUID, learning_id: UUID):
    session = get_session(session_id)
    if not session:
        return

    if session.get("type") == "solo":
        return

    learnings_created = session.get("learnings_created", [])
    if str(learning_id) not in learnings_created:
        learnings_created.append(str(learning_id))
        _execute_with_retry(
            "add_learning_to_session",
            lambda: supabase.table("sessions").update({
                "learnings_created": learnings_created
            }).eq("id", str(session_id)).execute(),
        )
