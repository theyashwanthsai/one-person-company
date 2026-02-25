"""Tool: ingest_external_link_knowledge
Fetch a web page and store extracted full text content in markdown knowledge base.
"""

from __future__ import annotations

import re
from typing import List
from urllib.parse import urlparse

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


def _extract_tweet_id(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if "twitter.com" not in host and "x.com" not in host:
        return ""
    match = re.search(r"/status/(\d+)", parsed.path)
    return match.group(1) if match else ""


def _is_tweet_url(url: str) -> bool:
    return bool(_extract_tweet_id(url))


def _fetch_tweet_payload(tweet_id: str) -> dict:
    response = requests.get(
        "https://cdn.syndication.twimg.com/tweet-result",
        params={"id": tweet_id, "lang": "en"},
        timeout=20,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0 Safari/537.36"
            )
        },
    )
    if response.status_code >= 400:
        raise RuntimeError(f"Tweet API HTTP {response.status_code}")
    data = response.json() if response.text else {}
    if not isinstance(data, dict):
        raise RuntimeError("Unexpected tweet API response format")
    return data


def _build_tweet_note_fields(url: str, payload: dict) -> tuple[str, str]:
    user = payload.get("user") if isinstance(payload.get("user"), dict) else {}
    text = (payload.get("text") or "").strip()
    if not text:
        raise RuntimeError("Tweet text not present in API payload")

    screen_name = (user.get("screen_name") or "").strip()
    display_name = (user.get("name") or "").strip()
    author_line = (
        f"{display_name} (@{screen_name})"
        if display_name and screen_name
        else (display_name or f"@{screen_name}" if screen_name else "unknown")
    )
    title = f"Tweet by @{screen_name}" if screen_name else "Tweet"
    created_at = (payload.get("created_at") or "").strip()
    likes = payload.get("favorite_count")
    replies = payload.get("conversation_count")
    retweets = payload.get("retweet_count")

    body = (
        f"## Source\n"
        f"- URL: {url}\n"
        f"- Tweet ID: {_extract_tweet_id(url)}\n"
        f"- Author: {author_line}\n"
        f"- Captured At: {created_at or 'unknown'}\n"
        f"- Likes: {likes if likes is not None else 'unknown'}\n"
        f"- Replies: {replies if replies is not None else 'unknown'}\n"
        f"- Retweets: {retweets if retweets is not None else 'unknown'}\n\n"
        f"## Tweet Content\n\n"
        f"{text}\n"
    )
    return title, body


def execute(agent_id: str, **kwargs):
    url = (kwargs.get("url") or "").strip()
    tags = kwargs.get("tags") or []
    folder = (kwargs.get("folder") or "sources/web").strip()
    if not url:
        return "Error: url is required."

    if _is_tweet_url(url):
        try:
            payload = _fetch_tweet_payload(_extract_tweet_id(url))
            title, body = _build_tweet_note_fields(url, payload)
        except Exception as exc:
            return f"Error fetching tweet content: {exc}"

        result = write_markdown_note(
            title=title,
            body=body,
            folder=folder,
            tags=["web", "knowledge", "tweet", "twitter", *tags],
            source_url=url,
            note_type="source_tweet",
            filename_hint=title,
        )
        return (
            f"Stored external link knowledge note.\n"
            f"- title: {title}\n"
            f"- path: {result['path']}"
        )

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
