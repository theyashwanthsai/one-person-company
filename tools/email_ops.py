"""
Tool: email_ops
Check inbox via IMAP and send email via SMTP.
"""

import os
from typing import List, Optional

from lib.email_client import EmailClient


SCHEMA = {
    "type": "function",
    "function": {
        "name": "email_ops",
        "description": "Check the email inbox or send an email. Use for periodic inbox updates or when the CEO asks to send an email.",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["check", "send"],
                    "description": "Whether to check inbox or send a message."
                },
                "limit": {
                    "type": "integer",
                    "description": "Max number of new emails to fetch when action=check. Default 5."
                },
                "unread_only": {
                    "type": "boolean",
                    "description": "Only return unread emails when action=check. Default true."
                },
                "post_to_discord": {
                    "type": "boolean",
                    "description": "Post inbox updates to Discord #mails. Default true for action=check."
                },
                "to": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Recipient emails when action=send."
                },
                "subject": {
                    "type": "string",
                    "description": "Email subject when action=send."
                },
                "body": {
                    "type": "string",
                    "description": "Email body when action=send."
                },
                "cc": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "CC recipients when action=send."
                },
                "bcc": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "BCC recipients when action=send."
                }
            },
            "required": ["action"]
        }
    }
}


def _ensure_list(value) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str):
        return [v.strip() for v in value.split(",") if v.strip()]
    return []


def _post_to_mails_channel(agent_id: str, content: str) -> Optional[str]:
    try:
        from lib.discord.client import DiscordClient

        client = DiscordClient()
    except Exception as exc:
        return f"Discord not configured: {exc}"

    channel_id = os.getenv("DISCORD_MAILS_CHANNEL_ID")
    if not channel_id:
        return "DISCORD_MAILS_CHANNEL_ID not configured"

    success = client.send_message(channel_id=channel_id, content=content, agent_id=agent_id)
    if success:
        return None
    return "Failed to send Discord update to #mails"


def execute(agent_id: str, **kwargs):
    action = kwargs.get("action")
    client = EmailClient()

    if action == "check":
        limit = int(kwargs.get("limit", 5))
        unread_only = kwargs.get("unread_only", True)
        post_to_discord = kwargs.get("post_to_discord", True)

        try:
            messages = client.fetch_new_messages(limit=limit, unread_only=unread_only)
        except Exception as exc:
            return f"Email check failed: {exc}"

        if not messages:
            return "No new emails."

        lines = [
            f"New emails ({len(messages)}):"
        ]
        for msg in messages:
            line = f"- From: {msg.sender} | Subject: {msg.subject} | Date: {msg.date}"
            if msg.flags:
                line += f" | Flags: {' '.join(msg.flags)}"
            if msg.attachments:
                names = ", ".join(a.get("filename", "attachment") for a in msg.attachments[:3])
                extra = "" if len(msg.attachments) <= 3 else f" (+{len(msg.attachments) - 3} more)"
                line += f" | Attachments: {len(msg.attachments)} ({names}{extra})"
            if msg.in_reply_to or msg.references:
                line += " | Threaded: yes"
            if msg.snippet:
                line += f" | Snippet: {msg.snippet[:160]}"
            lines.append(line)

        summary = "\n".join(lines)

        if post_to_discord:
            discord_error = _post_to_mails_channel(agent_id, summary)
            if discord_error:
                return f"{summary}\n\nDiscord update failed: {discord_error}"
            return "Inbox update posted to #mails."

        return summary

    if action == "send":
        to_addresses = _ensure_list(kwargs.get("to"))
        cc_addresses = _ensure_list(kwargs.get("cc"))
        bcc_addresses = _ensure_list(kwargs.get("bcc"))
        subject = (kwargs.get("subject") or "").strip()
        body = (kwargs.get("body") or "").strip()

        if not to_addresses:
            return "Email send failed: missing 'to' recipients."
        if not subject:
            return "Email send failed: missing 'subject'."
        if not body:
            return "Email send failed: missing 'body'."

        try:
            client.send_email(
                to_addresses=to_addresses,
                subject=subject,
                body=body,
                cc_addresses=cc_addresses or None,
                bcc_addresses=bcc_addresses or None,
            )
        except Exception as exc:
            return f"Email send failed: {exc}"

        return f"Email sent to {', '.join(to_addresses)}."

    return "Invalid action. Use 'check' or 'send'."
