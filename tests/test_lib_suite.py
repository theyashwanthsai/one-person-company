import importlib
import json
import os
import sys
import tempfile
import types
import unittest
from email.mime.text import MIMEText
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def fresh_import(module_name: str):
    """Import module with external client constructors patched."""
    sys.modules.pop(module_name, None)
    with patch("supabase.create_client", return_value=MagicMock(name="supabase_client")), patch(
        "openai.OpenAI", return_value=MagicMock(name="openai_client")
    ):
        return importlib.import_module(module_name)


def build_chain_mock(result_data):
    q = MagicMock()
    for name in ("select", "eq", "in_", "contains", "gte", "order", "limit", "insert", "update"):
        getattr(q, name).return_value = q
    q.execute.return_value = types.SimpleNamespace(data=result_data)
    return q


class TestSupabaseClient(unittest.TestCase):
    def test_get_supabase_requires_env(self):
        module = fresh_import("lib.supabase_client")
        module.get_supabase.cache_clear()
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError):
                module.get_supabase()

    def test_get_supabase_caches_client(self):
        module = fresh_import("lib.supabase_client")
        module.get_supabase.cache_clear()
        fake_client = MagicMock()
        with patch.dict(
            os.environ,
            {"SUPABASE_URL": "https://x.supabase.co", "SUPABASE_SERVICE_ROLE_KEY": "key"},
            clear=False,
        ), patch("lib.supabase_client.create_client", return_value=fake_client) as create_client:
            c1 = module.get_supabase()
            c2 = module.get_supabase()
            self.assertIs(c1, fake_client)
            self.assertIs(c2, fake_client)
            create_client.assert_called_once()


class TestLLM(unittest.TestCase):
    def test_chat_completion_retries_then_succeeds(self):
        module = fresh_import("lib.llm")
        resp = types.SimpleNamespace(
            choices=[types.SimpleNamespace(message=types.SimpleNamespace(content="ok"))]
        )
        module.client.chat.completions.create.side_effect = [Exception("temp"), resp]
        with patch("lib.llm.time.sleep", return_value=None):
            out = module.chat_completion("sys", "user")
        self.assertEqual(out, "ok")
        self.assertEqual(module.client.chat.completions.create.call_count, 2)

    def test_chat_completion_json_raises_after_retries(self):
        module = fresh_import("lib.llm")
        module.client.chat.completions.create.side_effect = Exception("fail")
        with patch("lib.llm.time.sleep", return_value=None):
            with self.assertRaises(Exception):
                module.chat_completion_json("sys", "user")

    def test_chat_with_history_calls_openai(self):
        module = fresh_import("lib.llm")
        resp = types.SimpleNamespace(
            choices=[types.SimpleNamespace(message=types.SimpleNamespace(content="history-ok"))]
        )
        module.client.chat.completions.create.return_value = resp
        out = module.chat_with_history([{"role": "user", "content": "hey"}])
        self.assertEqual(out, "history-ok")


class TestLearnings(unittest.TestCase):
    def setUp(self):
        self.module = fresh_import("lib.learnings")
        self.fake_supabase = MagicMock()
        self.module.supabase = self.fake_supabase

    def test_query_learnings_applies_filters(self):
        q = build_chain_mock([{"statement": "a"}])
        self.fake_supabase.table.return_value = q
        data = self.module.query_learnings(
            "strategist_lead", types=["pattern"], tags=["ai"], min_confidence=0.7, limit=3
        )
        self.assertEqual(data, [{"statement": "a"}])
        q.in_.assert_called_once_with("type", ["pattern"])
        q.contains.assert_called_once_with("tags", ["ai"])
        q.gte.assert_called_once_with("confidence", 0.7)
        q.limit.assert_called_once_with(3)

    def test_write_learning_serializes_source_session(self):
        q = build_chain_mock([{"id": "1"}])
        self.fake_supabase.table.return_value = q
        out = self.module.write_learning("a", "pattern", "stmt", source_session_id="abc")
        self.assertEqual(out["id"], "1")
        payload = q.insert.call_args[0][0]
        self.assertEqual(payload["source_session_id"], "abc")

    def test_get_agent_learnings_summary_empty(self):
        q = build_chain_mock([])
        self.fake_supabase.table.return_value = q
        summary = self.module.get_agent_learnings_summary("x")
        self.assertEqual(summary, {"total": 0, "by_type": {}, "avg_confidence": 0})


