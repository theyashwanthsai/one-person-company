"""
Tool: recall_memories
Search your past experiences and interactions.
"""

SCHEMA = {
    "type": "function",
    "function": {
        "name": "recall_memories",
        "description": "Search your past experiences and interactions. Use this to recall conversations, observations, decisions, and how you felt about them.",
        "parameters": {
            "type": "object",
            "properties": {
                "memory_type": {
                    "type": "string",
                    "description": "Filter by memory type (e.g. 'conversation', 'brainstorm', 'one_on_one')"
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tags to filter by (e.g. ['creator_lead'] to recall interactions with creator)"
                },
                "limit": {
                    "type": "integer",
                    "description": "Max memories to return. Default 5"
                }
            },
            "required": []
        }
    }
}


def execute(agent_id: str, **kwargs):
    """Query memories for this agent."""
    from lib.memories import query_memories

    results = query_memories(
        agent_id=agent_id,
        memory_type=kwargs.get('memory_type'),
        tags=kwargs.get('tags'),
        limit=kwargs.get('limit', 5)
    )

    if not results:
        return "No memories found matching your criteria."

    lines = []
    for m in results:
        valence = f" (felt: {m['emotional_valence']})" if m.get('emotional_valence') else ""
        lines.append(f"- [{m['memory_type']}] {m['summary']}{valence}")

    return f"Found {len(results)} memories:\n" + "\n".join(lines)

