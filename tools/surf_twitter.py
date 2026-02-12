"""Tool: Surf Twitter
Fetch tweets via Twitter API v2 and return structured data for agents to analyze."""

import os
import httpx

BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")

SCHEMA = {
    "type": "function",
    "function": {
        "name": "surf_twitter",
        "description": "Surf Twitter via search queries and return tweets for agents to review before deciding what to store.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (e.g. '@username', '#hashtag', or keywords).",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Number of tweets to fetch (max 100)",
                    "default": 20
                }
            },
            "required": ["query"]
        }
    }
}


def _normalize_tweet(tweet: dict, users: dict) -> dict:
    user = users.get(tweet["author_id"], {})
    metrics = tweet.get("public_metrics", {})
    return {
        "id": tweet.get("id"),
        "text": tweet.get("text", ""),
        "author": user.get("username", "unknown"),
        "author_name": user.get("name", ""),
        "created_at": tweet.get("created_at"),
        "url": f"https://twitter.com/i/web/status/{tweet.get('id')}",
        "metrics": {
            "likes": metrics.get("like_count", 0),
            "retweets": metrics.get("retweet_count", 0),
            "replies": metrics.get("reply_count", 0),
            "impressions": metrics.get("impression_count", 0)
        },
        "raw_data": tweet
    }


async def execute(query: str, max_results: int = 20) -> dict:
    if not BEARER_TOKEN:
        return {
            "success": False,
            "error": "TWITTER_BEARER_TOKEN is missing."
        }

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

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as exc:
        return {"success": False, "error": f"Twitter API error: {exc.response.status_code}"}
    except Exception as exc:
        return {"success": False, "error": f"Failed to surf Twitter: {exc}"}

    tweets = data.get("data", [])
    users = {u["id"]: u for u in data.get("includes", {}).get("users", [])}
    normalized = [_normalize_tweet(tweet, users) for tweet in tweets]
    top_tweet = max(normalized, key=lambda item: item["metrics"]["likes"]) if normalized else None

    return {
        "success": True,
        "query": query,
        "tweets": normalized,
        "top_tweet": top_tweet,
        "count": len(normalized)
    }
