import asyncio
import importlib
import os
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def fresh_import(module_name: str):
    """Import module with external client constructors patched."""
    sys.modules.pop(module_name, None)
    fake_schedule = MagicMock(name="schedule_module")
    with patch.dict(sys.modules, {"schedule": fake_schedule}), patch(
        "supabase.create_client", return_value=MagicMock(name="supabase_client")
    ), patch("openai.OpenAI", return_value=MagicMock(name="openai_client")):
        return importlib.import_module(module_name)


class TestSessionInteractions(unittest.TestCase):
    def setUp(self):
        self.engine = fresh_import("workers.engine")

    def test_run_meeting_records_turns_and_completes(self):
        module = self.engine

        responses = [
            ("Strategist update", []),
            ("Creator reply [DONE]", [{"tool": "discord_ceo"}]),
        ]

        with patch.object(module, "create_session", return_value="session-1"), patch.object(
            module, "append_turn"
        ) as append_turn, patch.object(module, "complete_session") as complete_session, patch.object(
            module, "update_agent"
        ), patch.object(
            module, "load_agent_full", return_value={"soul_instructions": "You are an agent."}
        ), patch.object(
            module, "run_agent_with_tools", new=AsyncMock(side_effect=responses)
        ):
            asyncio.run(
                module.run_meeting(
                    agents=["strategist_lead", "creator_lead"],
                    task="Brainstorm and conclude naturally.",
                    session_type="brainstorm",
                    max_turns=6,
                )
            )

        self.assertEqual(append_turn.call_count, 2)
        first_call = append_turn.call_args_list[0].kwargs
        second_call = append_turn.call_args_list[1].kwargs
        self.assertEqual(first_call["speaker"], "strategist_lead")
        self.assertEqual(second_call["speaker"], "creator_lead")

        complete_session.assert_called_once()
        artifacts = complete_session.call_args.kwargs["artifacts"]
        self.assertEqual(artifacts["type"], "brainstorm")
        self.assertEqual(artifacts["turns"], 2)
        self.assertEqual(artifacts["participants"], ["strategist_lead", "creator_lead"])

    def test_resolve_message_targets(self):
        module = self.engine
        agents = [
            {"id": "strategist_lead", "name": "Thea"},
            {"id": "creator_lead", "name": "Kavi"},
            {"id": "analyst_lead", "name": "Dara"},
            {"id": "watari", "name": "Watari"},
        ]

        self.assertEqual(
            module.resolve_message_targets("Thea please check this", agents),
            ["strategist_lead"],
        )
        self.assertEqual(
            module.resolve_message_targets("Team, everyone review this", agents),
            ["strategist_lead", "creator_lead", "analyst_lead"],
        )
        self.assertEqual(
            module.resolve_message_targets("Quick update with no direct mention", agents),
            ["watari"],
        )


