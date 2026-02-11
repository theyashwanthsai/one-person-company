"""
CEO Daily Standup Worker
Email-based async standup between CEO and agents.
"""

import os
import json
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()

from lib.llm import chat_completion
from lib.email_client import EmailClient
from lib.sessions import create_session, append_turn, complete_session, add_learning_to_session
from lib.learnings import write_learning, query_learnings
from lib.memories import store_memory
from lib.agents import update_agent

email_client = EmailClient()


async def run_ceo_standup(agents: List[str] = None):
    """
    Run CEO standup session.
    
    Flow:
        1. Send 5-min reminder to CEO
        2. Agents generate standup responses (LLM)
        3. Send all responses to CEO via email
        4. Wait for CEO feedback
        5. Each agent writes learnings + memories
        6. Process CEO feedback (boost/dampen/focus)
        7. Complete session
    """
    if agents is None:
        agents = ['strategist_lead', 'creator_lead', 'analyst_lead']
    
    print(f"Starting CEO standup with: {agents}")
    
    session_id_str = f"standup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    scheduled_time = (datetime.now() + timedelta(minutes=5)).strftime('%I:%M %p')
    
    # 1. Send reminder
    print("  Sending reminder to CEO...")
    email_client.send_reminder(session_id_str, scheduled_time)
    
    await asyncio.sleep(5 * 60)  # Wait 5 minutes
    
    # 2. Create session
    session_id = create_session(
        type='ceo_standup',
        participants=agents + ['ceo'],
        initiator='system',
        intent='Daily CEO standup'
    )
    
    # Update agent states
    for agent_id in agents:
        update_agent(agent_id, state='in_standup', current_location='meeting_room')
    
    # 3. Generate agent responses
    print("  Generating agent responses...")
    agent_responses = {}
    
    for i, agent_id in enumerate(agents):
        response = generate_agent_standup(agent_id)
        agent_responses[agent_id] = response
        
        formatted = format_standup(agent_id, response)
        append_turn(session_id, speaker=agent_id, text=formatted, turn=i)
    
    # 4. Email responses to CEO
    print("  Sending updates to CEO...")
    send_standup_email(session_id_str, agent_responses)
    
    email_client.send_questionnaire(session_id_str, agents)
    
    # 5. Each agent writes memory of standup
    for agent_id in agents:
        response = agent_responses[agent_id]
        
        store_memory(
            agent_id=agent_id,
            memory_type='standup',
            summary=f"Gave standup update. Changed: {response.get('changed', 'nothing')}. Confident about: {response.get('confident', 'nothing specific')}. Uncertain about: {response.get('uncertain', 'nothing specific')}.",
            full_content=response,
            emotional_valence='focused',
            tags=['standup', 'ceo']
        )
    
    # 6. Wait for CEO feedback
    print("  Waiting for CEO feedback...")
    ceo_feedback = await wait_for_ceo_feedback(session_id_str, timeout_hours=24)
    
    if ceo_feedback:
        append_turn(session_id, speaker='ceo', text=ceo_feedback, turn=len(agents))
        
        # Store CEO feedback memory for each agent
        for agent_id in agents:
            store_memory(
                agent_id=agent_id,
                memory_type='ceo_feedback',
                summary=f"CEO responded to standup: {ceo_feedback[:100]}...",
                full_content={'feedback': ceo_feedback},
                emotional_valence='motivated',
                tags=['standup', 'ceo_feedback']
            )
        
        # Process commands
        process_ceo_feedback(session_id, ceo_feedback, agents)
    
    # 7. Extract cross-agent learnings
    uncertainties = [f"{a}: {r.get('uncertain', '')}" for a, r in agent_responses.items() if r.get('uncertain')]
    if len(uncertainties) >= 2:
        write_learning(
            agent_id='strategist_lead',
            type='pattern',
            statement=f"Team uncertainty pattern: {'; '.join(uncertainties)}",
            confidence=0.7,
            tags=['standup', 'team_pattern', 'uncertainty'],
            source_session_id=session_id
        )
    
    # 8. Complete
    complete_session(session_id, artifacts={
        'agent_responses': agent_responses,
        'ceo_feedback': ceo_feedback,
        'agents': agents
    })
    
    for agent_id in agents:
        update_agent(agent_id, state='idle', current_location='lounge')
    
    print(f"✅ CEO standup completed: {session_id}")


