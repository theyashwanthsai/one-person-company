import os
import re
import time
import asyncio
import threading
from typing import Awaitable, Callable, Dict, List, Optional, Set


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
    reply_channel = message.get("reply_channel") or "auto"
    recent_chat = get_recent_chat_context(message.get("channel_id"), RECENT_CHAT_CONTEXT_LIMIT)
    return (
        "You received a direct Discord request from the CEO. "
        "Handle it now, then send your response via discord_ceo.\n"
        "Reply like a human in a normal chat: natural, direct, concise.\n"
        "Do not write status-report language (e.g., 'Acknowledged...').\n"
        "Do not include subject lines, urgency labels, signatures, or metadata.\n\n"
        "CRITICAL: Produce the actual work in your response. "
        "If asked for content, write the content. If asked for a summary, write the summary. "
        "If asked for analysis, write the analysis. "
        "NEVER say 'I will do it' or 'I'm working on it' — there is no later. "
        "Your discord_ceo message IS the deliverable. "
        "Use tools first to gather data if needed, then deliver the finished output.\n\n"
        f"Agent: {agent_id}\n"
        f"From: {sender}\n"
        f"Required reply channel: {reply_channel}\n"
        "When you call discord_ceo, set channel to this required reply channel.\n"
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


def _agent_discord_user_id(agent: dict) -> str:
    agent_id = (agent.get("id") or "").strip()
    if not agent_id:
        return ""
    normalized = re.sub(r"[^A-Z0-9]", "_", agent_id.upper())
    return (os.getenv(f"DISCORD_{normalized}_USER_ID") or "").strip()


def _resolve_targets_from_discord_mentions(message_body: str, agents: List[dict]) -> List[str]:
    mention_ids = {
        mention.strip()
        for mention in re.findall(r"<@!?(\d+)>", message_body or "")
        if mention.strip()
    }
    if not mention_ids:
        return []
    matched = []
    for agent in agents:
        discord_user_id = _agent_discord_user_id(agent)
        if discord_user_id and discord_user_id in mention_ids:
            matched.append(agent["id"])
    return matched


def _is_standup_request(message_body: str) -> bool:
    text = (message_body or "").lower()
    return bool(re.search(r"\bstandup\b", text))


CHANNEL_DEFAULT_AGENTS = {
    "content": "creator_lead",
    "mails": "watari",
    "standup": None,
    "general": None,
}


def _requested_reply_channel(message_body: str, source_channel: str) -> str:
    if source_channel in CHANNEL_DEFAULT_AGENTS:
        return source_channel
    if _is_standup_request(message_body):
        return "standup"
    return "general"


def resolve_message_targets(message_body: str, agents: List[dict], source_channel: str = "general") -> List[str]:
    """
    Route a CEO message to target agent(s).
    Rules:
    - Contains 'all'/'everyone'/'team' => all agents
    - Discord @mention or agent name => matching agents
    - Channel-specific default (e.g. #content → Kavi, #mails → Watari)
    - No explicit target => env default agent
    """
    text = (message_body or "").lower()
    agent_ids = [a.get("id") for a in agents if a.get("id")]
    if not agent_ids:
        return []

    matched_mentions = _resolve_targets_from_discord_mentions(message_body, agents)
    if matched_mentions:
        return matched_mentions

    if re.search(r"\b(all|everyone|team)\b", text) or "@everyone" in text:
        return agent_ids

    if _is_standup_request(message_body):
        return agent_ids

    matched = [a["id"] for a in agents if _message_targets_agent(text, a)]
    if matched:
        return matched

    if source_channel == "standup":
        return agent_ids

    channel_default = CHANNEL_DEFAULT_AGENTS.get(source_channel)
    if channel_default and channel_default in agent_ids:
        return [channel_default]

    configured_default = os.getenv("DISCORD_DEFAULT_AGENT_ID", "watari")
    if configured_default in agent_ids:
        return [configured_default]
    return [agent_ids[0]]


def _poll_channel(
    client,
    all_agents: List[dict],
    channel_id: str,
    channel_key: str,
    queue_fn: Callable[[str, dict], None],
    busy_fn: Callable[[str], bool],
):
    with LAST_SEEN_LOCK:
        last_seen = LAST_SEEN_DISCORD_MESSAGE_ID.get(channel_key)

    messages = client.get_recent_user_messages(
        channel_id=channel_id,
        token_agent_id=None,
        since_message_id=last_seen,
        limit=50,
    )
    if not messages:
        return set()

    triggered_agent_ids: Set[str] = set()
    for message in messages:
        body = message.get("body", "")
        targets = resolve_message_targets(body, all_agents, source_channel=channel_key)
        reply_channel = _requested_reply_channel(body, source_channel=channel_key)
        for agent_id in targets:
            payload = dict(message)
            payload["reply_channel"] = reply_channel
            queue_fn(agent_id, payload)
            triggered_agent_ids.add(agent_id)
            if busy_fn(agent_id):
                send_busy_ack(client, agent_id, payload)

    newest_id = messages[-1].get("id")
    if newest_id:
        with LAST_SEEN_LOCK:
            LAST_SEEN_DISCORD_MESSAGE_ID[channel_key] = newest_id

    return triggered_agent_ids


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

    general_channel_id = (client.general_channel_id or "").strip()
    standup_channel_id = (client.standup_channel_id or "").strip()
    content_channel_id = (client.content_channel_id or "").strip()
    mails_channel_id = (client.mails_channel_id or "").strip()
    channels: List[tuple[str, str]] = []
    if general_channel_id:
        channels.append(("general", general_channel_id))
    seen_ids = {general_channel_id}
    if standup_channel_id and standup_channel_id not in seen_ids:
        channels.append(("standup", standup_channel_id))
        seen_ids.add(standup_channel_id)
    if content_channel_id and content_channel_id not in seen_ids:
        channels.append(("content", content_channel_id))
        seen_ids.add(content_channel_id)
    if mails_channel_id and mails_channel_id not in seen_ids:
        channels.append(("mails", mails_channel_id))
        seen_ids.add(mails_channel_id)
    if not channels:
        return

    queue_fn = queue_message_fn or queue_inbox_message
    busy_fn = get_busy_fn or get_agent_busy
    trigger_fn = trigger_if_idle_fn or trigger_inbox_request_if_idle

    triggered_agents: Set[str] = set()
    for channel_key, channel_id in channels:
        triggered_agents |= _poll_channel(
            client=client,
            all_agents=all_agents,
            channel_id=channel_id,
            channel_key=channel_key,
            queue_fn=queue_fn,
            busy_fn=busy_fn,
        )

    for agent_id in triggered_agents:
        trigger_fn(agent_id)


def prime_discord_cursor_if_needed(client):
    """
    Initialize LAST_SEEN cursor at startup so restarts don't replay old messages.
    """
    if should_process_existing_messages_on_start():
        return

    general_channel_id = (client.general_channel_id or "").strip()
    standup_channel_id = (client.standup_channel_id or "").strip()
    content_channel_id = (client.content_channel_id or "").strip()
    mails_channel_id = (client.mails_channel_id or "").strip()
    channels: List[tuple[str, str]] = []
    seen_ids: set = set()
    if general_channel_id:
        channels.append(("general", general_channel_id))
        seen_ids.add(general_channel_id)
    if standup_channel_id and standup_channel_id not in seen_ids:
        channels.append(("standup", standup_channel_id))
        seen_ids.add(standup_channel_id)
    if content_channel_id and content_channel_id not in seen_ids:
        channels.append(("content", content_channel_id))
        seen_ids.add(content_channel_id)
    if mails_channel_id and mails_channel_id not in seen_ids:
        channels.append(("mails", mails_channel_id))
        seen_ids.add(mails_channel_id)

    for channel_key, channel_id in channels:
        with LAST_SEEN_LOCK:
            already = LAST_SEEN_DISCORD_MESSAGE_ID.get(channel_key)
        if already:
            continue

        latest_id = client.get_latest_message_id(
            channel_id=channel_id,
            token_agent_id=None,
        )
        if latest_id:
            with LAST_SEEN_LOCK:
                LAST_SEEN_DISCORD_MESSAGE_ID[channel_key] = latest_id
            print(
                f"  ℹ️ Primed Discord cursor at latest {channel_key}-channel message "
                "(startup replay disabled)."
            )


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
        "Act on these NOW and deliver the actual output. "
        "If asked for content/summaries/analysis, produce it — don't promise to do it later. "
        "If another agent should handle this, request a 1-on-1 and notify the CEO. "
        "When you message the CEO, keep it conversational and plain text."
    )
    recent_channel_id = messages[-1].get("channel_id")
    recent_chat = get_recent_chat_context(recent_channel_id, RECENT_CHAT_CONTEXT_LIMIT)
    if recent_chat:
        lines.append("")
        lines.append(recent_chat)
    return "\n".join(lines)
