"""Tool: Surf Twitter
Fetch tweets using keyword queries via Twitter API v2 recent search.
"""

import os
from typing import List, Optional

import httpx

BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")

SCHEMA = {
    "type": "function",
    "function": {
        "name": "surf_twitter",
        "description": "Search Twitter posts by keywords and return structured tweets for agents to review before saving.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Raw Twitter search query (optional if keywords are provided).",
                },
                "keywords": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Keywords to search. Combined with OR if query is not provided.",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Number of tweets to fetch (max 100).",
                    "default": 100,
                    "minimum": 10,
                    "maximum": 100,
                },
            },
        },
    },
}


def _build_query(query: Optional[str], keywords: Optional[List[str]]) -> Optional[str]:
    if query and query.strip():
        return query.strip()
    if keywords:
        words = [k.strip() for k in keywords if k and k.strip()]
        if words:
            joined = " OR ".join(f'"{w}"' if " " in w else w for w in words)
            return f"({joined}) -is:retweet lang:en"
    return None


def _normalize_tweet(tweet: dict, users: dict) -> dict:
    user = users.get(tweet.get("author_id"), {})
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
            "quotes": metrics.get("quote_count", 0),
            "bookmarks": metrics.get("bookmark_count", 0),
            "impressions": metrics.get("impression_count", 0),
        },
        "raw_data": tweet,
    }


async def execute(
    agent_id: Optional[str] = None,
    query: Optional[str] = None,
    keywords: Optional[List[str]] = None,
    max_results: int = 100,
) -> dict:
    del agent_id

    if not BEARER_TOKEN:
        return {"success": False, "error": "TWITTER_BEARER_TOKEN is missing."}

    built_query = _build_query(query, keywords)
    if not built_query:
        return {"success": False, "error": "Provide either query or keywords."}

    url = "https://api.twitter.com/2/tweets/search/recent"
    params = {
        "query": built_query,
        "max_results": max(10, min(max_results, 100)),
        "tweet.fields": "created_at,public_metrics,author_id,lang",
        "expansions": "author_id",
        "user.fields": "username,name",
    }
    headers = {"Authorization": f"Bearer {BEARER_TOKEN}"}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
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
        "query": built_query,
        "tweets": normalized,
        "top_tweet": top_tweet,
        "count": len(normalized),
    }
