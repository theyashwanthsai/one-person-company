"""Tool: ingest_external_link_knowledge
Fetch a web page and store extracted full text content in markdown knowledge base.
"""

from __future__ import annotations

from typing import List

import requests
from bs4 import BeautifulSoup

from lib.knowledge_base import write_markdown_note


SCHEMA = {
    "type": "function",
    "function": {
        "name": "ingest_external_link_knowledge",
        "description": "Ingest a URL into the markdown knowledge base with extracted full text content.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Web URL to ingest."},
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional tags for the knowledge note."
                },
                "folder": {
                    "type": "string",
                    "description": "Optional vault subfolder. Default: sources/web"
                }
            },
            "required": ["url"]
        },
    },
}


def _extract_text_chunks(html: str) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()

    chunks = []
    main = soup.find("main") or soup.find("article") or soup.body or soup
    for node in main.find_all(["h1", "h2", "h3", "p", "li", "blockquote"]):
        text = node.get_text(" ", strip=True)
        if text:
            chunks.append(text)
    return chunks


def execute(agent_id: str, **kwargs):
    url = (kwargs.get("url") or "").strip()
    tags = kwargs.get("tags") or []
    folder = (kwargs.get("folder") or "sources/web").strip()
    if not url:
        return "Error: url is required."

    try:
        response = requests.get(
            url,
            timeout=20,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0 Safari/537.36"
                )
            },
        )
    except Exception as exc:
        return f"Error fetching URL: {exc}"

    if response.status_code >= 400:
        return f"Error fetching URL: HTTP {response.status_code}"

    html = response.text or ""
    chunks = _extract_text_chunks(html)
    page_text = "\n\n".join(chunks).strip()
    if not page_text:
        return "Error: Could not extract readable text from the page."

    page_text = page_text[:200000]
    soup = BeautifulSoup(html, "html.parser")
    title = (soup.title.get_text(strip=True) if soup.title else "") or url

    body = (
        f"## Source\n"
        f"- URL: {url}\n"
        f"- Captured By: {agent_id}\n\n"
        f"## Extracted Content\n\n"
        f"{page_text}\n"
    )

    result = write_markdown_note(
        title=title,
        body=body,
        folder=folder,
        tags=["web", "knowledge", *tags],
        source_url=url,
        note_type="source_web",
        filename_hint=title,
    )
    return (
        f"Stored external link knowledge note.\n"
        f"- title: {title}\n"
        f"- path: {result['path']}"
    )

