"""
Tool: Ingest Reddit
Fetch posts from Reddit subreddits and store as external signals.
"""

import os
import praw
from datetime import datetime
from lib.supabase_client import get_supabase

# Reddit API configuration
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")

SCHEMA = {
    "name": "ingest_reddit",
    "description": "Fetch recent posts from Reddit subreddits and store as external signals. Use this to see what topics are trending, what questions people are asking, or what content is resonating.",
    "parameters": {
        "type": "object",
        "properties": {
            "subreddit": {
                "type": "string",
                "description": "Subreddit name (without r/ prefix, e.g. 'programming', 'startups', 'machinelearning')"
            },
            "sort": {
                "type": "string",
                "enum": ["hot", "new", "top", "rising"],
                "description": "How to sort posts",
                "default": "hot"
            },
            "limit": {
                "type": "integer",
                "description": "Number of posts to fetch (max 100)",
                "default": 25
            },
            "time_filter": {
                "type": "string",
                "enum": ["hour", "day", "week", "month", "year", "all"],
                "description": "Time filter (only applies to 'top' sort)",
                "default": "day"
            },
            "category": {
                "type": "string",
                "description": "Category for these signals",
                "default": "reddit_scan"
            }
        },
        "required": ["subreddit"]
    }
}


async def execute(
    subreddit: str,
    sort: str = "hot",
    limit: int = 25,
    time_filter: str = "day",
    category: str = "reddit_scan"
) -> dict:
    """
    Fetch Reddit posts and store as external signals.
    Returns summary of what was ingested.
    """
    
    if not REDDIT_CLIENT_ID or not REDDIT_CLIENT_SECRET:
        return {
            "success": False,
            "error": "Reddit API not configured. Set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET."
        }
    
    supabase = get_supabase()
    
    try:
        # Initialize Reddit client
        reddit = praw.Reddit(
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_CLIENT_SECRET,
            user_agent="one_person_company/1.0"
        )
        
        # Get subreddit
        sub = reddit.subreddit(subreddit)
        
        # Fetch posts based on sort
        if sort == "hot":
            posts = sub.hot(limit=limit)
        elif sort == "new":
            posts = sub.new(limit=limit)
        elif sort == "rising":
            posts = sub.rising(limit=limit)
        elif sort == "top":
            posts = sub.top(time_filter=time_filter, limit=limit)
        else:
            posts = sub.hot(limit=limit)
        
        # Store each post as an external signal
        signals_created = []
        posts_list = []
        
        for post in posts:
            # Skip stickied posts
            if post.stickied:
                continue
            
            posts_list.append(post)
            
            signal_data = {
                "source": "reddit",
                "category": category,
                "content": f"{post.title}\n\n{post.selftext[:500] if post.selftext else ''}",
                "url": f"https://reddit.com{post.permalink}",
                "author": f"u/{post.author.name if post.author else 'deleted'}",
                "metrics": {
                    "upvotes": post.score,
                    "upvote_ratio": post.upvote_ratio,
                    "num_comments": post.num_comments,
                    "engagement_score": post.score * post.upvote_ratio + post.num_comments * 2
                },
                "raw_data": {
                    "post_id": post.id,
                    "subreddit": post.subreddit.display_name,
                    "created_utc": datetime.fromtimestamp(post.created_utc).isoformat(),
                    "is_self": post.is_self,
                    "link_flair_text": post.link_flair_text,
                    "domain": post.domain
                },
                "ingested_at": datetime.utcnow().isoformat()
            }
            
            result = supabase.table("external_signals").insert(signal_data).execute()
            if result.data:
                signals_created.append(result.data[0]["id"])
        
        if not signals_created:
            return {
                "success": True,
                "posts_ingested": 0,
                "message": f"No posts found in r/{subreddit}"
            }
        
        # Get top post for summary
        top_post = posts_list[0] if posts_list else None
        
        return {
            "success": True,
            "posts_ingested": len(signals_created),
            "subreddit": subreddit,
            "sort": sort,
            "category": category,
            "signal_ids": signals_created[:5],
            "top_post": {
                "title": top_post.title[:100] if top_post else "",
                "score": top_post.score if top_post else 0,
                "comments": top_post.num_comments if top_post else 0,
                "url": f"https://reddit.com{top_post.permalink}" if top_post else ""
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to ingest Reddit posts: {str(e)}"
        }

