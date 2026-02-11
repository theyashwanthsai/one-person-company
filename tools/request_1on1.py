"""
Tool: request_1on1
Request a 1-on-1 conversation with another agent.
"""

SCHEMA = {
    "type": "function",
    "function": {
        "name": "request_1on1",
        "description": "Request a 1-on-1 conversation with another agent. Use this when you want to discuss something specific with a colleague, need their perspective, or want to collaborate on an idea.",
        "parameters": {
            "type": "object",
            "properties": {
                "target_agent": {
                    "type": "string",
                    "enum": ["strategist_lead", "creator_lead", "analyst_lead"],
                    "description": "The agent you want to talk to"
                },
                "reason": {
                    "type": "string",
                    "description": "Why you want to talk to them (be specific)"
                }
            },
            "required": ["target_agent", "reason"]
        }
    }
}


async def execute(agent_id: str, **kwargs):
    """Request a 1-on-1 session."""
    from workers.one_on_one import run_one_on_one

    target = kwargs['target_agent']
    reason = kwargs['reason']

    if target == agent_id:
        return "You can't request a 1-on-1 with yourself."

    result = await run_one_on_one(
        initiator=agent_id,
        target=target,
        reason=reason
    )

    if result:
        takeaways = result.get('takeaways', [])
        summary = f"1-on-1 with {target} completed."
        if takeaways:
            summary += " Takeaways:\n" + "\n".join([f"- {t['takeaway']}" for t in takeaways])
        return summary
    else:
        return f"Failed to start 1-on-1 with {target}."

