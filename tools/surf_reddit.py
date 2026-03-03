"""Tool: Surf Reddit
Fetch Reddit posts from public subreddit JSON endpoints and return structured
posts for agents to review before saving.
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional

import httpx

REDDIT_BASE_URL = "https://www.reddit.com"
USER_AGENT = "one-person-company/1.0 (by u/one_person_company_bot)"

SCHEMA = {
    "type": "function",
    "function": {
        "name": "surf_reddit",
        "description": "Surf Reddit subreddits and return structured posts for agents to review before saving.",
        "parameters": {
            "type": "object",
            "properties": {
                "subreddits": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Subreddits to scan (without /r/ prefix).",
                },
                "sort": {
                    "type": "string",
                    "enum": ["hot", "new", "top", "rising"],
                    "description": "Sort mode to use per subreddit.",
                    "default": "new",
                },
                "limit_per_subreddit": {
                    "type": "integer",
                    "description": "Maximum posts to pull per subreddit before filters.",
                    "default": 25,
                    "minimum": 1,
                    "maximum": 100,
                },
                "min_score": {
                    "type": "integer",
                    "description": "Minimum Reddit score to include.",
                    "default": 0,
                },
                "max_age_hours": {
                    "type": "integer",
                    "description": "Ignore posts older than this many hours.",
                    "default": 24,
                    "minimum": 1,
                },
                "time_filter": {
                    "type": "string",
                    "enum": ["hour", "day", "week", "month", "year", "all"],
                    "description": "Reddit time filter, mainly used with sort=top.",
                    "default": "day",
                },
            },
        },
    },
}


def _normalize_post(child: dict, subreddit: str) -> dict:
    data = child.get("data", {})
    created_utc = data.get("created_utc", 0)
    created_at = datetime.fromtimestamp(created_utc, tz=timezone.utc)
    permalink = data.get("permalink") or ""
    url = f"{REDDIT_BASE_URL}{permalink}" if permalink else data.get("url")

    selftext = (data.get("selftext") or "").strip()
    preview = selftext[:400]
    title = data.get("title") or "Untitled"

    return {
        "id": data.get("id"),
        "title": title,
        "url": url,
        "author": data.get("author", "unknown"),
        "subreddit": data.get("subreddit", subreddit),
        "score": data.get("score", 0),
        "comments": data.get("num_comments", 0),
        "created_at": created_at.isoformat(),
        "content": f"{title}\n\n{preview}".strip(),
        "engagement_score": data.get("score", 0) + (data.get("num_comments", 0) * 2),
    }


async def execute(
    agent_id: Optional[str] = None,
    subreddits: Optional[List[str]] = None,
    sort: str = "new",
    limit_per_subreddit: int = 25,
    min_score: int = 0,
    max_age_hours: int = 24,
    time_filter: str = "day",
) -> dict:
    """Surf Reddit and return normalized posts without persisting them."""
    del agent_id

    cleaned_subreddits = [s.strip() for s in (subreddits or []) if s and s.strip()]
    if not cleaned_subreddits:
        return {"success": False, "error": "Provide at least one subreddit."}

    clamped_limit = max(1, min(int(limit_per_subreddit), 100))
    threshold = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)

    headers = {"User-Agent": USER_AGENT}
    all_posts: List[dict] = []
    errors: List[str] = []

    try:
        async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
            for subreddit in cleaned_subreddits:
                params = {"limit": clamped_limit, "raw_json": 1}
                if sort == "top":
                    params["t"] = time_filter

                url = f"{REDDIT_BASE_URL}/r/{subreddit}/{sort}.json"
                try:
                    response = await client.get(url, params=params)
                    response.raise_for_status()
                except httpx.HTTPStatusError as exc:
                    errors.append(f"{subreddit}: HTTP {exc.response.status_code}")
                    continue
                except Exception as exc:  # pragma: no cover - network/runtime variance
                    errors.append(f"{subreddit}: {exc}")
                    continue

                children = response.json().get("data", {}).get("children", [])
                for child in children:
                    post = _normalize_post(child, subreddit)
                    created = datetime.fromisoformat(post["created_at"])
                    if post["score"] < min_score:
                        continue
                    if created < threshold:
                        continue
                    all_posts.append(post)
    except Exception as exc:
        return {"success": False, "error": f"Failed to surf Reddit: {exc}"}

    all_posts.sort(key=lambda item: item["engagement_score"], reverse=True)
    top_post = all_posts[0] if all_posts else None

    if not all_posts and errors:
        return {"success": False, "error": "; ".join(errors)}

    return {
        "success": True,
        "sort": sort,
        "subreddits": cleaned_subreddits,
        "min_score": min_score,
        "max_age_hours": max_age_hours,
        "count": len(all_posts),
        "posts": all_posts,
        "top_post": top_post,
        "errors": errors,
    }
