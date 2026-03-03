"""Tool: Surf Hacker News
Fetch Hacker News stories using the Algolia search_by_date endpoint and return structured posts for agents to inspect."""

import logging
from datetime import datetime, timedelta
from typing import List

import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SCHEMA = {
    "type": "function",
    "function": {
        "name": "surf_hn",
        "description": "Surf Hacker News via Algolia time windows and return structured stories for agents to review before saving.",
        "parameters": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "Calendar date (YYYY-MM-DD) to fetch stories for. Defaults to today.",
                },
                "hours_window": {
                    "type": "integer",
                    "description": "How many hours back to scan (overrides date if provided).",
                    "minimum": 1,
                },
                "min_points": {
                    "type": "integer",
                    "description": "Minimum score required for a story to be returned.",
                    "default": 0,
                },
                "max_posts": {
                    "type": "integer",
                    "description": "Max number of HN posts to return (default 100).",
                    "default": 100,
                    "minimum": 1,
                }
            }
        }
    }
}


def _build_time_window(date_str: str, hours_window: int | None):
    if hours_window is not None:
        now = datetime.utcnow()
        start = int((now - timedelta(hours=hours_window)).timestamp())
        end = int(now.timestamp())
        label = f"last {hours_window}h"
    else:
        try:
            target = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            logger.error("Invalid date format: %s", date_str)
            raise
        start = int(target.replace(hour=0, minute=0, second=0).timestamp())
        end = int((target + timedelta(days=1)).replace(hour=0, minute=0, second=0).timestamp())
        label = target.strftime("%Y-%m-%d")
    return start, end, label


def _normalize_post(post: dict) -> dict:
    title = post.get("title") or "Untitled"
    story_text = post.get("story_text") or post.get("comment_text") or ""
    created_at = datetime.fromtimestamp(post.get("created_at_i", 0)).isoformat()
    url = post.get("url") or f"https://news.ycombinator.com/item?id={post.get('objectID')}"

    return {
        "title": title,
        "url": url,
        "author": post.get("author", "unknown"),
        "score": post.get("points", 0),
        "comments": post.get("num_comments", 0) or 0,
        "created_at": created_at,
        "content": f"{title}\n\n{story_text[:400]}",
        "engagement_score": post.get("points", 0) + (post.get("num_comments", 0) or 0) * 2,
    }


async def execute(
    date: str | None = None,
    hours_window: int | None = None,
    min_points: int = 0,
    max_posts: int = 100,
) -> dict:
    """Surf Hacker News and return the stories without persisting them."""

    if hours_window is not None:
        window_start, window_end, range_label = _build_time_window("1970-01-01", hours_window)
    else:
        today = date or datetime.utcnow().strftime("%Y-%m-%d")
        window_start, window_end, range_label = _build_time_window(today, None)

    params = {
        "tags": "story",
        "numericFilters": f"created_at_i>={window_start},created_at_i<{window_end},points>={min_points}",
        "hitsPerPage": 100,
        "page": 0,
    }

    posts: List[dict] = []

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            while True:
                logger.info("Fetching Hacker News page %s", params["page"])
                response = await client.get("https://hn.algolia.com/api/v1/search_by_date", params=params)
                response.raise_for_status()
                payload = response.json()
                hits = payload.get("hits", [])

                for hit in hits:
                    if len(posts) >= max_posts:
                        break
                    posts.append(hit)

                current_page = payload.get("page", 0)
                total_pages = payload.get("nbPages", 0)

                if len(posts) >= max_posts or current_page + 1 >= total_pages:
                    break

                params["page"] = current_page + 1
    except httpx.HTTPStatusError as exc:
        return {"success": False, "error": f"HN API error: {exc.response.status_code}"}
    except Exception as exc:
        return {"success": False, "error": f"Failed to surf Hacker News: {exc}"}

    normalized = [_normalize_post(post) for post in posts]
    top_post = max(normalized, key=lambda item: item["score"]) if normalized else None

    return {
        "success": True,
        "range": range_label,
        "min_points": min_points,
        "posts": normalized,
        "top_post": top_post,
        "count": len(normalized)
    }
