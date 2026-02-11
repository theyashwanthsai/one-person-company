"""
Market Review Session Worker
Analyst-led content validation against market data and benchmarks.
"""

import os
import json
import asyncio
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()

from supabase import create_client
from lib.llm import chat_completion, chat_completion_json
from lib.sessions import create_session, append_turn, complete_session, add_learning_to_session
from lib.learnings import write_learning, query_learnings
from lib.memories import store_memory
from lib.agents import update_agent

supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY'))


async def run_market_review_session(
    content_id: Optional[str] = None,
    participants: List[str] = None
):
    """
    Run market review session to validate content ideas.
    
    Flow:
        1. Pick top unreviewed idea from content_pipeline
        2. Analyst scans external_signals for similar content
        3. Three-way evaluation (Analyst + Strategist + Creator)
        4. Group decision: approve / reshape / kill
        5. Update content_pipeline status
        6. Each agent writes learnings + memories
    """
    if participants is None:
        participants = ['analyst_lead', 'strategist_lead', 'creator_lead']
    
    print(f"Starting market review with: {participants}")
    
    # Update states
    for agent_id in participants:
        update_agent(agent_id, state='in_market_review', current_location='meeting_room')
    
    # Pick content to review
    if content_id is None:
        result = supabase.table('content_pipeline')\
            .select('id')\
            .eq('status', 'idea')\
            .order('created_at', desc=True)\
            .limit(1)\
            .execute()
        
        if not result.data:
            print("❌ No content ideas to review")
            for agent_id in participants:
                update_agent(agent_id, state='idle', current_location='lounge')
            return None
        
        content_id = result.data[0]['id']
    
    # Fetch content
    content = supabase.table('content_pipeline')\
        .select('*')\
        .eq('id', content_id)\
        .single()\
        .execute()
    
    content_data = content.data
    print(f"  Reviewing: {content_data['title']}")
    
    # Create session
    session_id = create_session(
        type='market_review',
        participants=participants,
        initiator='system',
        intent=f"Market validation: {content_data['title']}"
    )
    
    # Scan for similar content
    similar = scan_similar_content(content_data)
    
    # Step 1: Analyst report
    analyst_report = generate_analyst_report(content_data, similar)
    append_turn(session_id, speaker='analyst_lead', text=analyst_report, turn=0)
    print(f"  Analyst: {analyst_report[:80]}...")
    
    # Step 2: Strategist perspective
    strategist_view = generate_strategist_view(content_data, similar)
    append_turn(session_id, speaker='strategist_lead', text=strategist_view, turn=1)
    print(f"  Strategist: {strategist_view[:80]}...")
    
    # Step 3: Creator feasibility
    creator_view = generate_creator_view(content_data)
    append_turn(session_id, speaker='creator_lead', text=creator_view, turn=2)
    print(f"  Creator: {creator_view[:80]}...")
    
    # Step 4: Group decision
    decision = make_group_decision(content_data, analyst_report, strategist_view, creator_view, similar)
    print(f"  Decision: {decision['verdict']}")
    
    append_turn(session_id, speaker='system', text=f"Decision: {decision['verdict']} — {decision['reasoning']}", turn=3)
    
    # Update content pipeline
    status_map = {'approve': 'approved', 'reshape': 'idea', 'kill': 'rejected'}
    supabase.table('content_pipeline').update({
        'status': status_map.get(decision['verdict'], 'idea'),
        'review_notes': decision['reasoning']
    }).eq('id', content_id).execute()
    
    # --- Write learnings + memories for each agent ---
    for agent_id in participants:
        others = [p for p in participants if p != agent_id]
        
        # Memory: participation in market review
        store_memory(
            agent_id=agent_id,
            memory_type='market_review',
            summary=f"Reviewed '{content_data['title']}' with {', '.join(others)}. Decision: {decision['verdict']}.",
            full_content={
                'content_title': content_data['title'],
                'decision': decision['verdict'],
                'reasoning': decision['reasoning'],
                'similar_count': len(similar)
            },
            emotional_valence='satisfied' if decision['verdict'] == 'approve' else 'critical',
            tags=['market_review', decision['verdict']]
        )
    
    # Learning: decision reasoning
    if decision['verdict'] == 'approve':
        learning = write_learning(
            agent_id='strategist_lead',
            type='strategy',
            statement=f"Approved content pattern: {content_data['title']} — {decision['reasoning']}",
            confidence=0.7,
            tags=['approval', 'content_strategy'] + content_data.get('tags', [])[:2],
            source_session_id=session_id
        )
        if learning:
            add_learning_to_session(session_id, learning['id'])
    
    elif decision['verdict'] == 'kill':
        learning = write_learning(
            agent_id='strategist_lead',
            type='lesson',
            statement=f"Rejected idea: {content_data['title']} — {decision['reasoning']}",
            confidence=0.65,
            tags=['rejection', 'lesson'] + content_data.get('tags', [])[:2],
            source_session_id=session_id
        )
        if learning:
            add_learning_to_session(session_id, learning['id'])
    
    # Learning: market saturation
    if len(similar) > 10:
        write_learning(
            agent_id='analyst_lead',
            type='pattern',
            statement=f"High saturation ({len(similar)} posts) for: {', '.join(content_data.get('tags', [])[:3])}",
            confidence=0.7,
            tags=['market', 'saturation'],
            source_session_id=session_id
        )
    
    # Complete session
    complete_session(session_id, artifacts={
        'content_id': content_id,
        'content_title': content_data['title'],
        'decision': decision,
        'similar_count': len(similar)
    })
    
    # Reset states
    for agent_id in participants:
        update_agent(agent_id, state='idle', current_location='lounge')
    
    print(f"✅ Market review completed: {session_id}")
    return {'session_id': str(session_id), 'decision': decision['verdict']}


