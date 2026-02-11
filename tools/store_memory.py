"""
Tool: store_memory
Record an experiential memory — what happened, how it felt, what you observed.
"""

SCHEMA = {
    "type": "function",
    "function": {
        "name": "store_memory",
        "description": "Record a memory of something that happened. Memories are experiential — they capture events, interactions, observations with emotional context.",
        "parameters": {
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "Brief summary of what happened (1-2 sentences)"
                },
                "memory_type": {
                    "type": "string",
                    "enum": ["conversation", "observation", "decision", "feedback", "discovery", "brainstorm", "one_on_one", "standup", "watercooler", "market_review"],
                    "description": "Type of memory"
                },
                "emotional_valence": {
                    "type": "string",
                    "enum": ["energized", "satisfied", "neutral", "frustrated", "uncertain", "curious", "motivated", "critical", "collaborative", "casual", "focused"],
                    "description": "How you felt about this experience"
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tags to categorize this memory"
                }
            },
            "required": ["summary", "memory_type"]
        }
    }
}


def execute(agent_id: str, **kwargs):
    """Store a memory for this agent."""
    from lib.memories import store_memory

    result = store_memory(
        agent_id=agent_id,
        memory_type=kwargs['memory_type'],
        summary=kwargs['summary'],
        emotional_valence=kwargs.get('emotional_valence', 'neutral'),
        tags=kwargs.get('tags', [])
    )

    if result:
        return f"Memory stored: {kwargs['summary']}"
    else:
        return "Failed to store memory."

