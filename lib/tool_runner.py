"""
Tool Runner
Handles the LLM ↔ tool execution loop.

This is the core agent execution engine:
    1. Send prompt + tools to LLM
    2. If LLM calls a tool → execute it → feed result back
    3. Repeat until LLM gives a final text response
    4. Return the final response + list of tool calls made
"""

import os
import json
import time
from typing import List, Dict, Optional, Tuple
from openai import OpenAI
from dotenv import load_dotenv

from lib.tool_registry import get_tool_schemas, execute_tool

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MAX_TOOL_ROUNDS = 10  # Safety limit to prevent infinite loops


async def run_agent_with_tools(
    agent_id: str,
    system_prompt: str,
    user_prompt: str,
    model: str = "gpt-4o",
    temperature: float = 0.7,
    max_tokens: int = 500,
    tools: Optional[List[dict]] = None,
    messages: Optional[List[dict]] = None
) -> Tuple[str, List[dict]]:
    """
    Run an agent with tool calling support.
    
    Args:
        agent_id: The agent running (used for tool context)
        system_prompt: System message (agent's soul/instructions)
        user_prompt: User/task message
        model: OpenAI model to use
        temperature: Creativity level
        max_tokens: Max response length
        tools: Override tool schemas (auto-discovered if None)
        messages: Override full message history (ignores system/user if set)
    
    Returns:
        Tuple of (final_response_text, list_of_tool_calls_made)
    """
    # Get available tools
    if tools is None:
        tools = get_tool_schemas(agent_id)
    
    # Build messages
    if messages is None:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    
    tool_calls_made = []
    
    for round_num in range(MAX_TOOL_ROUNDS):
        # Call LLM
        call_kwargs = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        if tools:
            call_kwargs["tools"] = tools
        
        for attempt in range(3):
            try:
                response = client.chat.completions.create(**call_kwargs)
                break
            except Exception as e:
                if attempt == 2:
                    raise e
                time.sleep(2 ** attempt)
        
        choice = response.choices[0]
        
        # Case 1: LLM gives a final text response (no tool calls)
        if choice.finish_reason == "stop" or not choice.message.tool_calls:
            final_text = choice.message.content or ""
            return final_text, tool_calls_made
        
        # Case 2: LLM wants to call tools
        # Add the assistant message with tool calls to history
        messages.append(choice.message)
        
        # Execute each tool call
        for tool_call in choice.message.tool_calls:
            fn_name = tool_call.function.name
            
            try:
                fn_args = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError:
                fn_args = {}
            
            print(f"    🔧 {agent_id} → {fn_name}({_summarize_args(fn_args)})")
            
            # Execute the tool
            result = await execute_tool(
                agent_id=agent_id,
                tool_name=fn_name,
                arguments=fn_args
            )
            
            # Track what was called
            tool_calls_made.append({
                "tool": fn_name,
                "arguments": fn_args,
                "result_preview": result[:200] if result else ""
            })
            
            # Add tool result to messages
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result
            })
    
    # Safety: if we hit max rounds, return what we have
    print(f"  ⚠️ Hit max tool rounds ({MAX_TOOL_ROUNDS}) for {agent_id}")
    return messages[-1].get("content", ""), tool_calls_made


def _summarize_args(args: dict) -> str:
    """Short summary of tool arguments for logging."""
    parts = []
    for k, v in args.items():
        if isinstance(v, str) and len(v) > 30:
            v = v[:30] + "..."
        parts.append(f"{k}={v}")
    return ", ".join(parts[:3])


async def run_agent_step(
    agent_id: str,
    task: str,
    context: str = "",
    model: str = "gpt-4o"
) -> Tuple[str, List[dict]]:
    """
    High-level: Run one "step" for an agent with their soul and tools.
    
    Loads the agent's soul.md as system prompt, 
    discovers their tools, and runs the tool loop.
    
    Args:
        agent_id: Which agent to run
        task: What to do (becomes user message)
        context: Additional context (learnings, memories, etc.)
        model: OpenAI model
    
    Returns:
        Tuple of (agent_response, tool_calls_made)
    """
    from lib.agents import load_agent_full
    
    agent = load_agent_full(agent_id)
    system_prompt = agent.get("soul_instructions", f"You are {agent_id}.")
    
    user_prompt = task
    if context:
        user_prompt = f"{task}\n\n--- Context ---\n{context}"
    
    return await run_agent_with_tools(
        agent_id=agent_id,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        model=model
    )

