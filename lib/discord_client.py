"""
Discord client for CEO/agent communication.
Uses Discord REST API (no gateway dependency).
"""

import os
import re
from typing import Dict, List, Optional

import requests


def _env_key_for_agent(agent_id: str, suffix: str) -> str:
    normalized = re.sub(r"[^A-Z0-9]", "_", agent_id.upper())
    return f"DISCORD_{normalized}_{suffix}"


class DiscordClient:
    """Small Discord REST wrapper for agent communication."""

    def __init__(self):
        self.default_bot_token = os.getenv("DISCORD_BOT_TOKEN")
        self.default_channel_id = os.getenv("DISCORD_CHANNEL_ID")
        self.general_channel_id = os.getenv("DISCORD_GENERAL_CHANNEL_ID", self.default_channel_id)
        self.standup_channel_id = os.getenv("DISCORD_STANDUP_CHANNEL_ID", self.default_channel_id)
        self.ceo_user_id = os.getenv("DISCORD_CEO_USER_ID")
        self.http_timeout_seconds = int(os.getenv("DISCORD_HTTP_TIMEOUT_SECONDS", "15"))

        if not self.default_bot_token and not self._has_any_agent_token():
            raise ValueError(
                "Discord bot token not configured. Set DISCORD_BOT_TOKEN or per-agent DISCORD_<AGENT>_BOT_TOKEN."
            )

    def send_to_ceo(
        self,
        agent_id: str,
        subject: str,
        message: str,
        urgency: str = "medium",
        channel: str = "auto",
    ) -> bool:
        """Send a CEO escalation/update message for a specific agent."""
        channel_id = self._resolve_outbound_channel(agent_id=agent_id, channel=channel, subject=subject)
        if not channel_id:
            print(f"Discord channel not configured for {agent_id}")
            return False

        # Keep outbound messages human and clean: only send body text.
        content = (message or "").strip()
        return self.send_message(channel_id, content, agent_id=agent_id)

    def get_recent_user_messages(
        self,
        channel_id: str,
        token_agent_id: Optional[str] = None,
        since_message_id: Optional[str] = None,
        limit: int = 20,
    ) -> List[dict]:
        """
        Fetch recent user-authored messages from a Discord channel.
        Returns oldest-first list.
        """
        token = self._token_for_agent(token_agent_id)
        if not channel_id or not token:
            return []

        bounded_limit = max(1, min(limit, 100))
        params = {"limit": str(bounded_limit)}
        if since_message_id:
            params["after"] = since_message_id

        result = self._request("GET", f"/channels/{channel_id}/messages", token, params=params)
        if not isinstance(result, list):
            return []

        messages: List[dict] = []
        for item in reversed(result):
            author = item.get("author", {}) or {}
            author_id = str(author.get("id", ""))
            is_bot = bool(author.get("bot"))

            if is_bot:
                continue
            if self.ceo_user_id and author_id != self.ceo_user_id:
                continue

            body = (item.get("content") or "").strip()
            if not body:
                continue

            username = author.get("username", "unknown")
            global_name = author.get("global_name")
            sender = f"{global_name} (@{username})" if global_name else f"@{username}"
            messages.append(
                {
                    "id": str(item.get("id", "")),
                    "from": sender,
                    "author_id": author_id,
                    "subject": "Discord message",
                    "body": body,
                    "channel_id": channel_id,
                }
            )
        return messages

    def get_recent_channel_messages(
        self,
        channel_id: str,
        token_agent_id: Optional[str] = None,
        limit: int = 20,
    ) -> List[dict]:
        """
        Fetch recent channel messages (human + bot) for context.
        Returns oldest-first list.
        """
        token = self._token_for_agent(token_agent_id)
        if not channel_id or not token:
            return []

        bounded_limit = max(1, min(limit, 100))
        result = self._request(
            "GET",
            f"/channels/{channel_id}/messages",
            token,
            params={"limit": str(bounded_limit)},
        )
        if not isinstance(result, list):
            return []

        messages: List[dict] = []
        for item in reversed(result):
            author = item.get("author", {}) or {}
            username = author.get("username", "unknown")
            global_name = author.get("global_name")
            sender = f"{global_name} (@{username})" if global_name else f"@{username}"
            body = (item.get("content") or "").strip()
            if not body:
                continue
            messages.append(
                {
                    "id": str(item.get("id", "")),
                    "from": sender,
                    "author_id": str(author.get("id", "")),
                    "is_bot": bool(author.get("bot")),
                    "body": body,
                    "channel_id": channel_id,
                }
            )
        return messages

    def send_message(
        self,
        channel_id: str,
        content: str,
        agent_id: Optional[str] = None,
        reply_to_message_id: Optional[str] = None,
    ) -> bool:
        """Send a Discord message to a channel."""
        token = self._token_for_agent(agent_id) if agent_id else self.default_bot_token
        if not token:
            print(f"Discord token missing for agent={agent_id or 'default'}")
            return False

        payload: Dict[str, object] = {"content": (content or "")[:2000]}
        if reply_to_message_id:
            payload["message_reference"] = {"message_id": reply_to_message_id}
            payload["allowed_mentions"] = {"parse": []}

        result = self._request(
            "POST",
            f"/channels/{channel_id}/messages",
            token,
            json_body=payload,
        )
        return result is not None

    def get_latest_message_id(self, channel_id: str, token_agent_id: Optional[str] = None) -> Optional[str]:
        """
        Return the latest message id in a channel (any author, including bots).
        Useful for priming cursors on startup to avoid replaying old history.
        """
        token = self._token_for_agent(token_agent_id)
        if not channel_id or not token:
            return None

        result = self._request("GET", f"/channels/{channel_id}/messages", token, params={"limit": "1"})
        if not isinstance(result, list) or not result:
            return None
        latest = result[0] or {}
        msg_id = latest.get("id")
        return str(msg_id) if msg_id else None

    def get_pending_messages_for_agent(
        self,
        agent_id: str,
        since_message_id: Optional[str] = None,
        limit: int = 20,
    ) -> List[dict]:
        """
        Fetch messages for an agent channel that look like CEO requests.
        Returns oldest-first items, optionally filtering to messages newer than `since_message_id`.
        """
        channel_id = self._channel_for_agent(agent_id)
        return self.get_recent_user_messages(
            channel_id=channel_id or "",
            token_agent_id=agent_id,
            since_message_id=since_message_id,
            limit=limit,
        )

    def _has_any_agent_token(self) -> bool:
        for key, value in os.environ.items():
            if key.startswith("DISCORD_") and key.endswith("_BOT_TOKEN") and value:
                return True
        return False

    def _token_for_agent(self, agent_id: Optional[str]) -> Optional[str]:
        if agent_id:
            token = os.getenv(_env_key_for_agent(agent_id, "BOT_TOKEN"))
            if token:
                return token
        return self.default_bot_token

    def _channel_for_agent(self, agent_id: str) -> Optional[str]:
        channel = os.getenv(_env_key_for_agent(agent_id, "CHANNEL_ID"))
        if channel:
            return channel
        return self.general_channel_id

    def _resolve_outbound_channel(self, agent_id: str, channel: str, subject: str) -> Optional[str]:
        by_agent = self._channel_for_agent(agent_id)

        if channel == "standup":
            return self.standup_channel_id or by_agent
        if channel == "general":
            return self.general_channel_id or by_agent

        # "auto" defaults to general. Standup channel should only be used when explicitly requested.
        return self.general_channel_id or by_agent

    def _request(
        self,
        method: str,
        path: str,
        token: str,
        params: Optional[dict] = None,
        json_body: Optional[dict] = None,
    ):
        url = f"https://discord.com/api/v10{path}"
        headers = {"Authorization": f"Bot {token}"}
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json_body,
                timeout=self.http_timeout_seconds,
            )
            if response.status_code >= 400:
                print(f"Discord API error ({response.status_code}): {response.text[:200]}")
                return None
            if not response.text:
                return {}
            return response.json()
        except Exception as exc:
            print(f"Discord API request failed: {exc}")
            return None
