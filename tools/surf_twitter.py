"""Tool: Surf Twitter
Fetch tweets using keyword queries via Twitter API v2 recent search.

Currently DISABLED for this project – use Reddit/HN instead.
"""

import os
from typing import List, Optional

import httpx

BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")

SCHEMA = {
    "type": "function",
    "function": {
        "name": "surf_twitter",
        "description": "DISABLED. Do not use. Use Reddit/HN tools instead.",
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
    del agent_id, query, keywords, max_results
    return {
        "success": False,
        "error": "surf_twitter is disabled for now. Use surf_reddit and surf_hn instead.",
    }
