"""
Tool Registry
Discovers, validates, and manages tools for agents.

Convention: Each tool is a Python file with:
    SCHEMA  — OpenAI function calling schema (dict)
    execute — async function(agent_id, **kwargs) → result

Tools live in two places:
    tools/                        — shared tools (all agents)
    agents/<agent_id>/tools/      — optional legacy agent-specific tools
"""

import os
import importlib
import importlib.util
from pathlib import Path
from typing import Dict, List, Optional

PROJECT_ROOT = Path(__file__).parent.parent
SHARED_TOOLS_DIR = PROJECT_ROOT / "tools"
AGENTS_DIR = PROJECT_ROOT / "agents"


def _load_module_from_file(filepath: Path, module_name: str):
    """Load a Python module from a file path."""
    spec = importlib.util.spec_from_file_location(module_name, filepath)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
        return module
    except Exception as e:
        print(f"  ⚠️ Failed to load tool {filepath}: {e}")
        return None


def _validate_tool(module, filepath: Path) -> bool:
    """Check that a tool module has SCHEMA and execute."""
    if not hasattr(module, 'SCHEMA'):
        print(f"  ⚠️ Tool {filepath.name} missing SCHEMA")
        return False
    if not hasattr(module, 'execute'):
        print(f"  ⚠️ Tool {filepath.name} missing execute()")
        return False
    
    schema = module.SCHEMA
    if not isinstance(schema, dict):
        print(f"  ⚠️ Tool {filepath.name} SCHEMA must be a dict")
        return False
    
    # Validate schema structure
    func = schema.get('function', {})
    if not func.get('name'):
        print(f"  ⚠️ Tool {filepath.name} SCHEMA missing function.name")
        return False
    
    return True


def discover_shared_tools() -> Dict[str, dict]:
    """
    Discover all shared tools from tools/ directory.
    
    Returns:
        Dict of {tool_name: {"schema": ..., "module": ..., "source": "shared"}}
    """
    tools = {}
    
    if not SHARED_TOOLS_DIR.exists():
        return tools
    
    for filepath in sorted(SHARED_TOOLS_DIR.glob("*.py")):
        if filepath.name.startswith("_"):
            continue
        
        module_name = f"tools.{filepath.stem}"
        module = _load_module_from_file(filepath, module_name)
        
        if module and _validate_tool(module, filepath):
            tool_name = module.SCHEMA['function']['name']
            tools[tool_name] = {
                "schema": module.SCHEMA,
                "module": module,
                "source": "shared",
                "file": str(filepath)
            }
    
    return tools


def discover_agent_tools(agent_id: str) -> Dict[str, dict]:
    """
    Discover optional legacy agent-specific tools from agents/<agent_id>/tools/.
    
    Returns:
        Dict of {tool_name: {"schema": ..., "module": ..., "source": agent_id}}
    """
    tools = {}
    agent_tools_dir = AGENTS_DIR / agent_id / "tools"
    
    if not agent_tools_dir.exists():
        return tools
    
    for filepath in sorted(agent_tools_dir.glob("*.py")):
        if filepath.name.startswith("_"):
            continue
        
        module_name = f"agents.{agent_id}.tools.{filepath.stem}"
        module = _load_module_from_file(filepath, module_name)
        
        if module and _validate_tool(module, filepath):
            tool_name = module.SCHEMA['function']['name']
            tools[tool_name] = {
                "schema": module.SCHEMA,
                "module": module,
                "source": agent_id,
                "file": str(filepath)
            }
    
    return tools


def get_tools_for_agent(agent_id: str) -> Dict[str, dict]:
    """
    Get all tools available to a specific agent.
    Agent-specific tools override shared tools with the same name.
    
    Returns:
        Dict of {tool_name: {"schema": ..., "module": ..., "source": ...}}
    """
    # Start with shared tools
    tools = discover_shared_tools()
    
    # Agent tools override shared ones
    agent_tools = discover_agent_tools(agent_id)
    tools.update(agent_tools)
    
    return tools


def get_tool_schemas(agent_id: str) -> List[dict]:
    """
    Get OpenAI-format tool schemas for an agent.
    Ready to pass directly to chat.completions.create(tools=...).
    """
    tools = get_tools_for_agent(agent_id)
    return [t["schema"] for t in tools.values()]


async def execute_tool(agent_id: str, tool_name: str, arguments: dict) -> str:
    """
    Execute a tool by name with given arguments.
    
    Args:
        agent_id: The agent calling the tool (always passed to execute())
        tool_name: Name of the tool to execute
        arguments: Arguments from the LLM's tool call
    
    Returns:
        String result to feed back to the LLM
    """
    tools = get_tools_for_agent(agent_id)
    
    if tool_name not in tools:
        return f"Error: Tool '{tool_name}' not found. Available: {list(tools.keys())}"
    
    tool = tools[tool_name]
    execute_fn = tool["module"].execute
    
    try:
        import asyncio
        import inspect
        
        # Support both sync and async execute functions
        if inspect.iscoroutinefunction(execute_fn):
            result = await execute_fn(agent_id=agent_id, **arguments)
        else:
            result = execute_fn(agent_id=agent_id, **arguments)
        
        # Convert result to string for LLM
        if isinstance(result, str):
            return result
        elif isinstance(result, (dict, list)):
            import json
            return json.dumps(result, indent=2, default=str)
        else:
            return str(result)
    
    except Exception as e:
        return f"Error executing {tool_name}: {str(e)}"


def list_tools(agent_id: Optional[str] = None):
    """Print available tools for debugging."""
    if agent_id:
        tools = get_tools_for_agent(agent_id)
        print(f"\nTools for {agent_id}:")
    else:
        tools = discover_shared_tools()
        print("\nShared tools:")
    
    for name, tool in tools.items():
        desc = tool['schema']['function'].get('description', 'No description')
        print(f"  • {name} [{tool['source']}] — {desc[:60]}")
    
    print(f"\n  Total: {len(tools)} tools\n")
