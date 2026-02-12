"""
Tool: Fetch Metrics
Fetch engagement metrics for published content from Twitter.
"""

import os
import httpx
from datetime import datetime
from typing import Optional
from lib.supabase_client import get_supabase

# Twitter API v2 configuration
BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")

SCHEMA = {
    "type": "function",
    "function": {
        "name": "fetch_metrics",
        "description": "Fetch engagement metrics (likes, retweets, replies, impressions) for published tweets. Use this to analyze performance of your content and identify what's working.",
        "parameters": {
            "type": "object",
            "properties": {
                "tweet_id": {
                    "type": "string",
                    "description": "Twitter tweet ID to fetch metrics for"
                },
                "update_pipeline": {
                    "type": "boolean",
                    "description": "Whether to update the content_pipeline table with metrics",
                    "default": True
                }
            },
            "required": ["tweet_id"]
        }
    }
}


async def execute(tweet_id: str, update_pipeline: bool = True) -> dict:
    """
    Fetch metrics for a tweet and optionally update content pipeline.
    Returns engagement metrics.
    """
    
    if not BEARER_TOKEN:
        return {
            "success": False,
            "error": "Twitter API not configured. Set TWITTER_BEARER_TOKEN."
        }
    
    supabase = get_supabase()
    
    try:
        # Twitter API v2 tweet lookup
        url = f"https://api.twitter.com/2/tweets/{tweet_id}"
        
        params = {
            "tweet.fields": "created_at,public_metrics,author_id",
            "expansions": "author_id"
        }
        
        headers = {
            "Authorization": f"Bearer {BEARER_TOKEN}"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()
        
        tweet = data.get("data")
        if not tweet:
            return {
                "success": False,
                "error": f"Tweet {tweet_id} not found"
            }
        
        metrics = tweet.get("public_metrics", {})
        
        # Calculate engagement score
        likes = metrics.get("like_count", 0)
        retweets = metrics.get("retweet_count", 0)
        replies = metrics.get("reply_count", 0)
        impressions = metrics.get("impression_count", 0)
        
        # Weighted engagement score
        engagement_score = (likes * 1) + (retweets * 3) + (replies * 5)
        engagement_rate = (engagement_score / impressions * 100) if impressions > 0 else 0
        
        metrics_data = {
            "tweet_id": tweet_id,
            "likes": likes,
            "retweets": retweets,
            "replies": replies,
            "impressions": impressions,
            "engagement_score": engagement_score,
            "engagement_rate": round(engagement_rate, 2),
            "fetched_at": datetime.utcnow().isoformat()
        }
        
        # Update content pipeline if requested
        if update_pipeline:
            try:
                # Find content in pipeline by tweet_id in metadata
                result = supabase.table("content_pipeline")\
                    .select("*")\
                    .eq("stage", "published")\
                    .execute()
                
                for item in result.data:
                    metadata = item.get("metadata", {})
                    tweet_ids = metadata.get("tweet_ids", [])
                    
                    if tweet_id in tweet_ids:
                        # Update with metrics
                        supabase.table("content_pipeline").update({
                            "metrics": metrics_data,
                            "metadata": {
                                **metadata,
                                "last_metrics_update": datetime.utcnow().isoformat()
                            }
                        }).eq("id", item["id"]).execute()
                        break
            except:
                pass  # Don't fail if pipeline update fails
        
        # Analyze performance
        performance_level = "low"
        if engagement_rate > 5:
            performance_level = "excellent"
        elif engagement_rate > 3:
            performance_level = "good"
        elif engagement_rate > 1:
            performance_level = "average"
        
        return {
            "success": True,
            "tweet_id": tweet_id,
            "metrics": metrics_data,
            "performance": performance_level,
            "url": f"https://twitter.com/i/web/status/{tweet_id}",
            "analysis": {
                "total_engagements": likes + retweets + replies,
                "viral_potential": "high" if retweets > likes else "moderate",
                "discussion_quality": "high" if replies > likes else "low"
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
            "error": f"Failed to fetch metrics: {str(e)}"
        }
