import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools import ingest_external_link_knowledge as module


class TestIngestExternalLinkKnowledge(unittest.TestCase):
    def test_extract_tweet_id(self):
        self.assertEqual(
            module._extract_tweet_id("https://x.com/someone/status/1891234567890123456"),
            "1891234567890123456",
        )
        self.assertEqual(
            module._extract_tweet_id("https://twitter.com/someone/status/12345?s=20"),
            "12345",
        )
        self.assertEqual(module._extract_tweet_id("https://example.com/post/123"), "")

    def test_execute_tweet_url_stores_tweet_content(self):
        payload = {
            "text": "Ship every day.",
            "created_at": "2026-02-25T10:00:00Z",
            "favorite_count": 10,
            "conversation_count": 2,
            "retweet_count": 3,
            "user": {"name": "Yash", "screen_name": "yash"},
        }
        fake_response = types.SimpleNamespace(status_code=200, text="ok", json=lambda: payload)

        with patch.object(module.requests, "get", return_value=fake_response), patch.object(
            module, "write_markdown_note", return_value={"path": "knowledgebase/sources/web/tweet.md"}
        ) as write_note:
            out = module.execute(
                agent_id="strategist_lead",
                url="https://x.com/yash/status/1891234567890123456",
                tags=["founder_mode"],
            )

        self.assertIn("Stored external link knowledge note.", out)
        kwargs = write_note.call_args.kwargs
        self.assertEqual(kwargs["note_type"], "source_tweet")
        self.assertIn("tweet", kwargs["tags"])
        self.assertIn("twitter", kwargs["tags"])
        self.assertIn("founder_mode", kwargs["tags"])
        self.assertIn("Ship every day.", kwargs["body"])
        self.assertIn("Tweet Content", kwargs["body"])

    def test_execute_non_tweet_url_uses_html_extraction(self):
        html = "<html><head><title>Hello</title></head><body><main><p>World</p></main></body></html>"
        fake_response = types.SimpleNamespace(status_code=200, text=html)

        with patch.object(module.requests, "get", return_value=fake_response), patch.object(
            module, "write_markdown_note", return_value={"path": "knowledgebase/sources/web/hello.md"}
        ) as write_note:
            out = module.execute(agent_id="strategist_lead", url="https://example.com/article")

        self.assertIn("Stored external link knowledge note.", out)
        kwargs = write_note.call_args.kwargs
        self.assertEqual(kwargs["note_type"], "source_web")
        self.assertIn("Extracted Content", kwargs["body"])
        self.assertIn("World", kwargs["body"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
