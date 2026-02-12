"""Test script for external integration tools.
Run this to verify your API credentials are working.
"""

import asyncio
import os

from tests.utils import print_header, setup_test_environment

from tools.store_external_signal import execute as store_external_signal
from tools.surf_hn import execute as surf_hn
from tools.surf_reddit import execute as surf_reddit

setup_test_environment()

SUPABASE_READY = bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SERVICE_ROLE_KEY"))


async def _maybe_store(signals, source: str, category: str):
    if not SUPABASE_READY or not signals:
        return

    payload = signals[:3]
    await store_external_signal(signals=payload, source=source, category=category)


async def test_twitter():
    """Twitter surf is disabled until we re-enable the tool."""
    print_header("🐦 Twitter surf is currently suspended (skipped)")


async def test_reddit():
    """Test Reddit ingestion."
    print_header("🔴 Testing Reddit ingestion")
    result = await surf_reddit(
        subreddits=["ArcRaiders", "MachineLearning"],
        sort="new",
        limit_per_subreddit=5,
        min_score=0,
        max_age_hours=24,
    )

    if not result.get("success"):
        print(f"❌ Error: {result.get('error')}")
        return

    posts = result.get("posts", [])
    print(f"✅ Surfed {result.get('count', 0)} Reddit posts from {', '.join(result.get('subreddits', []))} in {result.get('range')}")
    top_post = result.get("top_post")
    if top_post:
        print(f"   Top post: {top_post.get('title')}")
        print(f"   Score: {top_post.get('score')}")
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


async def main():
    print_header("🧪 External Tools Test Suite")

    has_twitter = bool(os.getenv("TWITTER_BEARER_TOKEN"))

    print(f"   Twitter API: {'✅ configured' if has_twitter else '❌ not configured'}")
    print(f"   Supabase: {'✅ configured' if SUPABASE_READY else '❌ not configured'}")

    await test_hackernews()
    await test_reddit()

    if has_twitter:
        await test_twitter()

    print_header("✅ Test suite complete")


if __name__ == "__main__":
    asyncio.run(main())
