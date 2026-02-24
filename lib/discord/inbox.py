import os
import re
import time
import asyncio
import threading
from typing import Awaitable, Callable, Dict, List, Optional


INBOX_QUEUE: Dict[str, List[dict]] = {}
INBOX_QUEUE_LOCK = threading.Lock()
AGENT_BUSY: Dict[str, bool] = {}
AGENT_BUSY_LOCK = threading.Lock()
DEFAULT_DISCORD_POLL_SECONDS = 60
LAST_SEEN_DISCORD_MESSAGE_ID: Dict[str, str] = {}
LAST_SEEN_LOCK = threading.Lock()

_RUN_INBOX_CALLBACK: Optional[Callable[[str, str, str], Awaitable[None]]] = None
RECENT_CHAT_CONTEXT_LIMIT = 20


def configure_inbox_runner(callback: Callable[[str, str, str], Awaitable[None]]):
    """Register async callback used to process queued inbox requests."""
    global _RUN_INBOX_CALLBACK
    _RUN_INBOX_CALLBACK = callback


def get_discord_poll_seconds() -> int:
    """Read Discord polling interval from env with sane fallback."""
    raw = os.getenv("DISCORD_POLL_SECONDS", str(DEFAULT_DISCORD_POLL_SECONDS))
    try:
        value = int(raw)
        return max(15, value)
    except ValueError:
        return DEFAULT_DISCORD_POLL_SECONDS


def should_process_existing_messages_on_start() -> bool:
    """
    If enabled, process existing unread-ish history from #general on startup.
    Default is false to avoid reprocessing old messages after engine restart.
    """
    raw = os.getenv("DISCORD_PROCESS_EXISTING_ON_START", "0").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def set_agent_busy(agent_id: str, is_busy: bool):
    with AGENT_BUSY_LOCK:
        AGENT_BUSY[agent_id] = is_busy


def get_agent_busy(agent_id: str) -> bool:
    with AGENT_BUSY_LOCK:
        return AGENT_BUSY.get(agent_id, False)


async def wait_until_agents_idle(agent_ids: List[str], wait_seconds: int = 2):
    while True:
        with AGENT_BUSY_LOCK:
            any_busy = any(AGENT_BUSY.get(agent_id, False) for agent_id in agent_ids)
        if not any_busy:
            return
        await asyncio.sleep(wait_seconds)


def queue_inbox_message(agent_id: str, message: dict):
    with INBOX_QUEUE_LOCK:
        existing = INBOX_QUEUE.get(agent_id, [])
        INBOX_QUEUE[agent_id] = existing + [message]


def pop_next_inbox_message(agent_id: str) -> Optional[dict]:
    with INBOX_QUEUE_LOCK:
        existing = INBOX_QUEUE.get(agent_id, [])
        if not existing:
            return None
        message = existing[0]
        INBOX_QUEUE[agent_id] = existing[1:]
        return message


def build_inbox_request_task(agent_id: str, message: dict) -> str:
    sender = message.get("from", "unknown")
    subject = message.get("subject", "(no subject)")
    body = (message.get("body", "") or "").strip()
    recent_chat = get_recent_chat_context(message.get("channel_id"), RECENT_CHAT_CONTEXT_LIMIT)
    return (
        "You received a direct Discord request from the CEO. "
        "Handle it now, then send your response via discord_ceo.\n"
        "Reply like a human in a normal chat: natural, direct, concise.\n"
        "Do not write status-report language (e.g., 'Acknowledged...').\n"
        "Do not include subject lines, urgency labels, signatures, or metadata.\n\n"
        f"Agent: {agent_id}\n"
        f"From: {sender}\n"
        f"Subject: {subject}\n"
        f"Message:\n{body}\n\n"
        f"{recent_chat}"
    )


def _format_recent_chat_lines(messages: List[dict]) -> str:
    if not messages:
        return ""
    lines = [
        f"Recent Discord chat context (latest {len(messages)} messages, oldest first):"
    ]
    for item in messages:
        sender = item.get("from", "unknown")
        body = (item.get("body") or "").strip()
        if not body:
            continue
        short_body = body[:300] + ("..." if len(body) > 300 else "")
        lines.append(f"- {sender}: {short_body}")
    return "\n".join(lines)


def get_recent_chat_context(channel_id: Optional[str], limit: int = RECENT_CHAT_CONTEXT_LIMIT) -> str:
    if not channel_id:
        return ""
    try:
        from lib.discord.client import DiscordClient

        client = DiscordClient()
    except Exception:
        return ""

    try:
        messages = client.get_recent_channel_messages(
            channel_id=channel_id,
            token_agent_id=None,
            limit=limit,
        )
    except Exception:
        return ""

    return _format_recent_chat_lines(messages)


def send_busy_ack(client, agent_id: str, message: dict):
    channel_id = message.get("channel_id")
    if not channel_id:
        return
    subject = message.get("subject", "(no subject)")
    body = (
        f"{agent_id} is currently busy on an active session.\n"
        "Your request has been queued and will be handled after the current work finishes."
    )
    original_id = message.get("id")
    client.send_message(
        channel_id=channel_id,
        content=f"Re: {subject}\n\n{body}",
        agent_id=agent_id,
        reply_to_message_id=original_id,
    )


def _message_targets_agent(message_body: str, agent: dict) -> bool:
    """Check if message text addresses this agent directly."""
    text = (message_body or "").lower()
    if not text:
        return False

    agent_id = (agent.get("id") or "").lower()
    if agent_id and agent_id in text:
        return True

    name = (agent.get("name") or "").lower()
    if name:
        first_name = name.split()[0]
        if first_name and re.search(rf"\b{re.escape(first_name)}\b", text):
            return True
    return False


