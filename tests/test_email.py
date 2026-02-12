"""
Email tests:
1) SMTP sanity check
2) `email_ceo` tool check
3) Inbox round-trip check (wait for an incoming email, then reply)

Usage examples:
  python3 tests/test_email.py --smtp
  python3 tests/test_email.py --email-ceo
  python3 tests/test_email.py --roundtrip --agent strategist_lead
"""

import argparse
import os
import sys
import time
from pathlib import Path

# Allow imports from project root.
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv

from lib.email_client import EmailClient
from tools.email_ceo import execute as email_ceo_execute

load_dotenv()


def test_smtp():
    client = EmailClient()
    success = client._send_email(
        client.ceo_email,
        "SMTP test",
        "If you're reading this, SMTP works.",
    )
    print("SMTP:", "ok" if success else "failed")


def test_email_ceo_tool():
    result = email_ceo_execute(
        agent_id="strategist_lead",
        subject="Tool test message",
        message="Testing email_ceo tool path.",
        urgency="low",
    )
    print(result)


def test_roundtrip(agent_id: str, timeout_seconds: int, poll_seconds: int):
    """
    Wait for an incoming message directed to the agent, then send a reply.
    This validates the new inbox-check + response workflow.
    """
    client = EmailClient()
    deadline = time.time() + timeout_seconds

    print(
        f"Waiting for inbound mail for agent '{agent_id}' "
        f"(timeout={timeout_seconds}s, poll={poll_seconds}s)..."
    )

    matched = None
    while time.time() < deadline:
        messages = client.get_pending_messages_for_agent(agent_id=agent_id, limit=1)
        if messages:
            matched = messages[0]
            break
        time.sleep(poll_seconds)

    if not matched:
        print("No inbound message matched the agent within timeout.")
        return

    sender = matched.get("from") or client.ceo_email
    subject = matched.get("subject", "(no subject)")
    body = matched.get("body", "")
    short_body = body[:400] + ("..." if len(body) > 400 else "")

    reply_subject = f"Re: {subject}"
    reply_body = (
        f"Agent: {agent_id}\n\n"
        "Received your message and queued it for handling.\n\n"
        "Original snippet:\n"
        f"{short_body}\n"
    )

    success = client._send_email(sender, reply_subject, reply_body)
    if success:
        print(f"Round-trip reply sent to {sender}")
    else:
        print(f"Failed to send round-trip reply to {sender}")


def main():
    parser = argparse.ArgumentParser(description="Email test suite")
    parser.add_argument("--smtp", action="store_true", help="Run SMTP sanity test")
    parser.add_argument("--email-ceo", action="store_true", help="Run email_ceo tool test")
    parser.add_argument("--roundtrip", action="store_true", help="Run inbox round-trip test")
    parser.add_argument("--agent", default="strategist_lead", help="Agent id for round-trip match")
    parser.add_argument("--timeout", type=int, default=180, help="Round-trip wait timeout seconds")
    parser.add_argument("--poll", type=int, default=10, help="Round-trip poll interval seconds")

    args = parser.parse_args()

    # If no flags are passed, run all.
    run_all = not any([args.smtp, args.email_ceo, args.roundtrip])

    if args.smtp or run_all:
        test_smtp()

    if args.email_ceo or run_all:
        test_email_ceo_tool()

    if args.roundtrip or run_all:
        test_roundtrip(args.agent, args.timeout, args.poll)


if __name__ == "__main__":
    main()
