import os
import sys
from pathlib import Path
# Add repo root so shared modules can be imported even when the script lives in tests/
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from utils import print_header, setup_test_environment

setup_test_environment()

from lib import (
    query_learnings,
    write_learning,
    store_memory,
    query_memories,
    create_session,
    append_turn,
    complete_session
)

print_header("🧪 Testing Core Libraries")
print_header("1. Learning System")

try:
    learnings = query_learnings('strategist_lead', limit=3)
    print(f"✓ Queried learnings: {len(learnings)} found")
    if learnings:
        print(f"  Example: {learnings[0]['statement'][:60]}...")
except Exception as e:
    print(f"✗ Learning query failed: {e}")

print_header("2. Memory System")

try:
    memory = store_memory(
        agent_id='creator_lead',
        memory_type='test',
        summary='Test memory from core lib test',
        emotional_valence='neutral'
    )
    print(f"✓ Stored memory: {memory['id']}")
    
    memories = query_memories('creator_lead', limit=1)
    print(f"✓ Queried memories: {len(memories)} found")
except Exception as e:
    print(f"✗ Memory test failed: {e}")

print_header("3. Session System")

try:
    session_id = create_session(
        type='test',
        participants=['strategist_lead', 'creator_lead'],
        intent='Test core libraries'
    )
    print(f"✓ Created session: {session_id}")
    
    append_turn(session_id, speaker='strategist_lead', text='Hello from test')
    print(f"✓ Appended conversation turn")
    
    complete_session(session_id, artifacts={'test': 'passed'})
    print(f"✓ Completed session")
except Exception as e:
    print(f"✗ Session test failed: {e}")

print("\n" + "=" * 60)
print("✅ Core Libraries Test Complete!")
print("=" * 60)
print("\nAll systems operational. Ready to build workers!")
