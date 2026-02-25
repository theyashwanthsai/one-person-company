import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools import ingest_youtube_knowledge as module


class TestIngestYouTubeKnowledge(unittest.TestCase):
    def test_language_candidates_order(self):
        self.assertEqual(module._language_candidates("en"), ["en", "en-US", "en-GB"])
        self.assertEqual(module._language_candidates("es"), ["es", "en", "en-US", "en-GB"])

    def test_extract_video_id_from_youtu_be(self):
        url = "https://youtu.be/O_VBdNrX0PM?si=QF6XPO6lATefnUWc"
        self.assertEqual(module._extract_video_id(url), "O_VBdNrX0PM")

    def test_extract_video_id_from_youtube_query(self):
        url = "https://www.youtube.com/watch?v=O_VBdNrX0PM&t=5s"
        self.assertEqual(module._extract_video_id(url), "O_VBdNrX0PM")

    def test_extract_video_id_from_shorts(self):
        url = "https://www.youtube.com/shorts/O_VBdNrX0PM"
        self.assertEqual(module._extract_video_id(url), "O_VBdNrX0PM")

    def test_format_transcript_from_objects(self):
        lines = [
            types.SimpleNamespace(start=5.0, text="hello"),
            types.SimpleNamespace(start=65.0, text="world"),
        ]
        out = module._format_transcript(lines)
        self.assertIn("[00:05] hello", out)
        self.assertIn("[01:05] world", out)

    def test_execute_success_writes_note(self):
        transcript = [
            types.SimpleNamespace(start=0.0, text="line 1"),
            types.SimpleNamespace(start=61.0, text="line 2"),
        ]
        with patch.object(module, "_fetch_transcript", return_value=("abc123", transcript)), patch.object(
            module, "_fetch_title", return_value="My Video"
        ), patch.object(module, "write_markdown_note", return_value={"path": "knowledgebase/sources/youtube/my-video.md"}) as write_note:
            result = module.execute(
                agent_id="strategist_lead",
                url="https://youtu.be/abc123",
                tags=["ai", "agents"],
                folder="sources/youtube",
            )

        self.assertIn("Stored YouTube knowledge note.", result)
        self.assertIn("video_id: abc123", result)
        self.assertIn("path: knowledgebase/sources/youtube/my-video.md", result)

        kwargs = write_note.call_args.kwargs
        self.assertEqual(kwargs["title"], "My Video")
        self.assertEqual(kwargs["source_url"], "https://youtu.be/abc123")
        self.assertEqual(kwargs["folder"], "sources/youtube")
        self.assertEqual(kwargs["aliases"], ["abc123"])
        self.assertIn("youtube", kwargs["tags"])
        self.assertIn("knowledge", kwargs["tags"])
        self.assertIn("ai", kwargs["tags"])
        self.assertIn("agents", kwargs["tags"])

    def test_execute_missing_url(self):
        result = module.execute(agent_id="strategist_lead", url="")
        self.assertEqual(result, "Error: url is required.")

    def test_execute_transcript_error(self):
        with patch.object(module, "_fetch_transcript", side_effect=ValueError("boom")):
            result = module.execute(agent_id="strategist_lead", url="https://youtu.be/abc123")
        self.assertIn("Error fetching transcript:", result)
        self.assertIn("boom", result)

    def test_fetch_transcript_uses_get_transcript(self):
        lines = [{"start": 0.0, "text": "hello"}]
        with patch.object(
            module.YouTubeTranscriptApi, "get_transcript", return_value=lines, create=True
        ) as get_transcript:
            video_id, fetched = module._fetch_transcript("https://youtu.be/abc123", language="en")
        self.assertEqual(video_id, "abc123")
        self.assertEqual(fetched, lines)
        get_transcript.assert_called_once()


if __name__ == "__main__":
    unittest.main(verbosity=2)
