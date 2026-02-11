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
import json
import random
import asyncio
import schedule
import time
from datetime import datetime
from typing import List, Dict, Optional
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

from lib.tool_runner import run_agent_with_tools, run_agent_step
from lib.tool_registry import get_tool_schemas
from lib.sessions import create_session, append_turn, complete_session
from lib.agents import load_agent_full, update_agent, get_all_agents


# ============================================================
# SCHEDULE — Edit this to change the entire company's day
# ============================================================
#
# type: "solo" or "meeting"
# agent/agents: who does the work
# task: what they're told to do (the prompt)
# session_type: label for the session record
#
# For meetings: agents take turns. Each sees the full history.
# Conversation continues until natural conclusion or max_turns.
#
# Add/remove entries freely. Drop a new line = new task.
# ============================================================

SCHEDULE = [
    # ---- Morning: Signal Gathering ----
    {
        "time": "08:00", "type": "solo",
        "agent": "strategist_lead",
        "session_type": "scan",
        "task": "Scan external sources (Twitter, Reddit, HN) for trending topics in AI, coding, developer tools, and personal branding. Look for emerging patterns, viral threads, and new narratives. Document any new patterns as learnings."
    },
    {
        "time": "08:30", "type": "solo",
        "agent": "analyst_lead",
        "session_type": "analysis",
        "task": "Review recent external signals in the database. Look for engagement patterns and benchmark data. Calculate what content formats and topics are performing well. Document findings as learnings."
    },

    # ---- CEO Standup ----
    {
        "time": "09:00", "type": "meeting",
        "agents": ["strategist_lead", "creator_lead", "analyst_lead"],
        "session_type": "ceo_standup",
        "task": "Daily standup with the CEO. Each of you: share what changed since yesterday, what you're confident about, and what you're uncertain about. Be specific and reference your recent learnings. After sharing, email the CEO a summary of the standup."
    },

    # ---- Mid-Morning Work ----
    {
        "time": "09:30", "type": "solo",
        "agent": "strategist_lead",
        "session_type": "scan",
        "task": "Do another scan of external sources. Focus on anything you might have missed earlier. Look for contrarian takes and underexplored angles. Write learnings for anything interesting."
    },
    {
        "time": "10:00", "type": "solo",
        "agent": "analyst_lead",
        "session_type": "analysis",
        "task": "Check the content pipeline. Review any ideas waiting for validation. Look at external signals related to those ideas. Assess market saturation and engagement potential. Write your analysis as learnings."
    },

    # ---- Brainstorm ----
    {
        "time": "10:30", "type": "meeting",
        "agents": ["strategist_lead", "creator_lead"],
        "session_type": "brainstorm",
        "task": "Time to brainstorm content ideas. Strategist: share the strongest themes and patterns you've spotted today. Creator: propose specific content angles, hooks, and formats based on those themes. Build on each other's ideas. When you land on strong ideas, write them as learnings."
    },

    # ---- Late Morning: Creation ----
    {
        "time": "11:00", "type": "solo",
        "agent": "creator_lead",
        "session_type": "drafting",
        "task": "Check the content pipeline for approved ideas. Pick the highest priority one and start drafting. Use your learnings about what performs well. Write your draft progress and any insights as learnings and memories."
    },
    {
        "time": "11:30", "type": "solo",
        "agent": "strategist_lead",
        "session_type": "scan",
        "task": "Quick scan of external sources. Look for anything time-sensitive or rapidly trending. If something urgent comes up, email the CEO."
    },

    # ---- Lunch: Watercooler ----
    {
        "time": "12:00", "type": "meeting",
        "agents": "random_2",
        "session_type": "watercooler",
        "task": "Casual watercooler chat. No agenda. Share something surprising you noticed, an assumption you want to question, or a wild idea you've been thinking about. Keep it relaxed and curious. If anything interesting comes up, note it as a learning."
    },

    # ---- Afternoon: Deep Work ----
    {
        "time": "13:00", "type": "solo",
        "agent": "strategist_lead",
        "session_type": "scan",
        "task": "Afternoon signal scan. Focus on what's trending right now. Compare with what you saw this morning — any shifts?"
    },
    {
        "time": "13:30", "type": "solo",
        "agent": "analyst_lead",
        "session_type": "analysis",
        "task": "Deep analysis session. Look at the bigger picture — what patterns emerge across all recent signals? Any market shifts? Write a synthesis as learnings."
    },

    # ---- Market Review ----
    {
        "time": "14:00", "type": "meeting",
        "agents": ["analyst_lead", "strategist_lead", "creator_lead"],
        "session_type": "market_review",
        "task": "Market review meeting. Analyst: present your data on the top content idea in the pipeline — market saturation, engagement benchmarks, similar content performance. Strategist: evaluate strategic fit. Creator: assess execution feasibility. Together, decide: approve, reshape, or kill the idea. Document your decision reasoning as learnings."
    },

    # ---- Afternoon Brainstorm ----
    {
        "time": "15:00", "type": "meeting",
        "agents": ["strategist_lead", "creator_lead"],
        "session_type": "brainstorm",
        "task": "Afternoon brainstorm. Build on what came out of the market review. Generate new angles or refine existing ideas. If you discussed anything interesting at the watercooler, bring those threads in."
    },

    # ---- Late Afternoon Work ----
    {
        "time": "15:30", "type": "solo",
        "agent": "creator_lead",
        "session_type": "drafting",
        "task": "Continue drafting or refining content. Use today's brainstorm outputs and analyst feedback. If a draft is ready, note it in your learnings."
    },
    {
        "time": "16:00", "type": "solo",
        "agent": "strategist_lead",
        "session_type": "scan",
        "task": "Late afternoon scan. Catch anything that emerged during the day. Focus on evening/international trends."
    },

    # ---- Evening Watercooler ----
    {
        "time": "16:30", "type": "meeting",
        "agents": "random_2",
        "session_type": "watercooler",
        "task": "End-of-day watercooler. How did today go? Anything unresolved? Any interesting threads worth picking up tomorrow? Keep it casual."
    },

    # ---- End of Day ----
    {
        "time": "17:00", "type": "solo",
        "agent": "analyst_lead",
        "session_type": "analysis",
        "task": "End-of-day performance review. Check if any posted content got engagement today. Compare against benchmarks. Document what worked and what didn't as learnings."
    },
    {
        "time": "17:30", "type": "solo",
        "agent": "strategist_lead",
        "session_type": "scan",
        "task": "Final scan of the day. Quick sweep for anything you missed. Write a brief end-of-day learning summarizing the most important pattern or theme from today."
    },
]


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
    
    # Update state
    update_agent(agent_id, state=f'working_{session_type}', current_location='desk')
    
    # Create session
    session_id = create_session(
        type=session_type,
        participants=[agent_id],
        initiator='engine',
        intent=task[:200]
    )
    
    # Run the agent — they decide what tools to use
    full_task = f"Current time: {now}\n\n{task}"
    
    response, tool_calls = await run_agent_step(
        agent_id=agent_id,
        task=full_task,
        model="gpt-4o"
    )
    
    # Store what happened
    append_turn(session_id, speaker=agent_id, text=response)
    
    print(f"  Response: {response[:150]}...")
    print(f"  Tools used: {len(tool_calls)}")
    for tc in tool_calls:
        print(f"    🔧 {tc['tool']}")
    
    # Complete
    complete_session(session_id, artifacts={
        'type': session_type,
        'response': response,
        'tool_calls': tool_calls
    })
    
    update_agent(agent_id, state='idle', current_location='lounge')
    print(f"  ✅ Done\n")


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
    
    # Update states
    for agent_id in agents:
        update_agent(agent_id, state=f'in_{session_type}', current_location='meeting_room')
    
    # Create session
    session_id = create_session(
        type=session_type,
        participants=agents,
        initiator='engine',
        intent=task[:200]
    )
    
    conversation = []  # List of {"speaker": ..., "message": ...}
    all_tool_calls = []
    
    for turn in range(max_turns):
        # Pick speaker: rotate through agents
        speaker = agents[turn % len(agents)]
        agent_data = load_agent_full(speaker)
        soul = agent_data.get('soul_instructions', f'You are {speaker}.')
        
        # Build the conversation context
        if turn == 0:
            user_msg = f"Current time: {now}\nMeeting type: {session_type}\nParticipants: {', '.join(agents)}\n\n{task}"
        else:
            history = "\n\n".join([
                f"**{c['speaker']}**: {c['message']}"
                for c in conversation
            ])
            user_msg = f"Current time: {now}\nMeeting type: {session_type}\nParticipants: {', '.join(agents)}\n\nMeeting topic:\n{task}\n\nConversation so far:\n{history}\n\nIt's your turn. Respond naturally. When the conversation has reached a natural conclusion, end your message with [DONE]."
        
        # Run this agent's turn with their tools
        response, tool_calls = await run_agent_with_tools(
            agent_id=speaker,
            system_prompt=soul,
            user_prompt=user_msg,
            model="gpt-4o"
        )
        
        # Track
        conversation.append({"speaker": speaker, "message": response})
        all_tool_calls.extend(tool_calls)
        append_turn(session_id, speaker=speaker, text=response, turn=turn)
        
        print(f"  [{turn+1}] {speaker}: {response[:100]}...")
        for tc in tool_calls:
            print(f"       🔧 {tc['tool']}")
        
        # Check for natural conclusion
        if "[DONE]" in response or "[done]" in response:
            print(f"  → Natural conclusion at turn {turn+1}")
            break
        
        # Min turns: at least 2 per agent before we allow ending
        if turn >= len(agents) * 2:
            # Check if response sounds conclusive (simple heuristic)
            conclusive_phrases = [
                "let's wrap", "that covers it", "good session",
                "i think we're good", "let's move on", "we've covered",
                "sounds like a plan", "agreed on all points"
            ]
            if any(phrase in response.lower() for phrase in conclusive_phrases):
                print(f"  → Detected natural wrap-up at turn {turn+1}")
                break
    
    # Complete
    complete_session(session_id, artifacts={
        'type': session_type,
        'turns': len(conversation),
        'tool_calls_total': len(all_tool_calls),
        'participants': agents
    })
    
    # Reset states
    for agent_id in agents:
        update_agent(agent_id, state='idle', current_location='lounge')
    
    print(f"  ✅ Meeting done — {len(conversation)} turns, {len(all_tool_calls)} tool calls\n")


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
    
    return [agents_spec]  # Single agent name


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
            await run_solo(agent_id, task_prompt, session_type)
        
        elif task_type == "meeting":
            agents = resolve_agents(entry["agents"])
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
    print(f"\n🏢 One Person Company — Engine Starting")
    print(f"   Time: {datetime.now().strftime('%I:%M %p, %B %d %Y')}")
    print(f"   Tasks: {len(SCHEDULE)}")
    print()
    
    # Schedule each task
    for entry in SCHEDULE:
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
    if session_type is None:
        print("Running full day schedule now...")
        for entry in SCHEDULE:
            await run_task(entry)
    else:
        for entry in SCHEDULE:
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
        for entry in SCHEDULE:
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
        # Default: start the scheduler
        try:
            start()
        except KeyboardInterrupt:
            print("\n👋 Engine stopped")

