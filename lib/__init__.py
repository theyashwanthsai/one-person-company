"""Lazy package exports for core library helpers.

Avoid importing modules with external client initialization at package import time.
"""

from importlib import import_module

_EXPORT_MAP = {
    "load_all_agents_metadata": "lib.agents",
    "load_agent_full": "lib.agents",
    "get_agent_db": "lib.agents",
    "update_agent_state": "lib.agents",
    "update_agent_location": "lib.agents",
    "load_agent_skill": "lib.agents",
    "load_agent_prompt": "lib.agents",
    "load_agent_reference": "lib.agents",
    "get_all_agents": "lib.agents",
    "chat_completion": "lib.llm",
    "chat_completion_json": "lib.llm",
    "chat_with_history": "lib.llm",
    "query_learnings": "lib.learnings",
    "write_learning": "lib.learnings",
    "boost_learning": "lib.learnings",
    "dismiss_learning": "lib.learnings",
    "get_learning": "lib.learnings",
    "get_agent_learnings_summary": "lib.learnings",
    "store_memory": "lib.memories",
    "query_memories": "lib.memories",
    "get_memory": "lib.memories",
    "link_memory_to_learning": "lib.memories",
    "create_session": "lib.sessions",
    "get_session": "lib.sessions",
    "update_session": "lib.sessions",
    "append_turn": "lib.sessions",
    "complete_session": "lib.sessions",
    "fail_session": "lib.sessions",
    "get_recent_sessions": "lib.sessions",
    "add_learning_to_session": "lib.sessions",
}

__all__ = list(_EXPORT_MAP.keys())


def __getattr__(name):
    module_name = _EXPORT_MAP.get(name)
    if not module_name:
        raise AttributeError(f"module 'lib' has no attribute '{name}'")
    module = import_module(module_name)
    value = getattr(module, name)
    globals()[name] = value
    return value
