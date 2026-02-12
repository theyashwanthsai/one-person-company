"""
Test the tool system — discovery, schemas, and execution.
Run: python3 tests/test_tools.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Add repo root so shared modules can be imported even when the script lives in tests/
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from utils import print_header, setup_test_environment
from lib.tool_registry import (
    discover_shared_tools,
    get_tools_for_agent,
    get_tool_schemas,
    list_tools,
    execute_tool
)
from lib.tool_runner import run_agent_step

setup_test_environment()


def test_discovery():
    """Test tool discovery."""
    print_header("TEST 1: Shared tool discovery")
    
    tools = discover_shared_tools()
    print(f"Found {len(tools)} shared tools:")
    for name, t in tools.items():
        desc = t['schema']['function'].get('description', '')[:60]
        print(f"  ✅ {name} — {desc}")
    
    assert len(tools) > 0, "No shared tools found!"
    print()


def test_agent_tools():
    """Test per-agent tool resolution."""
    print_header("TEST 2: Agent tool resolution")
    
    for agent_id in ['strategist_lead', 'creator_lead', 'analyst_lead']:
        tools = get_tools_for_agent(agent_id)
        schemas = get_tool_schemas(agent_id)
        print(f"  {agent_id}: {len(tools)} tools, {len(schemas)} schemas")
    
    print()


def test_schemas():
    """Test that schemas are valid OpenAI format."""
    print_header("TEST 3: Schema validation")
    
    schemas = get_tool_schemas('strategist_lead')
    
    for schema in schemas:
        assert 'type' in schema, f"Missing 'type' in schema"
        assert schema['type'] == 'function', f"Schema type must be 'function'"
        assert 'function' in schema, f"Missing 'function' in schema"
        
        func = schema['function']
        assert 'name' in func, f"Missing 'name' in function"
        assert 'description' in func, f"Missing 'description' in function"
        assert 'parameters' in func, f"Missing 'parameters' in function"
        
        print(f"  ✅ {func['name']} — valid schema")
    
    print()


async def test_execution():
    """Test tool execution."""
    print_header("TEST 4: Tool execution")
    
    # Test query_learnings (should work even with no data)
    result = await execute_tool('strategist_lead', 'query_learnings', {
        'tags': ['test'],
        'min_confidence': 0.5
    })
    print(f"  query_learnings: {result[:80]}...")
    
    # Test scan_external_source
    result = await execute_tool('strategist_lead', 'scan_external_source', {
        'source': 'all',
        'limit': 3
    })
    print(f"  scan_external_source: {result[:80]}...")
    
    # Test check_content_pipeline
    result = await execute_tool('creator_lead', 'check_content_pipeline', {
        'status': 'all',
        'limit': 3
    })
    print(f"  check_content_pipeline: {result[:80]}...")
    
    # Test nonexistent tool
    result = await execute_tool('strategist_lead', 'nonexistent_tool', {})
    print(f"  nonexistent_tool: {result[:80]}...")
    
    print()


async def test_agent_step():
    """Test running an agent with tools (makes LLM call)."""
    print_header("TEST 5: Agent step with tools (LLM call)")
    
    response, tool_calls = await run_agent_step(
        agent_id='strategist_lead',
        task='Check if there are any recent learnings about content strategy. If not, note that we need to build more knowledge.',
    )
    
    print(f"  Response: {response[:150]}...")
    print(f"  Tool calls made: {len(tool_calls)}")
    for tc in tool_calls:
        print(f"    🔧 {tc['tool']}({tc['arguments']})")
    
    print()


def main():
    print_header("🔧 Tool System Tests")
    
    test_discovery()
    test_agent_tools()
    test_schemas()
    
    asyncio.run(test_execution())
    
    # Only run LLM test if API key is set
    if os.getenv('OPENAI_API_KEY'):
        asyncio.run(test_agent_step())
    else:
        print("⚠️ Skipping LLM test (OPENAI_API_KEY not set)")
    
    print("=" * 60)
    print("✅ All tool system tests passed!")
    print("=" * 60)


if __name__ == '__main__':
    main()
