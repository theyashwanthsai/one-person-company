"""
Tool: discord_ceo
Send a Discord message to the CEO. Use for escalations, important updates, or questions.
"""

SCHEMA = {
    "type": "function",
    "function": {
        "name": "discord_ceo",
        "description": "Send a plain-text Discord message to the CEO. Use this for escalations, updates, questions, or direct replies.",
        "parameters": {
            "type": "object",
            "properties": {
                "subject": {
                    "type": "string",
                    "description": "Optional metadata only. Not shown in Discord output."
                },
                "message": {
                    "type": "string",
                    "description": "The exact text to send in Discord. Write it naturally like a human conversation."
                },
                "urgency": {
                    "type": "string",
                    "enum": ["low", "medium", "high"],
                    "description": "How urgent is this. Default: medium"
                },
                "channel": {
                    "type": "string",
                    "enum": ["auto", "general", "standup", "content", "mails"],
                    "description": "Where to post in Discord. standup for standups, content for content updates, mails for email summaries. Default: auto"
                }
            },
            "required": ["message"]
        }
    }
}


def execute(agent_id: str, **kwargs):
    """Send Discord message to CEO."""
    try:
        from lib.discord.client import DiscordClient
        client = DiscordClient()
    except (ValueError, Exception) as e:
        return f"Discord not configured: {e}"

    urgency = kwargs.get("urgency", "medium")
    channel = kwargs.get("channel", "auto")
    success = client.send_to_ceo(
        agent_id=agent_id,
        subject=kwargs.get("subject", ""),
        message=kwargs["message"],
        urgency=urgency,
        channel=channel,
    )

    if success:
        return "Discord message sent to CEO."
    return "Failed to send Discord message. Check Discord configuration."
