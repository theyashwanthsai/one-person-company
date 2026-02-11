"""
Tool: scan_external_source
Search external signals (Twitter, Reddit, HN content) stored in the database.

Note: This searches STORED signals. To fetch NEW content, use:
- ingest_twitter (fetch fresh tweets)
- ingest_reddit (fetch fresh Reddit posts)  
- ingest_hackernews (fetch fresh HN stories)
"""

import os

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

    query = supabase.table('external_signals').select('*')

    if source != 'all':
        query = query.eq('source', source)

    if tags:
        query = query.overlaps('tags', tags)

    query = query.order('created_at', desc=True).limit(limit)
    result = query.execute()

    if not result.data:
        return f"No external signals found for source={source}, tags={tags}"

    lines = []
    for s in result.data:
        eng = f" (engagement: {s.get('engagement_score', 'N/A')})" if s.get('engagement_score') else ""
        lines.append(f"- [{s.get('source', '?')}] {s.get('title', 'Untitled')}{eng}\n  Tags: {s.get('tags', [])}")

    return f"Found {len(result.data)} signals:\n" + "\n".join(lines)

