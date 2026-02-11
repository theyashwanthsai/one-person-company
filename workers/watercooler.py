"""
Watercooler Session Worker
Casual conversations between agents for weak signal emergence.
"""

import os
import json
import asyncio
import random
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()

from lib.llm import chat_completion, chat_completion_json
from lib.sessions import create_session, append_turn, complete_session, add_learning_to_session
from lib.learnings import write_learning, query_learnings
from lib.memories import store_memory
from lib.agents import update_agent, get_all_agents


CASUAL_TOPICS = [
    "What's the most surprising thing you learned recently?",
    "If you could change one thing about how we work, what would it be?",
    "What content have you seen lately that really stood out?",
    "What patterns are you noticing that others might be missing?",
    "What's something you're uncertain about but haven't raised yet?",
    "If we had unlimited resources, what would you want to try?",
    "What trends are you seeing that worry you?",
    "What trends are you seeing that excite you?",
    "What's the biggest gap in our current approach?",
    "What feedback have you been sitting on?",
    "What's a wild idea you've been thinking about?",
    "What are we not talking about that we should be?",
    "What assumption should we question?",
]


async def run_watercooler_session(
    participants: List[str] = None,
    num_turns: int = 5
):
    """
    Run watercooler session - casual conversation for weak signals.
    
    - Random 2-3 agents, random topic
    - Short (3-5 turns), high creativity
    - Extracts weak signals as learnings
    - Stores conversation memories for each agent
    - No action items
    """
    # Random participant selection
    if participants is None:
        all_agents = get_all_agents()
        agent_ids = [a['id'] for a in all_agents]
        participants = random.sample(agent_ids, min(random.randint(2, 3), len(agent_ids)))
    
    print(f"Starting watercooler with: {participants}")
    
    # Update states
    for agent_id in participants:
        update_agent(agent_id, state='at_watercooler', current_location='watercooler')
    
    topic = random.choice(CASUAL_TOPICS)
    print(f"  Topic: {topic}")
    
    # Create session
    session_id = create_session(
        type='watercooler',
        participants=participants,
        initiator='system',
        intent=f'Casual chat: {topic}'
    )
    
    conversation_history = []
    actual_turns = random.randint(3, num_turns)
    
    for turn in range(actual_turns):
        # Pick speaker (avoid repeating last)
        if turn == 0:
            speaker = participants[0]
        else:
            others = [p for p in participants if p != conversation_history[-1]['speaker']]
            speaker = random.choice(others if others else participants)
        
        message = generate_watercooler_turn(
            agent_id=speaker,
            topic=topic,
            conversation_history=conversation_history,
            participants=participants
        )
        
        append_turn(session_id, speaker=speaker, text=message, turn=turn)
        conversation_history.append({'speaker': speaker, 'message': message})
        
        print(f"  [{turn+1}] {speaker}: {message[:80]}...")
        await asyncio.sleep(1)
    
    # Extract weak signals
    signals = extract_weak_signals(conversation_history, topic)
    
    # --- Write learnings + memories for each agent ---
    for agent_id in participants:
        my_turns = [h['message'] for h in conversation_history if h['speaker'] == agent_id]
        others = [p for p in participants if p != agent_id]
        
        # Memory: what happened at the watercooler
        store_memory(
            agent_id=agent_id,
            memory_type='watercooler',
            summary=f"Had a casual chat with {', '.join(others)} about: {topic}",
            full_content={
                'topic': topic,
                'my_turns': my_turns,
                'participants': participants
            },
            emotional_valence='casual',
            tags=['watercooler', 'casual']
        )
    
    # Store weak signals as learnings
    for signal in signals:
        agent_for_signal = signal.get('agent_id', participants[0])
        if agent_for_signal not in participants:
            agent_for_signal = participants[0]
        
        learning = write_learning(
            agent_id=agent_for_signal,
            type='pattern',
            statement=signal['signal'],
            confidence=signal.get('confidence', 0.5),
            tags=['watercooler', 'weak_signal', signal.get('signal_type', 'observation')],
            source_session_id=session_id
        )
        if learning:
            add_learning_to_session(session_id, learning['id'])
    
    if signals:
        print(f"  Extracted {len(signals)} weak signals")
    
    # Complete session
    complete_session(session_id, artifacts={
        'topic': topic,
        'turns': len(conversation_history),
        'weak_signals': signals
    })
    
    # Reset states
    for agent_id in participants:
        update_agent(agent_id, state='idle', current_location='lounge')
    
    print(f"✅ Watercooler completed: {session_id}")
    return {'session_id': str(session_id), 'signals': signals}


def generate_watercooler_turn(
    agent_id: str, topic: str,
    conversation_history: List[Dict], participants: List[str]
) -> str:
    """Generate one casual turn."""
    learnings = query_learnings(agent_id, limit=3, min_confidence=0.4)
    ctx = "\n".join([f"- {l['statement']}" for l in learnings[:3]]) if learnings else "No recent thoughts"
    
    if not conversation_history:
        user_msg = f'Topic: {topic}\n\nYour recent thoughts:\n{ctx}\n\nRespond casually (1-2 sentences).'
    else:
        recent = "\n".join([f"{h['speaker']}: {h['message']}" for h in conversation_history[-2:]])
        others = [p for p in participants if p != agent_id]
        user_msg = f'Topic: {topic}\n\nRecent chat:\n{recent}\n\nYour thoughts:\n{ctx}\n\nRespond naturally (1-2 sentences).'
    
    return chat_completion(
        system=f"You are {agent_id} at the watercooler. Casual, brief (1-2 sentences), no formal recommendations. Share observations, ask questions, be curious.",
        user=user_msg,
        temperature=0.9,
        max_tokens=100
    ).strip()


def extract_weak_signals(conversation_history: List[Dict], topic: str) -> List[Dict]:
    """Extract weak signals from conversation."""
    full_convo = "\n".join([f"{h['speaker']}: {h['message']}" for h in conversation_history])
    
    result_str = chat_completion_json(
        system='Extract subtle weak signals from this casual conversation. Return JSON: {"signals": [{"agent_id": "who", "signal": "1 sentence", "signal_type": "concern|opportunity|observation", "confidence": 0.4-0.6}]}. 0-2 signals max. Empty array if pure small talk.',
        user=f"Topic: {topic}\n\nConversation:\n{full_convo}",
        model="gpt-4o"
    )
    
    try:
        result = json.loads(result_str)
        return result.get('signals', [])
    except (json.JSONDecodeError, AttributeError):
        return []


if __name__ == '__main__':
    asyncio.run(run_watercooler_session())
