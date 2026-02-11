"""
Brainstorm Session Worker
Turn-by-turn creative ideation between Strategist and Creator agents.
"""

import os
import json
import asyncio
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()

from lib.llm import chat_completion, chat_completion_json
from lib.sessions import create_session, append_turn, complete_session, add_learning_to_session
from lib.learnings import write_learning, query_learnings
from lib.memories import store_memory


async def run_brainstorm_session(
    participants: List[str] = None,
    topic: str = None,
    num_turns: int = 10
):
    """
    Run brainstorm session between agents.
    
    Flow:
        1. Create session
        2. Auto-select topic from learnings if needed
        3. Turn-by-turn creative dialogue (10 turns)
        4. Extract content ideas → content_pipeline
        5. Each agent writes learnings + memories
        6. Complete session
    """
    if participants is None:
        participants = ['strategist_lead', 'creator_lead']
    
    print(f"Starting brainstorm with: {participants}")
    
    # Update agent states
    from lib.agents import update_agent
    for agent_id in participants:
        update_agent(agent_id, state='in_brainstorm', current_location='meeting_room')
    
    # Auto-select topic
    if topic is None:
        topic = select_brainstorm_topic(participants[0])
    
    print(f"Topic: {topic}")
    
    # Create session
    session_id = create_session(
        type='brainstorm',
        participants=participants,
        initiator='system',
        intent=f'Creative brainstorming on: {topic}'
    )
    
    conversation_history = []
    
    # Turn-by-turn conversation
    for turn in range(num_turns):
        current_speaker = participants[turn % len(participants)]
        
        message = generate_brainstorm_turn(
            agent_id=current_speaker,
            topic=topic,
            conversation_history=conversation_history,
            turn_number=turn,
            total_turns=num_turns
        )
        
        append_turn(session_id, speaker=current_speaker, text=message, turn=turn)
        conversation_history.append({'speaker': current_speaker, 'message': message})
        
        print(f"  [{turn+1}/{num_turns}] {current_speaker}: {message[:100]}...")
        await asyncio.sleep(1)
    
    # Extract content ideas
    ideas = extract_content_ideas(conversation_history)
    print(f"  Extracted {len(ideas)} content ideas")
    
    # Store ideas in content_pipeline
    from supabase import create_client
    supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY'))
    
    for idea in ideas:
        supabase.table('content_pipeline').insert({
            'title': idea['title'],
            'description': idea.get('description', ''),
            'status': 'idea',
            'source_session_id': str(session_id),
            'tags': idea.get('tags', []),
            'priority': idea.get('priority', 'medium')
        }).execute()
    
    # --- Write learnings + memories for each agent ---
    for agent_id in participants:
        # Memory: record of this brainstorm
        store_memory(
            agent_id=agent_id,
            memory_type='brainstorm',
            summary=f"Brainstormed about '{topic}' with {', '.join([p for p in participants if p != agent_id])}. Generated {len(ideas)} ideas.",
            full_content={
                'topic': topic,
                'ideas': [i['title'] for i in ideas],
                'my_turns': [h['message'] for h in conversation_history if h['speaker'] == agent_id]
            },
            emotional_valence='energized' if len(ideas) >= 3 else 'neutral',
            tags=['brainstorm', 'collaboration']
        )
        
        # Learning: what came out of this session
        if ideas:
            top_idea = ideas[0]
            learning = write_learning(
                agent_id=agent_id,
                type='insight',
                statement=f"Brainstorm produced strong angle: {top_idea['title']}",
                confidence=0.6,
                tags=['content', 'ideation'] + top_idea.get('tags', [])[:2],
                source_session_id=session_id
            )
            if learning:
                add_learning_to_session(session_id, learning['id'])
    
    # Meta-learning for strategist
    if len(ideas) >= 3:
        write_learning(
            agent_id=participants[0],
            type='pattern',
            statement=f"Brainstorm on '{topic}' was highly productive ({len(ideas)} ideas). This topic area has creative potential.",
            confidence=0.65,
            tags=['brainstorm', 'meta', 'productivity'],
            source_session_id=session_id
        )
    
    # Complete session
    complete_session(session_id, artifacts={
        'topic': topic,
        'ideas': ideas,
        'turns': len(conversation_history)
    })
    
    # Reset states
    for agent_id in participants:
        update_agent(agent_id, state='idle', current_location='lounge')
    
    print(f"✅ Brainstorm completed: {session_id}")
    return {'session_id': str(session_id), 'ideas': ideas}


