"""Test script for external integration tools.
Run this to verify your API credentials are working.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add repo root so shared modules can be imported even when the script lives in tests/
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from datetime import datetime

from utils import print_header, setup_test_environment

# Load .env before importing tools that initialize clients at import time.
setup_test_environment()

from lib.tool_runner import run_agent_step
from tools.store_external_signal import execute as store_external_signal
from tools.surf_hn import execute as surf_hn
from tools.surf_reddit import execute as surf_reddit
from tools.surf_twitter import execute as surf_twitter
from tools.publish_content import execute as publish_content

SUPABASE_READY = bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
RUN_PUBLISH_TEST = os.getenv("RUN_TWITTER_PUBLISH_TEST") == "1"
RUN_AGENT_EXTERNAL_SCAN_TEST = os.getenv("RUN_AGENT_EXTERNAL_SCAN_TEST") == "1"


async def _maybe_store(signals, source: str, category: str):
    if not SUPABASE_READY or not signals:
        return

    payload = signals[:3]
    result = await store_external_signal(signals=payload, source=source, category=category)
    if result.get("success"):
        print(
            "   ✅ Stored {total} signals in Supabase (new: {ins}, seen-again: {upd})".format(
                total=result.get("signals_stored", 0),
                ins=result.get("inserted_count", 0),
                upd=result.get("updated_count", 0),
            )
        )
    else:
        print(f"   ❌ Store failed: {result.get('error')}")


async def test_twitter():
    """Test Twitter ingestion by keywords."""
    print_header("🐦 Testing Twitter ingestion")
    result = await surf_twitter(
        keywords=["ai agents", "open source"],
        max_results=15,
    )

    if not result.get("success"):
        print(f"❌ Error: {result.get('error')}")
        return

    tweets = result.get("tweets", [])
    print(f"✅ Surfed {result.get('count', 0)} tweets")
    top = result.get("top_tweet")
    if top:
        print(f"   Top tweet: {top.get('text', '')[:80]}...")
        print(f"   Likes: {top.get('metrics', {}).get('likes', 0)}")
    await _maybe_store(tweets, source="twitter", category="test_scan")


async def test_reddit():
    """Test Reddit ingestion via public subreddit JSON endpoints."""
    print_header("🔴 Testing Reddit ingestion")
    result = await surf_reddit(
        subreddits=["MachineLearning", "LocalLLaMA"],
        sort="new",
        limit_per_subreddit=20,
        min_score=3,
        max_age_hours=24,
    )

    if not result.get("success"):
        print(f"❌ Error: {result.get('error')}")
        return

    posts = result.get("posts", [])
    print(f"✅ Surfed {result.get('count', 0)} Reddit posts")
    top = result.get("top_post")
    if top:
        print(f"   Top post: r/{top.get('subreddit')} - {top.get('title', '')[:80]}...")
        print(f"   Score: {top.get('score', 0)}")
    await _maybe_store(posts, source="reddit", category="test_scan")


async def test_hackernews():
    """Test Hacker News ingestion."""
    print_header("🟠 Testing Hacker News ingestion")
    result = await surf_hn(hours_window=6, min_points=20, max_posts=30)

    if not result.get("success"):
        print(f"❌ Error: {result.get('error')}")
        return

    posts = result.get("posts", [])
    print(f"✅ Surfed {result.get('count', 0)} Hacker News posts ({result.get('range')})")
    top = result.get("top_post")
    if top:
        print(f"   Top story: {top.get('title')}")
        print(f"   Score: {top.get('score')}")
    await _maybe_store(posts, source="hackernews", category="test_scan")


async def test_publish_content():
    """Optionally test the publishing tool (requires RUN_TWITTER_PUBLISH_TEST=1)."""
    print_header("📤 Testing Twitter publishing")
    timestamp = datetime.utcnow().strftime("%H:%M:%S")
    text = os.getenv("TWITTER_PUBLISH_TEST_TEXT", f"Automated test post at {timestamp}")

    result = await publish_content(text=text)
    if result.get("success"):
        print(f"✅ Published {result.get('tweets_posted')} tweet(s): {result.get('primary_url')}")
    else:
        print(f"❌ Publish failed: {result.get('error')}")


async def test_agent_external_scan():
    """Run Thea (strategist_lead) on a live external-scan task via the tool loop."""
    print_header("🤖 Testing agent-driven external scan (Thea)")

    response, tool_calls = await run_agent_step(
        agent_id="strategist_lead",
        task=(
            "Scan external sources for AI/agent trends from Reddit, Hacker News, and Twitter. "
            "Use available surf/scan tools, summarize top patterns, and note one actionable idea."
        ),
    )

    called_tools = [item.get("tool") for item in tool_calls]
    print(f"✅ Agent response: {response[:180]}...")
    print(f"   Tool calls made: {len(tool_calls)}")
    if called_tools:
        print(f"   Called: {', '.join(called_tools)}")

    external_scan_tools = {"surf_reddit", "surf_hn", "surf_twitter", "scan_external_source"}
    if not set(called_tools) & external_scan_tools:
        raise AssertionError(
            f"Agent did not call an external scan tool. Called tools: {called_tools}"
        )


async def main():
    print_header("🧪 External Tools Test Suite")

    has_twitter = bool(os.getenv("TWITTER_BEARER_TOKEN"))
    has_openai = bool(os.getenv("OPENAI_API_KEY"))

    print(f"   Twitter API: {'✅ configured' if has_twitter else '❌ not configured'}")
    print("   Reddit API: ✅ not required (public endpoints)")
    print(f"   Supabase: {'✅ configured' if SUPABASE_READY else '❌ not configured'}")
    print(f"   OpenAI API: {'✅ configured' if has_openai else '❌ not configured'}")

    await test_hackernews()
    await test_reddit()

    if has_twitter:
        await test_twitter()
        if RUN_PUBLISH_TEST:
            await test_publish_content()

    if RUN_AGENT_EXTERNAL_SCAN_TEST:
        if has_openai:
            await test_agent_external_scan()
        else:
            print("⚠️ Skipping agent external scan test (OPENAI_API_KEY not set)")

    print_header("✅ Test suite complete")


if __name__ == "__main__":
    asyncio.run(main())
