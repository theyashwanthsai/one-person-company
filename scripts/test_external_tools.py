"""
Test script for external integration tools.
Run this to verify your API credentials are working.
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment
load_dotenv()

async def test_twitter():
    """Test Twitter ingestion"""
    print("\n🐦 Testing Twitter ingestion...")
    from tools.ingest_twitter import execute
    
    result = await execute(
        query="AI OR machine learning",
        max_results=5,
        category="test_scan"
    )
    
    if result["success"]:
        print(f"✅ Ingested {result['tweets_ingested']} tweets")
        print(f"   Top tweet: {result['top_tweet']['text']}")
        print(f"   Author: @{result['top_tweet']['author']}")
    else:
        print(f"❌ Error: {result['error']}")


async def test_reddit():
    """Test Reddit ingestion"""
    print("\n🔴 Testing Reddit ingestion...")
    from tools.ingest_reddit import execute
    
    result = await execute(
        subreddit="programming",
        sort="hot",
        limit=5,
        category="test_scan"
    )
    
    if result["success"]:
        print(f"✅ Ingested {result['posts_ingested']} posts from r/{result['subreddit']}")
        print(f"   Top post: {result['top_post']['title']}")
        print(f"   Score: {result['top_post']['score']}")
    else:
        print(f"❌ Error: {result['error']}")


async def test_hackernews():
    """Test Hacker News ingestion"""
    print("\n🟠 Testing Hacker News ingestion...")
    from tools.ingest_hackernews import execute
    
    result = await execute(
        story_type="top",
        limit=5,
        category="test_scan"
    )
    
    if result["success"]:
        print(f"✅ Ingested {result['stories_ingested']} stories")
        print(f"   Top story: {result['top_story']['title']}")
        print(f"   Score: {result['top_story']['score']}")
    else:
        print(f"❌ Error: {result['error']}")


async def test_publish():
    """Test Twitter publishing (will actually post!)"""
    print("\n📤 Testing Twitter publishing...")
    print("   ⚠️  This will post a real tweet to your account!")
    
    confirm = input("   Continue? (yes/no): ")
    if confirm.lower() != "yes":
        print("   Skipped.")
        return
    
    from tools.publish_content import execute
    
    result = await execute(
        text="🤖 Testing the one-person company agent system!\n\nThis is an automated test post.",
    )
    
    if result["success"]:
        print(f"✅ Posted {result['tweets_posted']} tweet(s)")
        print(f"   URL: {result['primary_url']}")
    else:
        print(f"❌ Error: {result['error']}")


async def test_metrics():
    """Test metrics fetching"""
    print("\n📊 Testing metrics fetching...")
    
    tweet_id = input("   Enter a tweet ID to fetch metrics for: ")
    if not tweet_id:
        print("   Skipped.")
        return
    
    from tools.fetch_metrics import execute
    
    result = await execute(tweet_id=tweet_id, update_pipeline=False)
    
    if result["success"]:
        metrics = result["metrics"]
        print(f"✅ Fetched metrics:")
        print(f"   Likes: {metrics['likes']}")
        print(f"   Retweets: {metrics['retweets']}")
        print(f"   Replies: {metrics['replies']}")
        print(f"   Engagement rate: {metrics['engagement_rate']}%")
        print(f"   Performance: {result['performance']}")
    else:
        print(f"❌ Error: {result['error']}")


async def main():
    print("=" * 60)
    print("🧪 External Tools Test Suite")
    print("=" * 60)
    
    # Check environment
    print("\n🔧 Checking environment variables...")
    
    has_twitter = bool(os.getenv("TWITTER_BEARER_TOKEN"))
    has_reddit = bool(os.getenv("REDDIT_CLIENT_ID"))
    
    print(f"   Twitter API: {'✅ configured' if has_twitter else '❌ not configured'}")
    print(f"   Reddit API: {'✅ configured' if has_reddit else '❌ not configured'}")
    
    # Run tests
    await test_hackernews()  # Always works (no auth needed)
    
    if has_twitter:
        await test_twitter()
    
    if has_reddit:
        await test_reddit()
    
    # Optional: Publishing test
    if has_twitter:
        print("\n" + "=" * 60)
        await test_publish()
    
    # Optional: Metrics test
    if has_twitter:
        print("\n" + "=" * 60)
        await test_metrics()
    
    print("\n" + "=" * 60)
    print("✅ Test suite complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

