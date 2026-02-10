import os
from supabase import create_client
from typing import List, Optional
from uuid import UUID

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)


def query_learnings(
    agent_id: str,
    types: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    min_confidence: float = 0.5,
    limit: int = 10
) -> List[dict]:
    query = supabase.table("learnings").select("*").eq("agent_id", agent_id)
    
    if types:
        query = query.in_("type", types)
    
    if tags:
        query = query.contains("tags", tags)
    
    query = query.gte("confidence", min_confidence)
    query = query.order("confidence", desc=True)
    query = query.order("created_at", desc=True)
    query = query.limit(limit)
    
    result = query.execute()
    return result.data


def write_learning(
    agent_id: str,
    type: str,
    statement: str,
    confidence: float = 0.6,
    tags: Optional[List[str]] = None,
    evidence_refs: Optional[List[dict]] = None,
    source_session_id: Optional[UUID] = None,
    ceo_boosted: bool = False
) -> dict:
    learning_data = {
        "agent_id": agent_id,
        "type": type,
        "statement": statement,
        "confidence": confidence,
        "tags": tags or [],
        "evidence_refs": evidence_refs or [],
        "source_session_id": str(source_session_id) if source_session_id else None,
        "ceo_boosted": ceo_boosted
    }
    
    result = supabase.table("learnings").insert(learning_data).execute()
    return result.data[0] if result.data else None


def boost_learning(learning_id: UUID):
    supabase.table("learnings").update({
        "ceo_boosted": True,
        "confidence": supabase.rpc("least", {"a": "confidence * 1.2", "b": 0.95})
    }).eq("id", str(learning_id)).execute()


def dismiss_learning(learning_id: UUID):
    supabase.table("learnings").update({
        "confidence": 0.0
    }).eq("id", str(learning_id)).execute()


def get_learning(learning_id: UUID) -> Optional[dict]:
    result = supabase.table("learnings").select("*").eq("id", str(learning_id)).execute()
    return result.data[0] if result.data else None


def get_agent_learnings_summary(agent_id: str) -> dict:
    result = supabase.table("learnings").select("type, confidence").eq("agent_id", agent_id).execute()
    
    if not result.data:
        return {"total": 0, "by_type": {}, "avg_confidence": 0}
    
    learnings = result.data
    by_type = {}
    total_confidence = 0
    
    for l in learnings:
        by_type[l['type']] = by_type.get(l['type'], 0) + 1
        total_confidence += l['confidence']
    
    return {
        "total": len(learnings),
        "by_type": by_type,
        "avg_confidence": round(total_confidence / len(learnings), 2)
    }

