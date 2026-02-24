"""Tool: write_obsidian_note
Create a markdown note in an Obsidian-style vault with tags and wikilinks.
"""

from __future__ import annotations

from typing import List

from lib.knowledge_base import wiki_link, write_markdown_note


SCHEMA = {
    "type": "function",
    "function": {
        "name": "write_obsidian_note",
        "description": "Create a markdown knowledge note with tags and wikilinks in the local knowledge base filesystem.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Note title."},
                "content": {"type": "string", "description": "Main markdown note content."},
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional tags."
                },
                "links": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional note titles to link as wikilinks."
                },
                "folder": {
                    "type": "string",
                    "description": "Optional vault subfolder. Default: notes"
                }
            },
            "required": ["title", "content"]
        },
    },
}


def execute(agent_id: str, **kwargs):
    title = (kwargs.get("title") or "").strip()
    content = (kwargs.get("content") or "").strip()
    tags: List[str] = kwargs.get("tags") or []
    links: List[str] = kwargs.get("links") or []
    folder = (kwargs.get("folder") or "notes").strip()

    if not title:
        return "Error: title is required."
    if not content:
        return "Error: content is required."

    linked = [wiki_link(item.strip()) for item in links if (item or "").strip()]
    links_section = ""
    if linked:
        links_section = "## Related\n" + "\n".join(f"- {item}" for item in linked)

    body = (
        f"## Author\n"
        f"- Agent: {agent_id}\n\n"
        f"{content}\n\n"
        f"{links_section}\n"
    ).strip()

    result = write_markdown_note(
        title=title,
        body=body,
        folder=folder,
        tags=["note", *tags],
        note_type="obsidian_note",
        filename_hint=title,
    )
    return f"Created Obsidian-style note at {result['path']}"

