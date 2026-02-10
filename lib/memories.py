import os
from supabase import create_client
from typing import List, Optional
from uuid import UUID

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)


def store_memory(
    agent_id: str,
    memory_type: str,
    summary: str,
    full_content: Optional[dict] = None,
    emotional_valence: Optional[str] = None,
    related_learning_ids: Optional[List[UUID]] = None,
    tags: Optional[List[str]] = None
) -> dict:
    memory_data = {
        "agent_id": agent_id,
        "memory_type": memory_type,
        "summary": summary,
        "full_content": full_content,
        "emotional_valence": emotional_valence,
        "related_learning_ids": [str(id) for id in (related_learning_ids or [])],
        "tags": tags or []
    }
    
    result = supabase.table("memories").insert(memory_data).execute()
    return result.data[0] if result.data else None


def query_memories(
    agent_id: str,
    memory_type: Optional[str] = None,
    tags: Optional[List[str]] = None,
    limit: int = 10
) -> List[dict]:
    query = supabase.table("memories").select("*").eq("agent_id", agent_id)
    
    if memory_type:
        query = query.eq("memory_type", memory_type)
    
    if tags:
        query = query.contains("tags", tags)
    
    query = query.order("created_at", desc=True)
    query = query.limit(limit)
    
    result = query.execute()
    return result.data


def get_memory(memory_id: UUID) -> Optional[dict]:
    result = supabase.table("memories").select("*").eq("id", str(memory_id)).execute()
    return result.data[0] if result.data else None


def link_memory_to_learning(memory_id: UUID, learning_id: UUID):
    memory = get_memory(memory_id)
    if not memory:
        return
    
    related_ids = memory.get('related_learning_ids', [])
    if str(learning_id) not in related_ids:
        related_ids.append(str(learning_id))
        supabase.table("memories").update({
            "related_learning_ids": related_ids
        }).eq("id", str(memory_id)).execute()

