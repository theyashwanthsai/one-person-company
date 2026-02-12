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
    from lib.sessions import create_session, append_turn, complete_session

    target = kwargs['target_agent']
    reason = kwargs['reason']

    if target == agent_id:
        return "You can't request a 1-on-1 with yourself."

    session_id = create_session(
        type="one_on_one",
        participants=[agent_id, target],
        initiator=agent_id,
        intent=reason[:200]
    )

    if not session_id:
        return f"Failed to start 1-on-1 with {target}."

    append_turn(
        session_id,
        speaker=agent_id,
        text=f"Requested 1-on-1 with {target}. Reason: {reason}"
    )
    complete_session(session_id, artifacts={
        "requested_by": agent_id,
        "target_agent": target,
        "reason": reason,
        "status": "requested"
    })
    return f"1-on-1 session request logged with {target}. session_id={session_id}"