class TestDiscordChatting(unittest.TestCase):
    def setUp(self):
        self.engine = fresh_import("workers.engine")
        self.discord_module = fresh_import("lib.discord.client")

    def test_poll_discord_routes_message_to_target_agent(self):
        module = self.engine
        module.LAST_SEEN_DISCORD_MESSAGE_ID.clear()

        agents = [
            {"id": "strategist_lead", "name": "Thea"},
            {"id": "creator_lead", "name": "Kavi"},
            {"id": "analyst_lead", "name": "Dara"},
        ]

        fake_client = MagicMock()
        fake_client.general_channel_id = "general-123"
        fake_client.get_recent_user_messages.return_value = [
            {
                "id": "9001",
                "from": "@ceo",
                "subject": "Discord message",
                "body": "Thea can you prioritize this now?",
                "channel_id": "general-123",
            }
        ]

        with patch("lib.discord.client.DiscordClient", return_value=fake_client), patch.object(
            module, "get_all_agents", return_value=agents
        ), patch.object(module, "queue_inbox_message") as queue_inbox, patch.object(
            module, "trigger_inbox_request_if_idle"
        ) as trigger_idle, patch.object(
            module, "get_agent_busy", return_value=False
        ):
            module.poll_discord_for_all_agents()

        queue_inbox.assert_called_once()
        queued_agent = queue_inbox.call_args_list[0].args[0]
        self.assertEqual(queued_agent, "strategist_lead")
        self.assertEqual(module.LAST_SEEN_DISCORD_MESSAGE_ID["general"], "9001")
        self.assertEqual(trigger_idle.call_count, 3)

    def test_discord_client_sends_standup_to_standup_channel(self):
        with patch.dict(
            os.environ,
            {
                "DISCORD_BOT_TOKEN": "token-123",
                "DISCORD_GENERAL_CHANNEL_ID": "general-chan",
                "DISCORD_STANDUP_CHANNEL_ID": "standup-chan",
            },
            clear=False,
        ), patch.object(self.discord_module.requests, "request") as request:
            request.return_value = types.SimpleNamespace(
                status_code=200,
                text='{"id":"1"}',
                json=lambda: {"id": "1"},
            )
            client = self.discord_module.DiscordClient()
            ok = client.send_to_ceo(
                agent_id="strategist_lead",
                subject="Daily standup summary",
                message="All agents posted updates.",
                channel="standup",
            )

        self.assertTrue(ok)
        _, kwargs = request.call_args
        self.assertIn("/channels/standup-chan/messages", kwargs["url"])

    def test_discord_client_auto_channel_uses_general(self):
        with patch.dict(
            os.environ,
            {
                "DISCORD_BOT_TOKEN": "token-123",
                "DISCORD_GENERAL_CHANNEL_ID": "general-chan",
                "DISCORD_STANDUP_CHANNEL_ID": "standup-chan",
            },
            clear=False,
        ), patch.object(self.discord_module.requests, "request") as request:
            request.return_value = types.SimpleNamespace(
                status_code=200,
                text='{"id":"1"}',
                json=lambda: {"id": "1"},
            )
            client = self.discord_module.DiscordClient()
            ok = client.send_to_ceo(
                agent_id="strategist_lead",
                subject="Standup-looking subject should not auto-route",
                message="Normal update",
                channel="auto",
            )

        self.assertTrue(ok)
        _, kwargs = request.call_args
        self.assertIn("/channels/general-chan/messages", kwargs["url"])

    def test_discord_client_filters_bot_and_non_ceo_messages(self):
        response_payload = [
            {
                "id": "2",
                "content": "bot message",
                "author": {"id": "bot-1", "username": "agent-bot", "bot": True},
            },
            {
                "id": "3",
                "content": "message from someone else",
                "author": {"id": "not-ceo", "username": "other-user", "bot": False},
            },
            {
                "id": "4",
                "content": "please update me",
                "author": {"id": "ceo-1", "username": "ceo", "global_name": "Yash", "bot": False},
            },
        ]

        with patch.dict(
            os.environ,
            {
                "DISCORD_BOT_TOKEN": "token-123",
                "DISCORD_GENERAL_CHANNEL_ID": "general-chan",
                "DISCORD_CEO_USER_ID": "ceo-1",
            },
            clear=False,
        ), patch.object(self.discord_module.requests, "request") as request:
            request.return_value = types.SimpleNamespace(
                status_code=200,
                text="payload",
                json=lambda: response_payload,
            )
            client = self.discord_module.DiscordClient()
            msgs = client.get_recent_user_messages(channel_id="general-chan")

        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0]["author_id"], "ceo-1")
        self.assertEqual(msgs[0]["body"], "please update me")

    def test_prime_discord_cursor_sets_latest_on_start(self):
        module = self.engine
        module.LAST_SEEN_DISCORD_MESSAGE_ID.clear()

        fake_client = MagicMock()
        fake_client.general_channel_id = "general-123"
        fake_client.get_latest_message_id.return_value = "7777"

        with patch.dict(os.environ, {"DISCORD_PROCESS_EXISTING_ON_START": "0"}, clear=False):
            module.prime_discord_cursor_if_needed(fake_client)

        self.assertEqual(module.LAST_SEEN_DISCORD_MESSAGE_ID.get("general"), "7777")

    def test_prime_discord_cursor_skips_when_replay_enabled(self):
        module = self.engine
        module.LAST_SEEN_DISCORD_MESSAGE_ID.clear()

        fake_client = MagicMock()
        fake_client.general_channel_id = "general-123"

        with patch.dict(os.environ, {"DISCORD_PROCESS_EXISTING_ON_START": "1"}, clear=False):
            module.prime_discord_cursor_if_needed(fake_client)

        fake_client.get_latest_message_id.assert_not_called()
        self.assertIsNone(module.LAST_SEEN_DISCORD_MESSAGE_ID.get("general"))

    def test_discord_client_get_latest_message_id_reads_raw_latest(self):
        payload = [{"id": "9999", "content": "latest from bot", "author": {"bot": True}}]
        with patch.dict(
            os.environ,
            {
                "DISCORD_BOT_TOKEN": "token-123",
                "DISCORD_GENERAL_CHANNEL_ID": "general-chan",
            },
            clear=False,
        ), patch.object(self.discord_module.requests, "request") as request:
            request.return_value = types.SimpleNamespace(
                status_code=200,
                text="payload",
                json=lambda: payload,
            )
            client = self.discord_module.DiscordClient()
            latest_id = client.get_latest_message_id("general-chan")

        self.assertEqual(latest_id, "9999")

    def test_discord_client_get_recent_channel_messages_includes_bots_and_users(self):
        response_payload = [
            {
                "id": "11",
                "content": "agent update",
                "author": {"id": "bot-1", "username": "Theo", "bot": True},
            },
            {
                "id": "12",
                "content": "ceo follow-up",
                "author": {"id": "ceo-1", "username": "ceo", "global_name": "Yash", "bot": False},
            },
        ]
        with patch.dict(
            os.environ,
            {
                "DISCORD_BOT_TOKEN": "token-123",
                "DISCORD_GENERAL_CHANNEL_ID": "general-chan",
                "DISCORD_CEO_USER_ID": "ceo-1",
            },
            clear=False,
        ), patch.object(self.discord_module.requests, "request") as request:
            request.return_value = types.SimpleNamespace(
                status_code=200,
                text="payload",
                json=lambda: response_payload,
            )
            client = self.discord_module.DiscordClient()
            msgs = client.get_recent_channel_messages(channel_id="general-chan", limit=20)

        self.assertEqual(len(msgs), 2)
        self.assertEqual(msgs[0]["id"], "12")
        self.assertEqual(msgs[1]["id"], "11")


if __name__ == "__main__":
    unittest.main(verbosity=2)