def resolve_message_targets(message_body: str, agents: List[dict]) -> List[str]:
    """
    Route a CEO message from #general to target agent(s).
    Rules:
    - Contains 'all'/'everyone'/'team' => all agents
    - Mentions agent id or first name => matching agents
    - No explicit target => one default agent
    """
    text = (message_body or "").lower()
    agent_ids = [a.get("id") for a in agents if a.get("id")]
    if not agent_ids:
        return []

    if re.search(r"\b(all|everyone|team)\b", text) or "@everyone" in text:
        return agent_ids

    matched = [a["id"] for a in agents if _message_targets_agent(text, a)]
    if matched:
        return matched

    configured_default = os.getenv("DISCORD_DEFAULT_AGENT_ID", "watari")
    if configured_default in agent_ids:
        return [configured_default]
    return [agent_ids[0]]


def trigger_inbox_request_if_idle(agent_id: str):
    if get_agent_busy(agent_id) or _RUN_INBOX_CALLBACK is None:
        return

    message = pop_next_inbox_message(agent_id)
    if not message:
        return

    def _run():
        task = build_inbox_request_task(agent_id, message)
        try:
            asyncio.run(_RUN_INBOX_CALLBACK(agent_id, task, "inbox_request"))
        except Exception as e:
            print(f"  ❌ Inbox request failed for {agent_id}: {e}")

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()


def poll_discord_for_all_agents(
    get_all_agents_fn: Callable[[], List[dict]],
    queue_message_fn: Optional[Callable[[str, dict], None]] = None,
    get_busy_fn: Optional[Callable[[str], bool]] = None,
    trigger_if_idle_fn: Optional[Callable[[str], None]] = None,
):
    """
    Poll Discord messages for all agents and queue messages for their next run.
    This runs in a background thread every minute.
    """
    try:
        from lib.discord.client import DiscordClient

        client = DiscordClient()
    except Exception:
        return

    try:
        all_agents = get_all_agents_fn()
    except Exception:
        return

    general_channel_id = client.general_channel_id
    if not general_channel_id:
        return

    with LAST_SEEN_LOCK:
        last_seen = LAST_SEEN_DISCORD_MESSAGE_ID.get("general")

    messages = client.get_recent_user_messages(
        channel_id=general_channel_id,
        token_agent_id=None,
        since_message_id=last_seen,
        limit=50,
    )
    if not messages:
        return

    queue_fn = queue_message_fn or queue_inbox_message
    busy_fn = get_busy_fn or get_agent_busy
    trigger_fn = trigger_if_idle_fn or trigger_inbox_request_if_idle

    for message in messages:
        targets = resolve_message_targets(message.get("body", ""), all_agents)
        for agent_id in targets:
            queue_fn(agent_id, message)
            if busy_fn(agent_id):
                send_busy_ack(client, agent_id, message)

    newest_id = messages[-1].get("id")
    if newest_id:
        with LAST_SEEN_LOCK:
            LAST_SEEN_DISCORD_MESSAGE_ID["general"] = newest_id

    for agent in all_agents:
        agent_id = agent.get("id")
        if agent_id:
            trigger_fn(agent_id)


def prime_discord_cursor_if_needed(client):
    """
    Initialize LAST_SEEN cursor at startup so restarts don't replay old messages.
    """
    if should_process_existing_messages_on_start():
        return

    general_channel_id = client.general_channel_id
    if not general_channel_id:
        return

    with LAST_SEEN_LOCK:
        already = LAST_SEEN_DISCORD_MESSAGE_ID.get("general")
    if already:
        return

    latest_id = client.get_latest_message_id(
        channel_id=general_channel_id,
        token_agent_id=None,
    )
    if latest_id:
        with LAST_SEEN_LOCK:
            LAST_SEEN_DISCORD_MESSAGE_ID["general"] = latest_id
        print("  ℹ️ Primed Discord cursor at latest general-channel message (startup replay disabled).")


def start_discord_poller(get_all_agents_fn: Callable[[], List[dict]]):
    """Start daemon thread that polls Discord periodically."""

    def _loop():
        poll_seconds = get_discord_poll_seconds()
        try:
            from lib.discord.client import DiscordClient

            client = DiscordClient()
            prime_discord_cursor_if_needed(client)
        except Exception:
            pass

        while True:
            poll_discord_for_all_agents(get_all_agents_fn)
            time.sleep(poll_seconds)

    thread = threading.Thread(target=_loop, daemon=True)
    thread.start()


def get_inbox_context(agent_id: str) -> str:
    """
    Consume queued inbox messages for this agent and convert them into
    a prompt context block.
    """
    with INBOX_QUEUE_LOCK:
        queued = INBOX_QUEUE.get(agent_id, [])
        messages = queued[:3]
        INBOX_QUEUE[agent_id] = queued[3:]
    if not messages:
        return ""

    lines = ["Discord directives from CEO (process these before continuing your task):"]
    for idx, message in enumerate(messages, start=1):
        subject = message.get("subject", "").strip() or "(no subject)"
        sender = message.get("from", "unknown")
        body = message.get("body", "").strip()
        short_body = body[:500] + ("..." if len(body) > 500 else "")
        lines.append(f"{idx}. From: {sender}")
        lines.append(f"   Subject: {subject}")
        lines.append(f"   Message: {short_body}")
    lines.append(
        "Acknowledge and act on these as needed. "
        "If another agent should handle this, request a 1-on-1 and notify the CEO. "
        "When you message the CEO, keep it conversational and plain text."
    )
    recent_channel_id = messages[-1].get("channel_id")
    recent_chat = get_recent_chat_context(recent_channel_id, RECENT_CHAT_CONTEXT_LIMIT)
    if recent_chat:
        lines.append("")
        lines.append(recent_chat)
    return "\n".join(lines)
