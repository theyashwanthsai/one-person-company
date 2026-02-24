"""
Tool: scan_external_source
Search external signals (Twitter, Reddit, HN content) stored in the database.

Note: This searches STORED signals. To fetch NEW content, use:
- surf_twitter (fetch fresh Twitter posts by keyword)
- surf_reddit (fetch fresh Reddit posts by subreddit)
- surf_hn (fetch fresh Hacker News stories)
"""

import os
from dotenv import load_dotenv

load_dotenv()


SCHEMA = {
    "type": "function",
    "function": {
        "name": "scan_external_source",
        "description": "Search external signals — content from Twitter, Reddit, HN stored in the database. Use this to find trends, similar content, or market data.",
        "parameters": {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "enum": ["twitter", "reddit", "hackernews", "all"],
                    "description": "Which source to search. Use 'all' for everything."
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tags to filter by (e.g. ['ai', 'agents', 'coding'])"
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results to return. Default 10"
                },
                "only_unseen": {
                    "type": "boolean",
                    "description": "If true, return only signals seen once (newly discovered posts).",
                    "default": False,
                },
                "max_seen_count": {
                    "type": "integer",
                    "description": "Optional cap on seen_count (e.g. 1 for fresh-only, 2 for lightly repeated)."
                }
            },
            "required": ["source"]
        }
    }
}


def execute(agent_id: str, **kwargs):
    """Search external signals."""
    from supabase import create_client
    supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY'))

    source = kwargs.get('source', 'all')
    tags = kwargs.get('tags')
    limit = kwargs.get('limit', 10)
    only_unseen = kwargs.get('only_unseen', False)
    max_seen_count = kwargs.get('max_seen_count')

    query = supabase.table('external_signals').select('*')

    if source != 'all':
        query = query.eq('source', source)

    if tags:
        query = query.overlaps('tags', tags)
    if only_unseen:
        query = query.eq('seen_count', 1)
    if isinstance(max_seen_count, int):
        query = query.lte('seen_count', max_seen_count)

    query = query.order('ingested_at', desc=True).limit(limit)
    result = query.execute()

    if not result.data:
        return f"No external signals found for source={source}, tags={tags}"

    lines = []
    for s in result.data:
        eng = f" (engagement: {s.get('engagement_score', 'N/A')})" if s.get('engagement_score') else ""
        seen_count = s.get('seen_count', 1)
        first_seen = s.get('first_seen_at') or s.get('ingested_at')
        last_seen = s.get('last_seen_at') or s.get('ingested_at')
        lines.append(
            f"- [{s.get('source', '?')}] {s.get('title', 'Untitled')}{eng}\n"
            f"  Seen: {seen_count}x (first: {first_seen}, last: {last_seen})\n"
            f"  Tags: {s.get('tags', [])}"
        )

    return f"Found {len(result.data)} signals:\n" + "\n".join(lines)
