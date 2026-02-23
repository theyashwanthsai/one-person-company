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
RECENT_LEARNINGS_LIMIT = 5
RECENT_MEMORIES_LIMIT = 5


async def run_agent_with_tools(
    agent_id: str,
    system_prompt: str,
    user_prompt: str,
    model: str = "gpt-4o",
    temperature: float = 0.7,
    max_tokens: int = 500,
    tools: Optional[List[dict]] = None,
    messages: Optional[List[dict]] = None,
    prepend_recent_context: bool = False,
    auto_log_insights: bool = False,
    source_session_id: Optional[str] = None,
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
        prepend_recent_context: If true, prepend recent learnings/memories
        auto_log_insights: If true, auto-store memory/learning after run
        source_session_id: Optional session id for learning linkage
    
    Returns:
        Tuple of (final_response_text, list_of_tool_calls_made)
    """
    # Get available tools
    if tools is None:
        tools = get_tool_schemas(agent_id)
    
    # Build messages
    if messages is None:
        final_user_prompt = user_prompt
        if prepend_recent_context:
            final_user_prompt = _compose_prompt_with_recent_context(agent_id, user_prompt)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": final_user_prompt}
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
            if auto_log_insights:
                _auto_log_run(
                    agent_id=agent_id,
                    input_prompt=_get_latest_user_message(messages, fallback=user_prompt),
                    response=final_text,
                    tool_calls=tool_calls_made,
                    source_session_id=source_session_id,
                )
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
    fallback_text = messages[-1].get("content", "")
    if auto_log_insights:
        _auto_log_run(
            agent_id=agent_id,
            input_prompt=_get_latest_user_message(messages, fallback=user_prompt),
            response=fallback_text,
            tool_calls=tool_calls_made,
            source_session_id=source_session_id,
        )
    return fallback_text, tool_calls_made


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
    model: str = "gpt-4o",
    source_session_id: Optional[str] = None,
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
        model=model,
        prepend_recent_context=True,
        auto_log_insights=True,
        source_session_id=source_session_id,
    )


def _compose_prompt_with_recent_context(agent_id: str, user_prompt: str) -> str:
    context = _build_recent_context(agent_id)
    if not context:
        return user_prompt
    return f"{user_prompt}\n\n--- Recent Learnings & Memories ---\n{context}"


def _build_recent_context(agent_id: str) -> str:
    try:
        from lib.learnings import query_learnings
        from lib.memories import query_memories
    except Exception as e:
        print(f"  ⚠️ Failed to import learnings/memories for {agent_id}: {e}")
        return ""

    sections = []
    try:
        learnings = query_learnings(
            agent_id=agent_id,
            min_confidence=0.0,
            limit=RECENT_LEARNINGS_LIMIT,
        )
    except Exception as e:
        print(f"  ⚠️ Failed to load recent learnings for {agent_id}: {e}")
        learnings = []

    if learnings:
        lines = []
        for item in learnings:
            statement = (item.get("statement") or "").strip()
            if not statement:
                continue
            l_type = item.get("type", "learning")
            confidence = item.get("confidence", 0)
            lines.append(f"- [{l_type} | conf={confidence}] {statement}")
        if lines:
            sections.append("Recent learnings:\n" + "\n".join(lines))

    try:
        memories = query_memories(agent_id=agent_id, limit=RECENT_MEMORIES_LIMIT)
    except Exception as e:
        print(f"  ⚠️ Failed to load recent memories for {agent_id}: {e}")
        memories = []

    if memories:
        lines = []
        for item in memories:
            summary = (item.get("summary") or "").strip()
            if not summary:
                continue
            m_type = item.get("memory_type", "memory")
            valence = item.get("emotional_valence")
            label = f"{m_type}" if not valence else f"{m_type} | {valence}"
            lines.append(f"- [{label}] {summary}")
        if lines:
            sections.append("Recent memories:\n" + "\n".join(lines))

    return "\n\n".join(sections)


def _get_latest_user_message(messages: List[dict], fallback: str = "") -> str:
    for msg in reversed(messages):
        role = msg.get("role") if isinstance(msg, dict) else getattr(msg, "role", None)
        if role != "user":
            continue

        content = msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", None)
        if isinstance(content, str):
            return content or fallback
        if isinstance(content, list):
            # SDK can return structured content blocks; extract text parts if present.
            text_parts = []
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    text_parts.append(part.get("text", ""))
                else:
                    part_text = getattr(part, "text", None)
                    if isinstance(part_text, str):
                        text_parts.append(part_text)
            joined = "\n".join([p for p in text_parts if p]).strip()
            if joined:
                return joined
        if content is not None:
            return str(content)
    return fallback


def _auto_log_run(
    agent_id: str,
    input_prompt: str,
    response: str,
    tool_calls: List[dict],
    source_session_id: Optional[str] = None,
):
    called_tools = {item.get("tool") for item in (tool_calls or [])}
    summary = _safe_trim(_first_non_empty_line(response) or _first_non_empty_line(input_prompt), 240)
    if not summary:
        summary = "Agent completed a run."

    try:
        from lib.memories import store_memory
        if "store_memory" not in called_tools:
            store_memory(
                agent_id=agent_id,
                memory_type="execution",
                summary=summary,
                full_content={
                    "prompt": _safe_trim(input_prompt, 5000),
                    "response": _safe_trim(response, 5000),
                    "tool_calls": tool_calls,
                    "auto_logged": True,
                },
                emotional_valence="neutral",
                tags=["auto_log", "agent_run"],
            )
    except Exception as e:
        print(f"  ⚠️ Failed auto memory log for {agent_id}: {e}")

    try:
        from lib.learnings import write_learning
        if "write_learning" not in called_tools:
            write_learning(
                agent_id=agent_id,
                type="pattern",
                statement=_extract_learning_statement(input_prompt, response),
                confidence=0.55,
                tags=["auto_log", "agent_run"],
                evidence_refs=[
                    {"kind": "response_summary", "value": _safe_trim(response, 500)},
                    {"kind": "tool_calls", "value": [c.get("tool") for c in tool_calls]},
                ],
                source_session_id=source_session_id,
            )
    except Exception as e:
        print(f"  ⚠️ Failed auto learning log for {agent_id}: {e}")


def _extract_learning_statement(input_prompt: str, response: str) -> str:
    candidate = _first_non_empty_line(response)
    if not candidate:
        candidate = _first_non_empty_line(input_prompt)
    candidate = (candidate or "").replace("[DONE]", "").replace("[done]", "").strip()
    if not candidate:
        return "Execution produced a useful outcome worth revisiting."
    if len(candidate) < 25:
        return f"Execution takeaway: {_safe_trim(candidate, 180)}"
    return _safe_trim(candidate, 220)


def _first_non_empty_line(text: str) -> str:
    for line in (text or "").splitlines():
        line = line.strip()
        if line:
            return line
    return ""


def _safe_trim(text: str, max_len: int) -> str:
    text = (text or "").strip()
    if len(text) <= max_len:
        return text
    return text[:max_len - 3].rstrip() + "..."
