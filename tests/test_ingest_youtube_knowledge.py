import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools import ingest_youtube_knowledge as module


class TestIngestYoutubeKnowledge(unittest.TestCase):

    # ------------------------------------------------------------------ #
    # _extract_video_id                                                    #
    # ------------------------------------------------------------------ #

    def test_extract_video_id_standard_url(self):
        self.assertEqual(
            module._extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ"),
            "dQw4w9WgXcQ",
        )

    def test_extract_video_id_short_url(self):
        self.assertEqual(
            module._extract_video_id("https://youtu.be/dQw4w9WgXcQ"),
            "dQw4w9WgXcQ",
        )

    def test_extract_video_id_short_url_with_query(self):
        self.assertEqual(
            module._extract_video_id("https://youtu.be/dQw4w9WgXcQ?t=42"),
            "dQw4w9WgXcQ",
        )

    def test_extract_video_id_url_with_extra_params(self):
        self.assertEqual(
            module._extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=10s&list=PL123"),
            "dQw4w9WgXcQ",
        )

    def test_extract_video_id_invalid_url_returns_none(self):
        self.assertIsNone(module._extract_video_id("https://example.com/watch?v=abc"))

    # ------------------------------------------------------------------ #
    # _fetch_title                                                         #
    # ------------------------------------------------------------------ #

    def test_fetch_title_success(self):
        payload = {"title": "My Awesome Video"}
        fake_response = types.SimpleNamespace(status_code=200, json=lambda: payload)

        with patch.object(module.requests, "get", return_value=fake_response):
            title = module._fetch_title("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ")

        self.assertEqual(title, "My Awesome Video")

    def test_fetch_title_http_error_returns_fallback(self):
        fake_response = types.SimpleNamespace(status_code=404, json=lambda: {})

        with patch.object(module.requests, "get", return_value=fake_response):
            title = module._fetch_title("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ")

        self.assertEqual(title, "YouTube Video dQw4w9WgXcQ")

    def test_fetch_title_exception_returns_fallback(self):
        with patch.object(module.requests, "get", side_effect=Exception("network error")):
            title = module._fetch_title("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ")

        self.assertEqual(title, "YouTube Video dQw4w9WgXcQ")

    def test_fetch_title_empty_title_returns_fallback(self):
        payload = {"title": ""}
        fake_response = types.SimpleNamespace(status_code=200, json=lambda: payload)

        with patch.object(module.requests, "get", return_value=fake_response):
            title = module._fetch_title("https://www.youtube.com/watch?v=abc123", "abc123")

        self.assertEqual(title, "YouTube Video abc123")

    # ------------------------------------------------------------------ #
    # _format_transcript                                                   #
    # ------------------------------------------------------------------ #

    def test_format_transcript_with_timestamps_dicts(self):
        lines = [
            {"text": "Hello world", "start": 0.0},
            {"text": "How are you", "start": 65.5},
        ]
        result = module._format_transcript(lines, include_timestamps=True)
        self.assertIn("[00:00] Hello world", result)
        self.assertIn("[01:05] How are you", result)

    def test_format_transcript_without_timestamps(self):
        lines = [
            {"text": "Hello world", "start": 0.0},
            {"text": "How are you", "start": 65.5},
        ]
        result = module._format_transcript(lines, include_timestamps=False)
        self.assertNotIn("[", result)
        self.assertIn("Hello world", result)
        self.assertIn("How are you", result)

    def test_format_transcript_with_object_items(self):
        item1 = types.SimpleNamespace(text="First line", start=0.0)
        item2 = types.SimpleNamespace(text="Second line", start=30.0)
        result = module._format_transcript([item1, item2], include_timestamps=True)
        self.assertIn("[00:00] First line", result)
        self.assertIn("[00:30] Second line", result)

    def test_format_transcript_skips_empty_text(self):
        lines = [
            {"text": "", "start": 0.0},
            {"text": "  ", "start": 1.0},
            {"text": "Real content", "start": 2.0},
        ]
        result = module._format_transcript(lines)
        self.assertEqual(result.count("\n"), 0)
        self.assertIn("Real content", result)

    def test_format_transcript_newlines_replaced(self):
        lines = [{"text": "Line\nwith\nnewlines", "start": 0.0}]
        result = module._format_transcript(lines, include_timestamps=False)
        self.assertNotIn("\n\n", result)
        self.assertIn("Line with newlines", result)

    # ------------------------------------------------------------------ #
    # execute                                                              #
    # ------------------------------------------------------------------ #

    def _make_transcript_lines(self):
        return [
            {"text": "Welcome to the video", "start": 0.0},
            {"text": "Today we learn Python", "start": 5.0},
        ]

    def test_execute_stores_note_successfully(self):
        transcript_lines = self._make_transcript_lines()

        with (
            patch.object(module, "_fetch_transcript", return_value=("dQw4w9WgXcQ", transcript_lines)),
            patch.object(module, "_fetch_title", return_value="Learn Python Fast"),
            patch.object(
                module, "write_markdown_note", return_value={"path": "sources/youtube/learn-python-fast.md"}
            ) as write_note,
        ):
            out = module.execute(
                agent_id="researcher",
                url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                tags=["python", "tutorial"],
            )

        self.assertIn("Stored YouTube knowledge note.", out)
        self.assertIn("Learn Python Fast", out)
        self.assertIn("dQw4w9WgXcQ", out)

        kwargs = write_note.call_args.kwargs
        self.assertEqual(kwargs["note_type"], "source_youtube")
        self.assertIn("youtube", kwargs["tags"])
        self.assertIn("knowledge", kwargs["tags"])
        self.assertIn("python", kwargs["tags"])
        self.assertIn("tutorial", kwargs["tags"])
        self.assertIn("Welcome to the video", kwargs["body"])
        self.assertIn("Full Transcript", kwargs["body"])
        self.assertEqual(kwargs["folder"], "sources/youtube")

    def test_execute_uses_custom_folder(self):
        transcript_lines = self._make_transcript_lines()

        with (
            patch.object(module, "_fetch_transcript", return_value=("abc123", transcript_lines)),
            patch.object(module, "_fetch_title", return_value="Some Video"),
            patch.object(module, "write_markdown_note", return_value={"path": "custom/folder/some-video.md"}) as write_note,
        ):
            module.execute(
                agent_id="researcher",
                url="https://youtu.be/abc123",
                folder="custom/folder",
            )

        self.assertEqual(write_note.call_args.kwargs["folder"], "custom/folder")

    def test_execute_missing_url_returns_error(self):
        out = module.execute(agent_id="researcher", url="")
        self.assertIn("Error", out)
        self.assertIn("url is required", out)

    def test_execute_transcript_fetch_failure_returns_error(self):
        with patch.object(module, "_fetch_transcript", side_effect=Exception("transcript unavailable")):
            out = module.execute(
                agent_id="researcher",
                url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            )

        self.assertIn("Error fetching transcript", out)
        self.assertIn("transcript unavailable", out)

    def test_execute_empty_transcript_returns_error(self):
        with patch.object(module, "_fetch_transcript", return_value=("dQw4w9WgXcQ", [])):
            out = module.execute(
                agent_id="researcher",
                url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            )

        self.assertIn("No transcript lines found", out)

    def test_execute_default_language_is_english(self):
        transcript_lines = self._make_transcript_lines()

        with (
            patch.object(module, "_fetch_transcript", return_value=("abc", transcript_lines)) as fetch,
            patch.object(module, "_fetch_title", return_value="Video"),
            patch.object(module, "write_markdown_note", return_value={"path": "x.md"}),
        ):
            module.execute(agent_id="researcher", url="https://youtu.be/abc")

        _, call_kwargs = fetch.call_args
        self.assertEqual(call_kwargs.get("language", "en"), "en")

    def test_execute_custom_language(self):
        transcript_lines = self._make_transcript_lines()

        with (
            patch.object(module, "_fetch_transcript", return_value=("abc", transcript_lines)) as fetch,
            patch.object(module, "_fetch_title", return_value="Video"),
            patch.object(module, "write_markdown_note", return_value={"path": "x.md"}),
        ):
            module.execute(agent_id="researcher", url="https://youtu.be/abc", language="fr")

        _, call_kwargs = fetch.call_args
        self.assertEqual(call_kwargs.get("language"), "fr")

    def test_execute_body_contains_source_metadata(self):
        transcript_lines = self._make_transcript_lines()
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

        with (
            patch.object(module, "_fetch_transcript", return_value=("dQw4w9WgXcQ", transcript_lines)),
            patch.object(module, "_fetch_title", return_value="My Video"),
            patch.object(module, "write_markdown_note", return_value={"path": "x.md"}) as write_note,
        ):
            module.execute(agent_id="my_agent", url=url)

        body = write_note.call_args.kwargs["body"]
        self.assertIn(url, body)
        self.assertIn("dQw4w9WgXcQ", body)
        self.assertIn("my_agent", body)


if __name__ == "__main__":
    unittest.main(verbosity=2)