class TestMemories(unittest.TestCase):
    def setUp(self):
        self.module = fresh_import("lib.memories")
        self.fake_supabase = MagicMock()
        self.module.supabase = self.fake_supabase

    def test_store_memory_serializes_learning_ids(self):
        q = build_chain_mock([{"id": "m1"}])
        self.fake_supabase.table.return_value = q
        out = self.module.store_memory("agent", "conversation", "sum", related_learning_ids=["l1", "l2"])
        self.assertEqual(out["id"], "m1")
        payload = q.insert.call_args[0][0]
        self.assertEqual(payload["related_learning_ids"], ["l1", "l2"])

    def test_link_memory_to_learning_adds_once(self):
        q = build_chain_mock([])
        self.fake_supabase.table.return_value = q
        with patch("lib.memories.get_memory", return_value={"related_learning_ids": ["a"]}):
            self.module.link_memory_to_learning("m1", "b")
        q.update.assert_called_once_with({"related_learning_ids": ["a", "b"]})


class TestSessions(unittest.TestCase):
    def setUp(self):
        self.module = fresh_import("lib.sessions")
        self.fake_supabase = MagicMock()
        self.module.supabase = self.fake_supabase

    def test_create_session_returns_id(self):
        q = build_chain_mock([{"id": "s1"}])
        self.fake_supabase.table.return_value = q
        sid = self.module.create_session("meeting", ["a", "b"])
        self.assertEqual(sid, "s1")

    def test_append_turn_updates_conversation(self):
        q = build_chain_mock([])
        self.fake_supabase.table.return_value = q
        with patch("lib.sessions.get_session", return_value={"conversation": []}):
            self.module.append_turn("s1", "a", "hello")
        args = q.update.call_args[0][0]
        self.assertEqual(args["conversation"][0]["speaker"], "a")
        self.assertEqual(args["conversation"][0]["text"], "hello")

    def test_add_learning_to_session_skips_solo(self):
        q = build_chain_mock([])
        self.fake_supabase.table.return_value = q
        with patch("lib.sessions.get_session", return_value={"type": "solo", "learnings_created": []}):
            self.module.add_learning_to_session("s1", "l1")
        q.update.assert_not_called()


class TestAgents(unittest.TestCase):
    def setUp(self):
        self.module = fresh_import("lib.agents")
        self.fake_supabase = MagicMock()
        self.module.supabase = self.fake_supabase
        self.module._agent_cache.clear()

    def test_load_all_agents_metadata_reads_frontmatter(self):
        with tempfile.TemporaryDirectory() as td:
            agents_dir = Path(td) / "agents"
            a_dir = agents_dir / "agent_a"
            a_dir.mkdir(parents=True)
            (a_dir / "soul.md").write_text(
                "---\n"
                "id: agent_a\n"
                "name: Agent A\n"
                "role: Strategy\n"
                "description: Desc\n"
                "capabilities:\n"
                "  - analysis\n"
                "---\n"
                "Instructions."
            )
            self.module.AGENTS_DIR = agents_dir
            data = self.module.load_all_agents_metadata()
            self.assertIn("agent_a", data)
            self.assertEqual(data["agent_a"]["name"], "Agent A")

    def test_load_agent_prompt_missing_returns_none(self):
        with tempfile.TemporaryDirectory() as td:
            self.module.AGENTS_DIR = Path(td)
            out = self.module.load_agent_prompt("x", "standup")
            self.assertIsNone(out)

    def test_get_all_agents_merges_db_and_metadata(self):
        q = build_chain_mock([{"id": "agent_a", "state": "idle"}])
        self.fake_supabase.table.return_value = q
        with patch("lib.agents.load_all_agents_metadata", return_value={"agent_a": {"name": "A", "role": "R", "capabilities": []}}):
            data = self.module.get_all_agents()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "A")


