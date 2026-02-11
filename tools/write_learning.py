"""
Tool: write_learning
Document a new learning — a pattern, insight, strategy, or lesson discovered.
"""

SCHEMA = {
    "type": "function",
    "function": {
        "name": "write_learning",
        "description": "Document a new learning you've discovered. Use this to record patterns, insights, strategies, or lessons so the team remembers them.",
        "parameters": {
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "enum": ["insight", "pattern", "strategy", "lesson", "warning", "preference"],
                    "description": "Type of learning"
                },
                "statement": {
                    "type": "string",
                    "description": "Clear, specific statement of what you learned (1-2 sentences)"
                },
                "confidence": {
                    "type": "number",
                    "description": "How confident you are (0.0 to 1.0). Default 0.6"
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tags to categorize this learning"
                }
            },
            "required": ["type", "statement"]
        }
    }
}


def execute(agent_id: str, **kwargs):
    """Write a new learning for this agent."""
    from lib.learnings import write_learning

    result = write_learning(
        agent_id=agent_id,
        type=kwargs['type'],
        statement=kwargs['statement'],
        confidence=kwargs.get('confidence', 0.6),
        tags=kwargs.get('tags', [])
    )

    if result:
        return f"Learning recorded: [{kwargs['type']}] {kwargs['statement']} (confidence: {kwargs.get('confidence', 0.6)})"
    else:
        return "Failed to record learning."

