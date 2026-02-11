"""
1-on-1 Session Worker
Agent-initiated conversations. Any agent can "call" another for a quick chat.

This is the tool agents will invoke when they want to discuss something
with a specific colleague — like a watercooler but intentional.
"""

import os
import json
import asyncio
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()

from lib.llm import chat_completion, chat_completion_json
from lib.sessions import create_session, append_turn, complete_session, add_learning_to_session
from lib.learnings import write_learning, query_learnings
from lib.memories import store_memory, query_memories
from lib.agents import update_agent


async def run_one_on_one(
    initiator: str,
    target: str,
    reason: str,
    num_turns: int = 6
):
    """
    Run agent-initiated 1-on-1 conversation.
    
    Args:
        initiator: Agent who requested the chat
        target: Agent being invited
        reason: Why they want to talk (the initiator's motivation)
        num_turns: Conversation length (default: 6)
    
    This function is designed to be called as an agent tool:
        request_one_on_one(target="creator_lead", reason="Want to discuss hook strategies")
    """
    participants = [initiator, target]
    print(f"Starting 1-on-1: {initiator} → {target}")
    print(f"  Reason: {reason}")
    
    # Update states
    for agent_id in participants:
        update_agent(agent_id, state='in_1on1', current_location='meeting_room')
    
    # Create session
    session_id = create_session(
        type='one_on_one',
        participants=participants,
        initiator=initiator,
        intent=reason
    )
    
    conversation_history = []
    
    # Initiator opens with their reason
    opener = generate_1on1_turn(
        agent_id=initiator,
        other_agent=target,
        reason=reason,
        conversation_history=[],
        is_opener=True
    )
    
    append_turn(session_id, speaker=initiator, text=opener, turn=0)
    conversation_history.append({'speaker': initiator, 'message': opener})
    print(f"  [1] {initiator}: {opener[:80]}...")
    
    # Back and forth
    for turn in range(1, num_turns):
        speaker = participants[turn % 2]
        other = participants[(turn + 1) % 2]
        
        message = generate_1on1_turn(
            agent_id=speaker,
            other_agent=other,
            reason=reason,
            conversation_history=conversation_history,
            is_opener=False
        )
        
        append_turn(session_id, speaker=speaker, text=message, turn=turn)
        conversation_history.append({'speaker': speaker, 'message': message})
        print(f"  [{turn+1}] {speaker}: {message[:80]}...")
        
        await asyncio.sleep(1)
    
    # Extract takeaways
    takeaways = extract_takeaways(conversation_history, reason)
    
    # --- Write learnings + memories for both agents ---
    for agent_id in participants:
        other = [p for p in participants if p != agent_id][0]
        my_turns = [h['message'] for h in conversation_history if h['speaker'] == agent_id]
        
        # Memory: detailed record of the 1-on-1
        store_memory(
            agent_id=agent_id,
            memory_type='one_on_one',
            summary=f"Had a 1-on-1 with {other} about: {reason}. {'I initiated.' if agent_id == initiator else f'{initiator} reached out to me.'}",
            full_content={
                'with': other,
                'reason': reason,
                'my_turns': my_turns,
                'takeaways': takeaways,
                'i_initiated': agent_id == initiator
            },
            emotional_valence='collaborative',
            tags=['one_on_one', 'collaboration', other]
        )
        
        # Learning from the conversation
        if takeaways:
            for takeaway in takeaways[:2]:  # Max 2 learnings per agent
                learning = write_learning(
                    agent_id=agent_id,
                    type=takeaway.get('type', 'insight'),
                    statement=takeaway['takeaway'],
                    confidence=takeaway.get('confidence', 0.6),
                    tags=['one_on_one', other],
                    source_session_id=session_id
                )
                if learning:
                    add_learning_to_session(session_id, learning['id'])
    
    # Complete session
    complete_session(session_id, artifacts={
        'initiator': initiator,
        'target': target,
        'reason': reason,
        'takeaways': takeaways,
        'turns': len(conversation_history)
    })
    
    # Reset states
    for agent_id in participants:
        update_agent(agent_id, state='idle', current_location='lounge')
    
    print(f"✅ 1-on-1 completed: {session_id}")
    return {'session_id': str(session_id), 'takeaways': takeaways}


