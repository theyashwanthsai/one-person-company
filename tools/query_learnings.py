"""
Tool: query_learnings
Search the team knowledge base for relevant learnings.
"""

SCHEMA = {
    "type": "function",
    "function": {
        "name": "query_learnings",
        "description": "Search team knowledge base for relevant learnings. Use this to recall what the team has learned — patterns, insights, strategies, lessons.",
        "parameters": {
            "type": "object",
            "properties": {
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tags to filter by (e.g. ['content', 'strategy', 'twitter'])"
                },
                "types": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Learning types to filter by: insight, pattern, strategy, lesson, warning, preference"
                },
                "min_confidence": {
                    "type": "number",
                    "description": "Minimum confidence threshold (0.0 to 1.0). Default 0.5"
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results to return. Default 10"
                }
            },
            "required": []
        }
    }
}


def execute(agent_id: str, **kwargs):
    """Query learnings for this agent."""
    from lib.learnings import query_learnings

    results = query_learnings(
        agent_id=agent_id,
        tags=kwargs.get('tags'),
        types=kwargs.get('types'),
        min_confidence=kwargs.get('min_confidence', 0.5),
        limit=kwargs.get('limit', 10)
    )

    if not results:
        return "No learnings found matching your criteria."

    lines = []
    for l in results:
        lines.append(f"- [{l['type']}] {l['statement']} (confidence: {l['confidence']}, tags: {l.get('tags', [])})")

    return f"Found {len(results)} learnings:\n" + "\n".join(lines)

