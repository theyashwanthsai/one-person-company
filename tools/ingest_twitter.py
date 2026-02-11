"""
Tool: Ingest Twitter
Fetch recent tweets from specified accounts or search terms and store as external signals.
"""

import os
import httpx
from datetime import datetime
from lib.supabase_client import get_supabase

# Twitter API v2 configuration
BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")

SCHEMA = {
    "name": "ingest_twitter",
    "description": "Fetch recent tweets from Twitter accounts or search terms and store as external signals. Use this to scan what's trending, what competitors are posting, or what topics are getting engagement.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query (e.g. '@username', '#hashtag', or 'topic keywords'). For user timeline use 'from:username'. See Twitter API search syntax."
            },
            "max_results": {
                "type": "integer",
                "description": "Number of tweets to fetch (max 100)",
                "default": 20
            },
            "category": {
                "type": "string",
                "description": "Category for these signals (e.g. 'competitor_content', 'trending_topic', 'industry_news')",
                "default": "twitter_scan"
            }
        },
        "required": ["query"]
    }
}


async def execute(query: str, max_results: int = 20, category: str = "twitter_scan") -> dict:
    """
    Fetch tweets and store as external signals.
    Returns summary of what was ingested.
    """
    
    if not BEARER_TOKEN:
        return {
            "success": False,
            "error": "Twitter API not configured. Set TWITTER_BEARER_TOKEN in environment."
        }
    
    supabase = get_supabase()
    
    try:
        # Twitter API v2 recent search endpoint
        url = "https://api.twitter.com/2/tweets/search/recent"
        
        params = {
            "query": query,
            "max_results": min(max_results, 100),
            "tweet.fields": "created_at,public_metrics,author_id",
            "expansions": "author_id",
            "user.fields": "username,name"
        }
        
        headers = {
            "Authorization": f"Bearer {BEARER_TOKEN}"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()
        
        tweets = data.get("data", [])
        users = {u["id"]: u for u in data.get("includes", {}).get("users", [])}
        
        if not tweets:
            return {
                "success": True,
                "tweets_ingested": 0,
                "message": f"No tweets found for query: {query}"
            }
        
        # Store each tweet as an external signal
        signals_created = []
        
        for tweet in tweets:
            author = users.get(tweet["author_id"], {})
            metrics = tweet.get("public_metrics", {})
            
            signal_data = {
                "source": "twitter",
                "category": category,
                "content": tweet.get("text", ""),
                "url": f"https://twitter.com/i/web/status/{tweet['id']}",
                "author": author.get("username", "unknown"),
                "metrics": {
                    "likes": metrics.get("like_count", 0),
                    "retweets": metrics.get("retweet_count", 0),
                    "replies": metrics.get("reply_count", 0),
                    "impressions": metrics.get("impression_count", 0)
                },
                "raw_data": {
                    "tweet_id": tweet["id"],
                    "author_name": author.get("name", ""),
                    "created_at": tweet.get("created_at")
                },
                "ingested_at": datetime.utcnow().isoformat()
            }
            
            result = supabase.table("external_signals").insert(signal_data).execute()
            if result.data:
                signals_created.append(result.data[0]["id"])
        
        return {
            "success": True,
            "tweets_ingested": len(signals_created),
            "query": query,
            "category": category,
            "signal_ids": signals_created[:5],  # First 5 IDs
            "top_tweet": {
                "text": tweets[0]["text"][:100],
                "author": users.get(tweets[0]["author_id"], {}).get("username"),
                "likes": tweets[0].get("public_metrics", {}).get("like_count", 0)
            }
        }
        
    except httpx.HTTPStatusError as e:
        return {
            "success": False,
            "error": f"Twitter API error: {e.response.status_code} - {e.response.text}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to ingest tweets: {str(e)}"
        }