def generate_1on1_turn(
    agent_id: str, other_agent: str, reason: str,
    conversation_history: List[Dict], is_opener: bool
) -> str:
    """Generate one turn of 1-on-1 conversation."""
    # Get agent's recent learnings and memories for context
    learnings = query_learnings(agent_id, limit=5, min_confidence=0.5)
    memories_with_other = query_memories(agent_id, tags=[other_agent], limit=3)
    
    learning_ctx = "\n".join([f"- {l['statement']}" for l in learnings[:3]]) if learnings else "No recent learnings"
    memory_ctx = "\n".join([f"- {m['summary']}" for m in memories_with_other[:2]]) if memories_with_other else "No past interactions"
    
    if is_opener:
        user_msg = f"""You are {agent_id}. You reached out to {other_agent} for a 1-on-1.

        Reason: {reason}

        Your recent learnings:
        {learning_ctx}

        Past interactions with {other_agent}:
        {memory_ctx}

        Open the conversation. Explain what you want to discuss and why. Be specific (2-3 sentences)."""
    else:
        recent = "\n".join([f"{h['speaker']}: {h['message']}" for h in conversation_history[-3:]])
        user_msg = f"""You are {agent_id} in a 1-on-1 with {other_agent}.

            Topic: {reason}

            Recent:
            {recent}

            Your learnings:
            {learning_ctx}

            Past interactions with {other_agent}:
            {memory_ctx}

            Respond naturally. Share your perspective, ask questions, or build on what was said (2-3 sentences)."""
    
    return chat_completion(
        system=f"You are {agent_id} in a focused 1-on-1 conversation. Be specific, collaborative, and honest. Keep it brief (2-3 sentences).",
        user=user_msg
    ).strip()


def extract_takeaways(conversation_history: List[Dict], reason: str) -> List[Dict]:
    """Extract takeaways from 1-on-1 conversation."""
    full_convo = "\n".join([f"{h['speaker']}: {h['message']}" for h in conversation_history])
    
    result_str = chat_completion_json(
        system='Extract key takeaways from this 1-on-1 conversation. Return JSON: {"takeaways": [{"takeaway": "1 sentence", "type": "insight|strategy|pattern|lesson", "confidence": 0.5-0.8}]}. 1-3 takeaways. Empty array if nothing concrete.',
        user=f"Reason for meeting: {reason}\n\nConversation:\n{full_convo}",
        model="gpt-4o"
    )
    
    try:
        result = json.loads(result_str)
        return result.get('takeaways', [])
    except (json.JSONDecodeError, AttributeError):
        return []


# --- Agent Tool Definition ---
# This is the function schema agents can call

REQUEST_ONE_ON_ONE_TOOL = {
    "type": "function",
    "function": {
        "name": "request_one_on_one",
        "description": "Request a 1-on-1 conversation with another agent. Use this when you want to discuss something specific with a colleague, need their perspective, or want to collaborate on an idea.",
        "parameters": {
            "type": "object",
            "properties": {
                "target_agent": {
                    "type": "string",
                    "description": "The agent_id you want to talk to (e.g. 'creator_lead', 'strategist_lead', 'analyst_lead')"
                },
                "reason": {
                    "type": "string",
                    "description": "Why you want to talk to them (be specific, e.g. 'Want to discuss whether our technical content angle is resonating')"
                }
            },
            "required": ["target_agent", "reason"]
        }
    }
}


async def handle_tool_call(calling_agent: str, tool_name: str, arguments: dict):
    """Handle when an agent calls the request_one_on_one tool."""
    if tool_name == "request_one_on_one":
        return await run_one_on_one(
            initiator=calling_agent,
            target=arguments['target_agent'],
            reason=arguments['reason']
        )


if __name__ == '__main__':
    # Test: strategist wants to talk to creator
    asyncio.run(run_one_on_one(
        initiator='strategist_lead',
        target='creator_lead',
        reason='Want to discuss which content angles are resonating most'
    ))

