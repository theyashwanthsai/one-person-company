"""
Engine — The entire company runs from this file.

One schedule. Each entry prompts an agent with a task.
The agent uses their tools to do the actual work.

Solo work:  run_agent_step(agent_id, task) → agent uses tools autonomously
Meetings:   turn-taking, each turn is run_agent_step() with conversation history

Run:  python3 workers/engine.py
"""

import os
import sys
import random
import asyncio
import schedule
import time
from datetime import datetime
from typing import List
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

from lib.tool_runner import run_agent_with_tools, run_agent_step
from lib.sessions import create_session, append_turn, complete_session
from lib.agents import load_agent_full, update_agent, get_all_agents
from lib import discord_inbox
from lib.schedule_loader import load_schedule_from_markdown


SCHEDULE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schedule.md")

# Compatibility exports used by tests and external scripts.
INBOX_QUEUE = discord_inbox.INBOX_QUEUE
INBOX_QUEUE_LOCK = discord_inbox.INBOX_QUEUE_LOCK
AGENT_BUSY = discord_inbox.AGENT_BUSY
AGENT_BUSY_LOCK = discord_inbox.AGENT_BUSY_LOCK
DEFAULT_DISCORD_POLL_SECONDS = discord_inbox.DEFAULT_DISCORD_POLL_SECONDS
LAST_SEEN_DISCORD_MESSAGE_ID = discord_inbox.LAST_SEEN_DISCORD_MESSAGE_ID
LAST_SEEN_LOCK = discord_inbox.LAST_SEEN_LOCK


def get_schedule() -> List[dict]:
    return load_schedule_from_markdown(SCHEDULE_FILE)


def get_discord_poll_seconds() -> int:
    return discord_inbox.get_discord_poll_seconds()


def should_process_existing_messages_on_start() -> bool:
    return discord_inbox.should_process_existing_messages_on_start()


def set_agent_busy(agent_id: str, is_busy: bool):
    discord_inbox.set_agent_busy(agent_id, is_busy)


def get_agent_busy(agent_id: str) -> bool:
    return discord_inbox.get_agent_busy(agent_id)


async def wait_until_agents_idle(agent_ids: List[str], wait_seconds: int = 2):
    await discord_inbox.wait_until_agents_idle(agent_ids, wait_seconds)


def queue_inbox_message(agent_id: str, message: dict):
    discord_inbox.queue_inbox_message(agent_id, message)


def pop_next_inbox_message(agent_id: str):
    return discord_inbox.pop_next_inbox_message(agent_id)


def build_inbox_request_task(agent_id: str, message: dict) -> str:
    return discord_inbox.build_inbox_request_task(agent_id, message)


def send_busy_ack(client, agent_id: str, message: dict):
    discord_inbox.send_busy_ack(client, agent_id, message)


def resolve_message_targets(message_body: str, agents: List[dict]) -> List[str]:
    return discord_inbox.resolve_message_targets(message_body, agents)


def trigger_inbox_request_if_idle(agent_id: str):
    discord_inbox.trigger_inbox_request_if_idle(agent_id)


def poll_discord_for_all_agents():
    discord_inbox.poll_discord_for_all_agents(
        get_all_agents_fn=get_all_agents,
        queue_message_fn=queue_inbox_message,
        get_busy_fn=get_agent_busy,
        trigger_if_idle_fn=trigger_inbox_request_if_idle,
    )


def prime_discord_cursor_if_needed(client):
    discord_inbox.prime_discord_cursor_if_needed(client)


def start_discord_poller():
    discord_inbox.start_discord_poller(get_all_agents)


def get_inbox_context(agent_id: str) -> str:
    return discord_inbox.get_inbox_context(agent_id)


# ============================================================
# SOLO TASK — One agent, one prompt, tools handle the rest
# ============================================================


