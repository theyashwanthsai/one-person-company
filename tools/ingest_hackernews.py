"""
Tool: Ingest Hacker News
Fetch top/new stories from Hacker News and store as external signals.
"""

import httpx
from datetime import datetime
from lib.supabase_client import get_supabase

SCHEMA = {
    "name": "ingest_hackernews",
    "description": "Fetch stories from Hacker News (top, new, best, or ask) and store as external signals. Use this to see what tech stories are trending, what discussions are happening, or what questions developers are asking.",
    "parameters": {
        "type": "object",
        "properties": {
            "story_type": {
                "type": "string",
                "enum": ["top", "new", "best", "ask", "show"],
                "description": "Type of stories to fetch (top: most upvoted, new: newest, best: best stories, ask: Ask HN, show: Show HN)",
                "default": "top"
            },
            "limit": {
                "type": "integer",
                "description": "Number of stories to fetch (max 30)",
                "default": 20
            },
            "category": {
                "type": "string",
                "description": "Category for these signals",
                "default": "hackernews_scan"
            }
        },
        "required": []
    }
}


async def execute(
    story_type: str = "top",
    limit: int = 20,
    category: str = "hackernews_scan"
) -> dict:
    """
    Fetch HN stories and store as external signals.
    Returns summary of what was ingested.
    """
    
    supabase = get_supabase()
    
    try:
        # HN API endpoints
        base_url = "https://hacker-news.firebaseio.com/v0"
        
        # Get story IDs
        story_endpoint = f"{base_url}/{story_type}stories.json"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(story_endpoint)
            response.raise_for_status()
            story_ids = response.json()[:limit]
            
            if not story_ids:
                return {
                    "success": True,
                    "stories_ingested": 0,
                    "message": f"No {story_type} stories found"
                }
            
            # Fetch each story
            stories = []
            for story_id in story_ids:
                story_response = await client.get(f"{base_url}/item/{story_id}.json")
                if story_response.status_code == 200:
                    story_data = story_response.json()
                    if story_data and story_data.get("type") == "story":
                        stories.append(story_data)
        
        if not stories:
            return {
                "success": True,
                "stories_ingested": 0,
                "message": "No valid stories found"
            }
        
        # Store each story as an external signal
        signals_created = []
        
        for story in stories:
            # Determine if it's a text post or link
            is_text = "text" in story and story["text"]
            
            signal_data = {
                "source": "hackernews",
                "category": category,
                "content": f"{story.get('title', '')}\n\n{story.get('text', '')[:500] if is_text else ''}",
                "url": story.get("url") or f"https://news.ycombinator.com/item?id={story['id']}",
                "author": story.get("by", "unknown"),
                "metrics": {
                    "score": story.get("score", 0),
                    "comments": story.get("descendants", 0),
                    "engagement_score": story.get("score", 0) + story.get("descendants", 0) * 2
                },
                "raw_data": {
                    "story_id": story["id"],
                    "story_type": story_type,
                    "time": datetime.fromtimestamp(story.get("time", 0)).isoformat(),
                    "is_text": is_text,
                    "hn_url": f"https://news.ycombinator.com/item?id={story['id']}"
                },
                "ingested_at": datetime.utcnow().isoformat()
            }
            
            result = supabase.table("external_signals").insert(signal_data).execute()
            if result.data:
                signals_created.append(result.data[0]["id"])
        
        # Get top story for summary
        top_story = stories[0]
        
        return {
            "success": True,
            "stories_ingested": len(signals_created),
            "story_type": story_type,
            "category": category,
            "signal_ids": signals_created[:5],
            "top_story": {
                "title": top_story.get("title", "")[:100],
                "score": top_story.get("score", 0),
                "comments": top_story.get("descendants", 0),
                "url": f"https://news.ycombinator.com/item?id={top_story['id']}"
            }
        }
        
    except httpx.HTTPStatusError as e:
        return {
            "success": False,
            "error": f"HN API error: {e.response.status_code}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to ingest HN stories: {str(e)}"
        }