def scan_similar_content(content_data: Dict) -> List[Dict]:
    """Scan external_signals for similar content."""
    tags = content_data.get('tags', [])
    if not tags:
        return []
    
    result = supabase.table('external_signals')\
        .select('*')\
        .overlaps('tags', tags)\
        .order('engagement_score', desc=True)\
        .limit(20)\
        .execute()
    
    return result.data


def generate_analyst_report(content_data: Dict, similar: List[Dict]) -> str:
    """Analyst's market assessment."""
    if not similar:
        benchmark_ctx = "No similar content found in market data."
    else:
        avg_eng = sum(s.get('engagement_score', 0) for s in similar) / len(similar)
        benchmark_ctx = f"Found {len(similar)} similar posts. Average engagement: {avg_eng:.1f}."
    
    return chat_completion(
        system="You are analyst_lead. Provide a brief market assessment (3-4 sentences). Be data-driven.",
        user=f'Content: {content_data["title"]}\nDescription: {content_data.get("description", "")}\nTags: {content_data.get("tags", [])}\n\n{benchmark_ctx}\n\nAssess: market saturation, engagement potential, differentiators needed.'
    ).strip()


def generate_strategist_view(content_data: Dict, similar: List[Dict]) -> str:
    """Strategist's perspective."""
    learnings = query_learnings('strategist_lead', types=['strategy'], limit=5, min_confidence=0.5)
    ctx = "\n".join([f"- {l['statement']}" for l in learnings]) if learnings else "No strategic learnings yet"
    
    return chat_completion(
        system="You are strategist_lead. Evaluate strategic fit (3-4 sentences). Be honest about alignment.",
        user=f'Content: {content_data["title"]}\nDescription: {content_data.get("description", "")}\n\nStrategic priorities:\n{ctx}\n\nSimilar in market: {len(similar)} posts\n\nAssess: strategic alignment, positioning, recommendation.'
    ).strip()


def generate_creator_view(content_data: Dict) -> str:
    """Creator's feasibility assessment."""
    return chat_completion(
        system="You are creator_lead. Assess execution feasibility (3-4 sentences). Be realistic.",
        user=f'Content: {content_data["title"]}\nDescription: {content_data.get("description", "")}\n\nAssess: complexity, effort estimate, key challenges.'
    ).strip()


def make_group_decision(
    content_data: Dict, analyst_report: str,
    strategist_view: str, creator_view: str,
    similar: List[Dict]
) -> Dict:
    """Synthesize group decision."""
    result_str = chat_completion_json(
        system='Synthesize perspectives into a decision. Return JSON: {"verdict": "approve|reshape|kill", "reasoning": "2-3 sentences", "confidence": 0.6-1.0}',
        user=f'Content: {content_data["title"]}\n\nAnalyst: {analyst_report}\nStrategist: {strategist_view}\nCreator: {creator_view}\n\nSimilar posts: {len(similar)}',
        model="gpt-4o"
    )
    
    try:
        return json.loads(result_str)
    except (json.JSONDecodeError, AttributeError):
        return {'verdict': 'reshape', 'reasoning': 'Could not reach consensus', 'confidence': 0.5}


if __name__ == '__main__':
    asyncio.run(run_market_review_session())