async def run_solo(agent_id: str, task: str, session_type: str):
    """
    Run a solo task for one agent.
    The agent gets the prompt and uses tools autonomously.
    """
    now = datetime.now().strftime('%I:%M %p, %B %d')

    print(f"\n{'='*60}")
    print(f"[{now}] SOLO: {agent_id} → {session_type}")
    print(f"{'='*60}")
    set_agent_busy(agent_id, True)
    try:
        update_agent(agent_id, state=f'working_{session_type}', current_location='desk')

        session_id = create_session(
            type=session_type,
            participants=[agent_id],
            initiator='engine',
            intent=task[:200]
        )

        inbox_context = get_inbox_context(agent_id)
        full_task = f"Current time: {now}\n\n{task}"
        if inbox_context:
            full_task = f"{full_task}\n\n{inbox_context}"

        response, tool_calls = await run_agent_step(
            agent_id=agent_id,
            task=full_task,
            model="gpt-4o",
            source_session_id=session_id,
        )

        append_turn(session_id, speaker=agent_id, text=response)

        print(f"  Response: {response[:150]}...")
        print(f"  Tools used: {len(tool_calls)}")
        for tc in tool_calls:
            print(f"    🔧 {tc['tool']}")

        complete_session(session_id, artifacts={
            'type': session_type,
            'response': response,
            'tool_calls': tool_calls
        })
    finally:
        update_agent(agent_id, state='idle', current_location='lounge')
        set_agent_busy(agent_id, False)
        print(f"  ✅ Done\n")
        trigger_inbox_request_if_idle(agent_id)


# Register solo executor for queued Discord inbox requests.
discord_inbox.configure_inbox_runner(run_solo)


# ============================================================
# MEETING — Multi-agent, turn-taking, each turn uses tools
# ============================================================


async def run_meeting(
    agents: List[str],
    task: str,
    session_type: str,
    max_turns: int = 20
):
    """
    Run a multi-agent meeting.
    Thin orchestration: just handles turn order and conversation history.
    Each turn is run_agent_with_tools() — agent decides what to do.
    Continues until natural conclusion or max_turns.
    """
    now = datetime.now().strftime('%I:%M %p, %B %d')

    print(f"\n{'='*60}")
    print(f"[{now}] MEETING: {session_type} — {', '.join(agents)}")
    print(f"{'='*60}")
    for agent_id in agents:
        set_agent_busy(agent_id, True)
    try:
        if session_type == "watercooler":
            meeting_location = "watercooler_zone"
        elif session_type == "one_on_one":
            meeting_location = "one_on_one_room"
        else:
            meeting_location = "meeting_room"

        for agent_id in agents:
            update_agent(agent_id, state=f'in_{session_type}', current_location=meeting_location)

        session_id = create_session(
            type=session_type,
            participants=agents,
            initiator='engine',
            intent=task[:200]
        )

        conversation = []
        all_tool_calls = []

        for turn in range(max_turns):
            speaker = agents[turn % len(agents)]
            agent_data = load_agent_full(speaker)
            soul = agent_data.get('soul_instructions', f'You are {speaker}.')
            inbox_context = get_inbox_context(speaker)

            if turn == 0:
                user_msg = f"Current time: {now}\nMeeting type: {session_type}\nParticipants: {', '.join(agents)}\n\n{task}"
            else:
                history = "\n\n".join([
                    f"**{c['speaker']}**: {c['message']}"
                    for c in conversation
                ])
                user_msg = f"Current time: {now}\nMeeting type: {session_type}\nParticipants: {', '.join(agents)}\n\nMeeting topic:\n{task}\n\nConversation so far:\n{history}\n\nIt's your turn. Respond naturally. When the conversation has reached a natural conclusion, end your message with [DONE]."
            if inbox_context:
                user_msg = f"{user_msg}\n\n{inbox_context}"

            response, tool_calls = await run_agent_with_tools(
                agent_id=speaker,
                system_prompt=soul,
                user_prompt=user_msg,
                model="gpt-4o",
                prepend_recent_context=True,
                auto_log_insights=True,
                source_session_id=session_id,
            )

            conversation.append({"speaker": speaker, "message": response})
            all_tool_calls.extend(tool_calls)
            append_turn(session_id, speaker=speaker, text=response, turn=turn)

            print(f"  [{turn+1}] {speaker}: {response[:100]}...")
            for tc in tool_calls:
                print(f"       🔧 {tc['tool']}")

            if "[DONE]" in response or "[done]" in response:
                print(f"  → Natural conclusion at turn {turn+1}")
                break

            if turn >= len(agents) * 2:
                conclusive_phrases = [
                    "let's wrap", "that covers it", "good session",
                    "i think we're good", "let's move on", "we've covered",
                    "sounds like a plan", "agreed on all points"
                ]
                if any(phrase in response.lower() for phrase in conclusive_phrases):
                    print(f"  → Detected natural wrap-up at turn {turn+1}")
                    break

        complete_session(session_id, artifacts={
            'type': session_type,
            'turns': len(conversation),
            'tool_calls_total': len(all_tool_calls),
            'participants': agents
        })
    finally:
        for agent_id in agents:
            update_agent(agent_id, state='idle', current_location='lounge')
            set_agent_busy(agent_id, False)
            trigger_inbox_request_if_idle(agent_id)

        print(f"  ✅ Meeting done\n")