def generate_agent_standup(agent_id: str) -> Dict[str, str]:
    """Generate standup response for an agent."""
    learnings = query_learnings(agent_id, limit=10, min_confidence=0.4)
    ctx = "\n".join([f"- [{l['type']}] {l['statement']} (conf: {l['confidence']})" for l in learnings[:5]]) if learnings else "No recent learnings"
    
    text = chat_completion(
        system="You are an AI agent giving a standup update. Be brief, specific, honest. Answer each question in 2-3 sentences.",
        user=f"You are {agent_id}.\n\nRecent learnings:\n{ctx}\n\nAnswer:\n1. What changed since last time?\n2. What are you confident about?\n3. What are you uncertain about?"
    )
    
    return parse_standup(text)


def parse_standup(text: str) -> Dict[str, str]:
    """Parse standup response into sections."""
    import re
    result = {'changed': '', 'confident': '', 'uncertain': ''}
    
    m = re.search(r'1\.?\s*(.+?)(?=2\.|$)', text, re.DOTALL)
    if m: result['changed'] = m.group(1).strip()
    
    m = re.search(r'2\.?\s*(.+?)(?=3\.|$)', text, re.DOTALL)
    if m: result['confident'] = m.group(1).strip()
    
    m = re.search(r'3\.?\s*(.+?)$', text, re.DOTALL)
    if m: result['uncertain'] = m.group(1).strip()
    
    return result


def format_standup(agent_id: str, response: Dict[str, str]) -> str:
    """Format for email/session."""
    return f"**{agent_id}**\n\n📌 What changed:\n{response.get('changed', 'No updates')}\n\n✅ Confident about:\n{response.get('confident', 'Nothing specific')}\n\n❓ Uncertain about:\n{response.get('uncertain', 'Nothing specific')}"


def send_standup_email(session_id_str: str, responses: Dict[str, Dict[str, str]]):
    """Send all agent responses to CEO."""
    subject = f"📊 Standup Updates - {datetime.now().strftime('%B %d, %Y')}"
    
    body = "Your team's standup updates:\n\n" + "-" * 60 + "\n\n"
    for agent_id, response in responses.items():
        body += format_standup(agent_id, response) + f"\n\n{'-' * 60}\n\n"
    
    body += "\nReply with feedback. Commands: boost [agent], dampen [agent], focus on [topic]\n"
    
    email_client._send_email(email_client.ceo_email, subject, body, session_id=session_id_str)


async def wait_for_ceo_feedback(session_id_str: str, timeout_hours: int = 24) -> str:
    """Wait for CEO reply."""
    timeout = datetime.now() + timedelta(hours=timeout_hours)
    
    while datetime.now() < timeout:
        replies = email_client.parse_replies(session_id_str)
        ceo_reply = replies.get(email_client.ceo_email)
        if ceo_reply:
            return ceo_reply
        await asyncio.sleep(5 * 60)
    
    print("  ⚠️ CEO feedback timeout")
    return None


def process_ceo_feedback(session_id, feedback: str, agents: List[str]):
    """Process CEO feedback commands."""
    from supabase import create_client
    sb = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY'))
    
    feedback_lower = feedback.lower()
    
    for agent_id in agents:
        if f'boost {agent_id}' in feedback_lower:
            sb.rpc('boost_agent_learnings', {'p_agent_id': agent_id, 'p_boost_factor': 0.1}).execute()
            print(f"  ✅ Boosted {agent_id}")
        
        if f'dampen {agent_id}' in feedback_lower:
            sb.rpc('dampen_agent_learnings', {'p_agent_id': agent_id, 'p_dampen_factor': 0.1}).execute()
            print(f"  📉 Dampened {agent_id}")
    
    if 'focus on' in feedback_lower:
        directive = feedback_lower.split('focus on')[1].strip().split('.')[0].split('\n')[0]
        for agent_id in agents:
            write_learning(
                agent_id=agent_id,
                type='strategy',
                statement=f"CEO directive: Focus on {directive}",
                confidence=0.9,
                tags=['ceo_directive', 'strategy'],
                source_session_id=session_id,
                ceo_boosted=True
            )
        print(f"  🎯 Directive set: focus on {directive}")


if __name__ == '__main__':
    asyncio.run(run_ceo_standup())