def select_brainstorm_topic(agent_id: str) -> str:
    """Auto-select topic from recent learnings."""
    learnings = query_learnings(agent_id, types=['insight', 'pattern'], limit=10, min_confidence=0.6)
    
    if not learnings:
        return "Content strategy and audience engagement"
    
    context = "\n".join([f"- {l['statement']}" for l in learnings[:5]])
    
    return chat_completion(
        system="Suggest ONE specific, actionable brainstorm topic (10 words max). Just the title, nothing else.",
        user=f"Based on these insights:\n{context}"
    ).strip().strip('"')


def generate_brainstorm_turn(
    agent_id: str, topic: str, conversation_history: List[Dict],
    turn_number: int, total_turns: int
) -> str:
    """Generate one turn of brainstorm conversation."""
    learnings = query_learnings(agent_id, limit=5, min_confidence=0.5)
    learning_ctx = "\n".join([f"- [{l['type']}] {l['statement']}" for l in learnings[:3]]) if learnings else "No recent learnings"
    
    role_map = {
        'strategist_lead': 'Strategic thinker sharing themes and high-level insights',
        'creator_lead': 'Creative writer proposing content angles and hooks',
        'analyst_lead': 'Data analyst bringing numbers and benchmarks'
    }
    role = role_map.get(agent_id, 'Thoughtful contributor')
    
    if turn_number == 0:
        user_msg = f'You are {agent_id}, {role}.\n\nBrainstorm topic: "{topic}"\n\nOpen with your initial thoughts. Reference your learnings if relevant.\n\nLearnings:\n{learning_ctx}\n\nKeep it brief (2-3 sentences).'
    elif turn_number < total_turns - 2:
        recent = "\n".join([f"{h['speaker']}: {h['message']}" for h in conversation_history[-3:]])
        user_msg = f'You are {agent_id}, {role}.\n\nTopic: "{topic}"\n\nRecent:\n{recent}\n\nYour learnings:\n{learning_ctx}\n\nBuild on what was said. Keep it brief (2-3 sentences).'
    else:
        all_msgs = "\n".join([f"{h['speaker']}: {h['message']}" for h in conversation_history])
        user_msg = f'You are {agent_id}, {role}.\n\nTopic: "{topic}"\n\nFull conversation:\n{all_msgs}\n\nSynthesize and propose concrete content ideas. Keep it brief (2-3 sentences).'
    
    return chat_completion(
        system=f"You are {agent_id} in a brainstorm. Role: {role}. Be specific, brief (2-3 sentences), no meta-commentary.",
        user=user_msg,
        model="gpt-4o"
    ).strip()


def extract_content_ideas(conversation_history: List[Dict]) -> List[Dict]:
    """Extract concrete content ideas from conversation."""
    full_convo = "\n".join([f"{h['speaker']}: {h['message']}" for h in conversation_history])
    
    result_str = chat_completion_json(
        system="Extract actionable content ideas from this brainstorm. Return JSON with key 'ideas' containing array of {title, description, tags, priority}. 2-5 ideas max. If none are clear, return empty array.",
        user=full_convo,
        model="gpt-4o"
    )
    
    try:
        result = json.loads(result_str)
        return result.get('ideas', [])
    except (json.JSONDecodeError, AttributeError):
        return []


if __name__ == '__main__':
    asyncio.run(run_brainstorm_session())