# ============================================================
# RESOLVE AGENTS — Handle "random_2" etc.
# ============================================================


def resolve_agents(agents_spec) -> List[str]:
    """Resolve agent specification to actual agent list."""
    if isinstance(agents_spec, list):
        return agents_spec

    if agents_spec == "random_2":
        all_agents = get_all_agents()
        ids = [a['id'] for a in all_agents]
        return random.sample(ids, min(2, len(ids)))

    if agents_spec == "random_3":
        all_agents = get_all_agents()
        ids = [a['id'] for a in all_agents]
        return random.sample(ids, min(3, len(ids)))

    return [agents_spec]


# ============================================================
# RUN TASK — Dispatches solo or meeting based on type
# ============================================================


async def run_task(entry: dict):
    """Run a single schedule entry."""
    task_type = entry["type"]
    task_prompt = entry["task"]
    session_type = entry.get("session_type", "general")

    try:
        if task_type == "solo":
            agent_id = entry["agent"]
            await wait_until_agents_idle([agent_id])
            await run_solo(agent_id, task_prompt, session_type)

        elif task_type == "meeting":
            agents = resolve_agents(entry["agents"])
            await wait_until_agents_idle(agents)
            await run_meeting(agents, task_prompt, session_type)

    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()


# ============================================================
# SCHEDULER — Runs the daily schedule
# ============================================================


def start():
    """Start the engine. Schedules all tasks and runs the loop."""
    schedule_entries = get_schedule()

    print(f"\n🏢 One Person Company — Engine Starting")
    print(f"   Time: {datetime.now().strftime('%I:%M %p, %B %d %Y')}")
    print(f"   Tasks: {len(schedule_entries)}")
    print()

    start_discord_poller()

    for entry in schedule_entries:
        t = entry["time"]
        stype = entry.get("session_type", "?")

        if entry["type"] == "solo":
            label = f"{entry['agent']} → {stype}"
        else:
            agents = entry["agents"]
            if isinstance(agents, list):
                label = f"{', '.join(agents)} → {stype}"
            else:
                label = f"{agents} → {stype}"

        schedule.every().day.at(t).do(
            lambda e=entry: asyncio.run(run_task(e))
        )

        print(f"  {t}  {label}")

    print(f"\n⏳ Engine running. Ctrl+C to stop.\n")

    while True:
        schedule.run_pending()
        time.sleep(30)


# ============================================================
# MANUAL RUN — Run a specific task or the full day right now
# ============================================================


async def run_now(session_type: str = None):
    """
    Run task(s) immediately.

    Usage:
        run_now()                    # Run ALL tasks sequentially
        run_now("brainstorm")        # Run first brainstorm
        run_now("scan")              # Run first scan task
    """
    schedule_entries = get_schedule()
    if session_type is None:
        print("Running full day schedule now...")
        for entry in schedule_entries:
            await run_task(entry)
    else:
        for entry in schedule_entries:
            if entry.get("session_type") == session_type:
                await run_task(entry)
                return
        print(f"No task found with session_type='{session_type}'")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='One Person Company Engine')
    parser.add_argument('--run', type=str, help='Run a specific task type now (e.g. "brainstorm", "scan")')
    parser.add_argument('--run-all', action='store_true', help='Run all tasks now sequentially')
    parser.add_argument('--list', action='store_true', help='List the schedule')

    args = parser.parse_args()

    if args.list:
        print("\n📅 Daily Schedule:\n")
        for entry in get_schedule():
            t = entry["time"]
            stype = entry.get("session_type", "?")
            etype = entry["type"]
            if etype == "solo":
                print(f"  {t}  [{etype}]  {entry['agent']} → {stype}")
            else:
                agents = entry["agents"]
                label = ', '.join(agents) if isinstance(agents, list) else agents
                print(f"  {t}  [{etype}]  {label} → {stype}")
        print()

    elif args.run:
        asyncio.run(run_now(args.run))

    elif args.run_all:
        asyncio.run(run_now())

    else:
        try:
            start()
        except KeyboardInterrupt:
            print("\n👋 Engine stopped")
