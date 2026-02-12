"""Tool: Surf Reddit
Fetch Reddit posts via the public JSON endpoints and return structured content for agents to inspect."""

import logging
import time
from datetime import datetime
from typing import Iterable, List, Optional

import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SCHEMA = {
    "type": "function",
    "function": {
        "name": "surf_reddit",
        "description": "Surf Reddit by calling /r/<subreddit>/<sort>.json and return posts for agents to evaluate before saving.",
        "parameters": {
            "type": "object",
            "properties": {
                "subreddits": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of subreddit names (without r/)."
                },
                "subreddit": {
                    "type": "string",
                    "description": "Single subreddit name (fall-back)."
                },
                "sort": {
                    "type": "string",
                    "enum": ["hot", "new", "top", "rising"],
                    "description": "Listing sort order",
                    "default": "new"
                },
                "limit_per_subreddit": {
                    "type": "integer",
                    "description": "Max posts to fetch per subreddit (max 50)",
                    "default": 25,
                    "minimum": 1,
                    "maximum": 50
                },
                "time_filter": {
                    "type": "string",
                    "enum": ["hour", "day", "week", "month", "year", "all"],
                    "description": "Time filter (applies to top sort).",
                    "default": "day"
                },
                "min_score": {
                    "type": "integer",
                    "description": "Minimum score required for a post.",
                    "default": 0
                },
                "max_age_hours": {
                    "type": "integer",
                    "description": "Only include posts younger than this many hours.",
                    "minimum": 1
                }
            }
        }
    }
}

USER_AGENT = "one-person-company/1.0 (+https://theyashwanthsai.com)"


def _normalize_subreddits(subreddits: Optional[Iterable[str]], subreddit: Optional[str]) -> List[str]:
    names: List[str] = []
    if subreddits:
        names.extend([name.strip() for name in subreddits if name and name.strip()])
    if subreddit:
        names.append(subreddit.strip())
    if not names:
        names = ["programming"]
    seen = set()
    clean: List[str] = []
    for name in names:
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        clean.append(name)
    return clean


def _build_url(subreddit: str, sort: str) -> str:
    return f"https://www.reddit.com/r/{subreddit}/{sort}.json"


def _post_matches_filters(post: dict, min_score: int, cutoff_ts: Optional[int]) -> bool:
    score = post.get("score", 0)
    created = post.get("created_utc", 0)
    if score < min_score:
        return False
    if cutoff_ts and created < cutoff_ts:
        return False
    return True


async def _fetch_subreddit_posts(
    client: httpx.AsyncClient,
    subreddit: str,
    sort: str,
    limit: int,
    time_filter: str,
    min_score: int,
    cutoff_ts: Optional[int]
) -> List[dict]:
    url = _build_url(subreddit, sort)
    params = {"limit": limit}
    if sort == "top":
        params["t"] = time_filter

    response = await client.get(url, params=params)
    response.raise_for_status()
    payload = response.json()
    posts = payload.get("data", {}).get("children", [])

    filtered: List[dict] = []
    for child in posts:
        post = child.get("data") or {}
        if not post or post.get("stickied"):
            continue
        if not _post_matches_filters(post, min_score, cutoff_ts):
            continue
        filtered.append(post)
    logger.info("Fetched %s posts from r/%s", len(filtered), subreddit)
    return filtered


def _normalize_post(post: dict) -> dict:
    title = post.get("title") or "Untitled"
    created_at = datetime.fromtimestamp(post.get("created_utc", 0)).isoformat()
    url = post.get("url") or f"https://reddit.com{post.get('permalink')}"

    return {
        "title": title,
        "url": url,
        "author": f"u/{post.get('author') or 'deleted'}",
        "score": post.get("score", 0),
        "comments": post.get("num_comments", 0),
        "created_at": created_at,
        "content": f"{title}\n\n{post.get('selftext', '')[:400]}",
        "engagement_score": post.get("score", 0) + post.get("num_comments", 0) * 2,
        "raw_data": {
            "id": post.get("id"),
            "subreddit": post.get("subreddit"),
            "created_utc": post.get("created_utc"),
            "permalink": post.get("permalink"),
            "flair": post.get("link_flair_text"),
            "domain": post.get("domain")
        }
    }


async def execute(
    subreddits: Optional[List[str]] = None,
    subreddit: Optional[str] = None,
    sort: str = "new",
    limit_per_subreddit: int = 25,
    time_filter: str = "day",
    min_score: int = 0,
    max_age_hours: Optional[int] = None,
) -> dict:
    """Surf Reddit and return posts without saving them."""

    names = _normalize_subreddits(subreddits, subreddit)
    cutoff_ts = None
    range_label = "latest"
    if max_age_hours is not None:
        cutoff_ts = int(time.time()) - max_age_hours * 3600
        range_label = f"last {max_age_hours}h"

    try:
        async with httpx.AsyncClient(headers={"User-Agent": USER_AGENT}, timeout=30.0) as client:
            aggregated: List[dict] = []
            for name in names:
                posts = await _fetch_subreddit_posts(
                    client,
                    name,
                    sort,
                    limit_per_subreddit,
                    time_filter,
                    min_score,
                    cutoff_ts
                )
                normalized = [_normalize_post(post) for post in posts]
                aggregated.extend(normalized)
    except httpx.HTTPStatusError as exc:
        return {"success": False, "error": f"Reddit API error: {exc.response.status_code}"}
    except Exception as exc:
        return {"success": False, "error": f"Failed to surf Reddit: {exc}"}

    top_post = max(aggregated, key=lambda item: item["score"]) if aggregated else None

    return {
        "success": True,
        "subreddits": names,
        "sort": sort,
        "range": range_label,
        "posts": aggregated,
        "top_post": top_post,
        "count": len(aggregated)
    }
