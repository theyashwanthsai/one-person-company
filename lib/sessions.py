import os
from supabase import create_client
from typing import List, Optional
from uuid import UUID
from datetime import datetime

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)


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
    
    result = supabase.table("sessions").insert(session_data).execute()
    return result.data[0]['id'] if result.data else None


def get_session(session_id: UUID) -> Optional[dict]:
    result = supabase.table("sessions").select("*").eq("id", str(session_id)).execute()
    return result.data[0] if result.data else None


def update_session(session_id: UUID, updates: dict):
    supabase.table("sessions").update(updates).eq("id", str(session_id)).execute()


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
    
    supabase.table("sessions").update({
        "conversation": conversation
    }).eq("id", str(session_id)).execute()


def complete_session(session_id: UUID, artifacts: Optional[dict] = None):
    updates = {
        "status": "completed",
        "ended_at": datetime.utcnow().isoformat()
    }
    
    if artifacts:
        updates["artifacts"] = artifacts
    
    supabase.table("sessions").update(updates).eq("id", str(session_id)).execute()


def fail_session(session_id: UUID, error: str):
    supabase.table("sessions").update({
        "status": "failed",
        "error_log": error,
        "ended_at": datetime.utcnow().isoformat()
    }).eq("id", str(session_id)).execute()


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
    
    result = query.execute()
    return result.data


def add_learning_to_session(session_id: UUID, learning_id: UUID):
    session = get_session(session_id)
    if not session:
        return
    
    learnings_created = session.get('learnings_created', [])
    if str(learning_id) not in learnings_created:
        learnings_created.append(str(learning_id))
        supabase.table("sessions").update({
            "learnings_created": learnings_created
        }).eq("id", str(session_id)).execute()

