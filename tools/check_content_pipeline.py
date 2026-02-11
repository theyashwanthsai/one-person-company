"""
Tool: check_content_pipeline
Check the status of content ideas in the pipeline.
"""

import os

SCHEMA = {
    "type": "function",
    "function": {
        "name": "check_content_pipeline",
        "description": "Check the content pipeline — see what ideas exist, their status (idea/approved/rejected/drafted/posted), and priorities.",
        "parameters": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["idea", "approved", "rejected", "drafted", "posted", "all"],
                    "description": "Filter by status. Default: all"
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results. Default 10"
                }
            },
            "required": []
        }
    }
}


def execute(agent_id: str, **kwargs):
    """Check content pipeline."""
    from supabase import create_client
    supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY'))

    status = kwargs.get('status', 'all')
    limit = kwargs.get('limit', 10)

    query = supabase.table('content_pipeline').select('*')

    if status != 'all':
        query = query.eq('status', status)

    query = query.order('created_at', desc=True).limit(limit)
    result = query.execute()

    if not result.data:
        return f"No content in pipeline (status={status})"

    lines = []
    for c in result.data:
        review = f"\n  Review: {c['review_notes']}" if c.get('review_notes') else ""
        lines.append(f"- [{c['status']}] {c['title']} (priority: {c.get('priority', '?')}){review}")

    return f"Content pipeline ({len(result.data)} items):\n" + "\n".join(lines)

