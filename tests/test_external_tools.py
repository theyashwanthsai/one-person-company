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

from utils import print_header, setup_test_environment

from tools.store_external_signal import execute as store_external_signal
from tools.surf_hn import execute as surf_hn
from tools.surf_reddit import execute as surf_reddit
from tools.surf_twitter import execute as surf_twitter

setup_test_environment()

SUPABASE_READY = bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SERVICE_ROLE_KEY"))


async def _maybe_store(signals, source: str, category: str):
    if not SUPABASE_READY or not signals:
        return

    payload = signals[:3]
    await store_external_signal(signals=payload, source=source, category=category)


async def test_twitter():
    """Test Twitter ingestion"""
    print_header("🐦 Testing Twitter ingestion")
    surf = surf_twitter

    result = await surf(query="AI OR machine learning", max_results=5)

    if not result.get("success"):
        print(f"❌ Error: {result.get('error')}")
        return

    tweets = result.get("tweets", [])
    print(f"✅ Surfed {result.get('count', 0)} tweets for query '{result.get('query')}'")
    top = result.get("top_tweet")
    if top:
        print(f"   Top tweet: {top.get('text', '')[:100]}")
    await _maybe_store(tweets, source="twitter", category="test_scan")


async def test_reddit():
    """Test Reddit ingestion"""
    print_header("🔴 Testing Reddit ingestion")
    surf = surf_reddit

    result = await surf(
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
    """Test Hacker News ingestion"""
    print_header("🟠 Testing Hacker News ingestion")
    surf = surf_hn

    result = await surf(hours_window=6, min_points=20, max_posts=30)

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
