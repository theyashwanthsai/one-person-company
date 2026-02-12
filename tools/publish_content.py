"""
Tool: Publish Content
Post content to Twitter (with optional thread support).
"""

import os
import httpx
from datetime import datetime
from typing import List, Optional
from lib.supabase_client import get_supabase

# Twitter API v2 configuration
BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")
ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
ACCESS_SECRET = os.getenv("TWITTER_ACCESS_SECRET")
API_KEY = os.getenv("TWITTER_API_KEY")
API_SECRET = os.getenv("TWITTER_API_SECRET")

SCHEMA = {
    "type": "function",
    "function": {
        "name": "publish_content",
        "description": "Post content to Twitter. Can post single tweets or threads. Use this when you have content ready to publish. The tweet will be posted immediately.",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Tweet text (max 280 characters). For threads, separate tweets with '\\n---\\n'"
                },
                "draft_id": {
                    "type": "string",
                    "description": "Optional: Content pipeline ID if this is publishing a draft",
                    "default": None
                }
            },
            "required": ["text"]
        }
    }
}


async def execute(text: str, draft_id: Optional[str] = None) -> dict:
    """
    Post tweet(s) to Twitter.
    Returns published tweet info.
    """
    
    if not all([BEARER_TOKEN, ACCESS_TOKEN, ACCESS_SECRET, API_KEY, API_SECRET]):
        return {
            "success": False,
            "error": "Twitter API not fully configured. Set TWITTER_* environment variables."
        }
    
    supabase = get_supabase()
    
    try:
        # Check if this is a thread (contains separator)
        tweets = text.split("\n---\n") if "\n---\n" in text else [text]
        
        # Validate tweet lengths
        for i, tweet in enumerate(tweets):
            if len(tweet) > 280:
                return {
                    "success": False,
                    "error": f"Tweet {i+1} exceeds 280 characters ({len(tweet)} chars)"
                }
        
        # Post tweets
        posted_tweets = []
        reply_to_id = None
        
        # OAuth 1.0a for posting (Twitter API v2 with OAuth 1.0a)
        from requests_oauthlib import OAuth1Session
        
        oauth = OAuth1Session(
            API_KEY,
            client_secret=API_SECRET,
            resource_owner_key=ACCESS_TOKEN,
            resource_owner_secret=ACCESS_SECRET
        )
        
        url = "https://api.twitter.com/2/tweets"
        
        for tweet_text in tweets:
            payload = {"text": tweet_text.strip()}
            
            # If this is part of a thread, reply to previous tweet
            if reply_to_id:
                payload["reply"] = {"in_reply_to_tweet_id": reply_to_id}
            
            response = oauth.post(url, json=payload)
            
            if response.status_code != 201:
                return {
                    "success": False,
                    "error": f"Failed to post tweet: {response.status_code} - {response.text}"
                }
            
            tweet_data = response.json()["data"]
            tweet_id = tweet_data["id"]
            posted_tweets.append({
                "id": tweet_id,
                "text": tweet_text[:100],
                "url": f"https://twitter.com/i/web/status/{tweet_id}"
            })
            
            # Next tweet will reply to this one
            reply_to_id = tweet_id
        
        # Update content pipeline if draft_id provided
        if draft_id:
            try:
                supabase.table("content_pipeline").update({
                    "stage": "published",
                    "published_at": datetime.utcnow().isoformat(),
                    "published_url": posted_tweets[0]["url"],
                    "metadata": {
                        "tweet_ids": [t["id"] for t in posted_tweets],
                        "is_thread": len(posted_tweets) > 1
                    }
                }).eq("id", draft_id).execute()
            except:
                pass  # Don't fail if pipeline update fails
        
        return {
            "success": True,
            "tweets_posted": len(posted_tweets),
            "is_thread": len(posted_tweets) > 1,
            "tweets": posted_tweets,
            "primary_url": posted_tweets[0]["url"]
        }
        
    except ImportError:
        return {
            "success": False,
            "error": "requests-oauthlib not installed. Run: pip install requests-oauthlib"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to publish content: {str(e)}"
        }