class TestToolRegistry(unittest.TestCase):
    def setUp(self):
        self.module = fresh_import("lib.tool_registry")

    def test_discover_shared_tools_and_override(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            shared = root / "tools"
            agent_tools = root / "agents" / "agent_x" / "tools"
            shared.mkdir(parents=True)
            agent_tools.mkdir(parents=True)

            (shared / "sample.py").write_text(
                "SCHEMA={'type':'function','function':{'name':'ping','description':'d','parameters':{'type':'object','properties':{}}}}\n"
                "def execute(agent_id, **kwargs):\n"
                "    return 'shared'\n"
            )
            (agent_tools / "sample.py").write_text(
                "SCHEMA={'type':'function','function':{'name':'ping','description':'d','parameters':{'type':'object','properties':{}}}}\n"
                "def execute(agent_id, **kwargs):\n"
                "    return 'agent'\n"
            )

            self.module.SHARED_TOOLS_DIR = shared
            self.module.AGENTS_DIR = root / "agents"
            tools = self.module.get_tools_for_agent("agent_x")
            self.assertIn("ping", tools)
            self.assertEqual(tools["ping"]["source"], "agent_x")

    def test_execute_tool_returns_json_for_dict(self):
        async def execute(agent_id, **kwargs):
            return {"ok": True, "agent_id": agent_id, "kwargs": kwargs}

        with patch(
            "lib.tool_registry.get_tools_for_agent",
            return_value={"t": {"module": types.SimpleNamespace(execute=execute)}},
        ):
            # run async without extra helper class
            async def _runner():
                result = await self.module.execute_tool("a", "t", {"x": 1})
                self.assertEqual(json.loads(result)["ok"], True)

            import asyncio

            asyncio.run(_runner())


class TestToolRunner(unittest.TestCase):
    def setUp(self):
        self.module = fresh_import("lib.tool_runner")

    def test_summarize_args_truncates(self):
        s = self.module._summarize_args({"a": "x" * 40, "b": 1})
        self.assertIn("...", s)

    def test_run_agent_with_tools_stop_path(self):
        response = types.SimpleNamespace(
            choices=[
                types.SimpleNamespace(
                    finish_reason="stop", message=types.SimpleNamespace(content="done", tool_calls=None)
                )
            ]
        )
        self.module.client.chat.completions.create.return_value = response
        import asyncio
        out, calls = asyncio.run(
            self.module.run_agent_with_tools("agent", "sys", "user", tools=[])
        )
        self.assertEqual(out, "done")
        self.assertEqual(calls, [])

    def test_run_agent_with_tools_tool_call_path(self):
        tool_call = types.SimpleNamespace(
            id="tc1",
            function=types.SimpleNamespace(name="ping", arguments='{"x": 1}')
        )
        first = types.SimpleNamespace(
            choices=[
                types.SimpleNamespace(
                    finish_reason="tool_calls",
                    message=types.SimpleNamespace(content=None, tool_calls=[tool_call]),
                )
            ]
        )
        second = types.SimpleNamespace(
            choices=[
                types.SimpleNamespace(
                    finish_reason="stop",
                    message=types.SimpleNamespace(content="final", tool_calls=None),
                )
            ]
        )
        self.module.client.chat.completions.create.side_effect = [first, second]
        with patch("lib.tool_runner.execute_tool", new=AsyncMock(return_value="tool-ok")):
            import asyncio
            out, calls = asyncio.run(
                self.module.run_agent_with_tools("agent", "sys", "user", tools=[{"type": "function"}])
            )
        self.assertEqual(out, "final")
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["tool"], "ping")

    def test_run_agent_step_builds_context(self):
        with patch("lib.agents.load_agent_full", return_value={"soul_instructions": "sys"}), patch(
            "lib.tool_runner.run_agent_with_tools",
            new=AsyncMock(return_value=("ok", [])),
        ) as run_agent:
            import asyncio
            asyncio.run(self.module.run_agent_step("a", "task", context="ctx"))
        kwargs = run_agent.call_args.kwargs
        self.assertIn("--- Context ---", kwargs["user_prompt"])


class TestEmailClient(unittest.TestCase):
    def setUp(self):
        self.env = {
            "EMAIL_ADDRESS": "bot@example.com",
            "EMAIL_PASSWORD": "secret",
            "CEO_EMAIL": "ceo@example.com",
            "SMTP_HOST": "smtp.example.com",
            "SMTP_PORT": "587",
            "IMAP_HOST": "imap.example.com",
        }

    def test_init_requires_credentials(self):
        module = fresh_import("lib.email_client")
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError):
                module.EmailClient()

    def test_send_email_success(self):
        module = fresh_import("lib.email_client")
        with patch.dict(os.environ, self.env, clear=False), patch("lib.email_client.smtplib.SMTP") as smtp:
            smtp.return_value.__enter__.return_value = MagicMock()
            client = module.EmailClient()
            ok = client._send_email("x@example.com", "subj", "body")
            self.assertTrue(ok)

    def test_get_email_body_plain(self):
        module = fresh_import("lib.email_client")
        with patch.dict(os.environ, self.env, clear=False):
            client = module.EmailClient()
        msg = MIMEText("hello", "plain")
        self.assertEqual(client._get_email_body(msg), "hello")

    def test_is_message_for_agent(self):
        module = fresh_import("lib.email_client")
        with patch.dict(os.environ, self.env, clear=False):
            client = module.EmailClient()
        self.assertTrue(client._is_message_for_agent("strategist", "hello strategist_lead"))
        self.assertTrue(client._is_message_for_agent("strategist", "team update"))
        self.assertFalse(client._is_message_for_agent("strategist", "unrelated note"))


class TestLibInit(unittest.TestCase):
    def test_lazy_exports(self):
        module = fresh_import("lib")
        self.assertIn("chat_completion", module.__all__)
        with patch("lib.llm.chat_completion", return_value="ok"):
            fn = module.chat_completion
            self.assertTrue(callable(fn))


if __name__ == "__main__":
    unittest.main(verbosity=2)
