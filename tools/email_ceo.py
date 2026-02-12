"""
Tool: email_ceo
Send an email to the CEO. Use for escalations, important updates, or questions.
"""

SCHEMA = {
    "type": "function",
    "function": {
        "name": "email_ceo",
        "description": "Send an email to the CEO. Use this for escalations, important discoveries, strategic questions, or when you need human guidance.",
        "parameters": {
            "type": "object",
            "properties": {
                "subject": {
                    "type": "string",
                    "description": "Email subject line (clear and specific)"
                },
                "message": {
                    "type": "string",
                    "description": "Email body. Be concise and actionable."
                },
                "urgency": {
                    "type": "string",
                    "enum": ["low", "medium", "high"],
                    "description": "How urgent is this. Default: medium"
                }
            },
            "required": ["subject", "message"]
        }
    }
}


def execute(agent_id: str, **kwargs):
    """Send email to CEO."""
    try:
        from lib.email_client import EmailClient
        client = EmailClient()
    except (ValueError, Exception) as e:
        return f"Email not configured: {e}"

    urgency = kwargs.get('urgency', 'medium')
    urgency_emoji = {'low': '📋', 'medium': '📌', 'high': '🚨'}
    emoji = urgency_emoji.get(urgency, '📌')

    subject = f"{emoji} [{agent_id}] {kwargs['subject']}"
    body = f"""From: {agent_id}
        Urgency: {urgency}

        {kwargs['message']}

        ---
        This email was sent by your AI agent {agent_id}.
        Reply to provide feedback or direction.
        """

    success = client._send_email(client.ceo_email, subject, body)

    if success:
        return f"Email sent to CEO: {kwargs['subject']}"
    else:
        return "Failed to send email. Check email configuration."

