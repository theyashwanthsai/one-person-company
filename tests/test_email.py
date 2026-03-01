"""
Manual tests for email parsing and email_ops tool.
Run: python3 tests/test_email.py
"""

import os
import tempfile
from email.message import EmailMessage
from unittest import mock

from utils import print_header, setup_test_environment

setup_test_environment()

from lib import email_client
from lib.email_client import EmailClient, EmailMessageSummary
from tools import email_ops


class FakeIMAP:
    def __init__(self, raw_message: bytes):
        self.raw_message = raw_message
        self.logged_in = False
        self.selected = False
        self.searched = False

    def login(self, user, password):
        self.logged_in = True
        return "OK", [b"Logged in"]

    def select(self, folder, readonly=True):
        self.selected = True
        return "OK", [b"Selected"]

    def uid(self, command, *args):
        if command == "search":
            self.searched = True
            return "OK", [b"101"]
        if command == "fetch":
            meta = b"101 (FLAGS (\\Seen)) BODY[]"
            return "OK", [(meta, self.raw_message)]
        return "NO", []

    def logout(self):
        return "OK", [b"Logged out"]


class FakeSMTP:
    def __init__(self):
        self.logged_in = False
        self.sent = []

    def login(self, user, password):
        self.logged_in = True

    def send_message(self, message, from_addr=None, to_addrs=None):
        self.sent.append((message, from_addr, to_addrs))

    def quit(self):
        return

    def starttls(self, context=None):
        return


class FakeDiscordClient:
    def __init__(self, *args, **kwargs):
        return

    def send_message(self, channel_id, content, agent_id=None, reply_to_message_id=None):
        return True


def _build_test_message() -> bytes:
    msg = EmailMessage()
    msg["From"] = "Alice Example <alice@example.com>"
    msg["To"] = "you@example.com"
    msg["Subject"] = "Test email"
    msg["Date"] = "Mon, 01 Jan 2024 10:00:00 -0000"
    msg["Message-ID"] = "<msg-1@example.com>"
    msg["In-Reply-To"] = "<msg-0@example.com>"
    msg["References"] = "<msg-0@example.com> <msg-1@example.com>"

    msg.set_content("Hello plain text body")
    msg.add_alternative("<html><body><p>Hello <b>HTML</b> body</p></body></html>", subtype="html")

    msg.add_attachment(b"file-bytes", maintype="application", subtype="octet-stream", filename="file.txt")
    return msg.as_bytes()


def test_email_fetch_parsing():
    print_header("TEST 1: Email parsing")

    raw_message = _build_test_message()

    with tempfile.NamedTemporaryFile(delete=False) as state_file:
        state_path = state_file.name
        state_file.write(b"{}")

    os.environ["EMAIL_IMAP_HOST"] = "imap.example.com"
    os.environ["EMAIL_IMAP_USER"] = "you@example.com"
    os.environ["EMAIL_IMAP_PASSWORD"] = "password"
    os.environ["EMAIL_IMAP_SSL"] = "1"

    with mock.patch.object(email_client, "STATE_PATH", state_path):
        with mock.patch("imaplib.IMAP4_SSL", return_value=FakeIMAP(raw_message)):
            client = EmailClient()
            messages = client.fetch_new_messages(limit=5, unread_only=True)

    assert len(messages) == 1, "Expected one message"
    msg = messages[0]
    assert msg.sender == "Alice Example", "Sender parsing failed"
    assert msg.subject == "Test email", "Subject parsing failed"
    assert "Hello" in msg.snippet, "Snippet should include body"
    assert msg.flags == ["\\Seen"], "Flags parsing failed"
    assert msg.message_id == "<msg-1@example.com>", "Message-ID parsing failed"
    assert msg.in_reply_to == "<msg-0@example.com>", "In-Reply-To parsing failed"
    assert msg.references == ["<msg-0@example.com>", "<msg-1@example.com>"], "References parsing failed"
    assert msg.attachments and msg.attachments[0]["filename"] == "file.txt", "Attachment parsing failed"

    print("✅ Parsing OK")


def test_email_send():
    print_header("TEST 2: Email send")

    os.environ["EMAIL_SMTP_HOST"] = "smtp.example.com"
    os.environ["EMAIL_SMTP_USER"] = "you@example.com"
    os.environ["EMAIL_SMTP_PASSWORD"] = "password"
    os.environ["EMAIL_SMTP_SSL"] = "1"
    os.environ["EMAIL_FROM"] = "you@example.com"

    fake_smtp = FakeSMTP()

    with mock.patch("smtplib.SMTP_SSL", return_value=fake_smtp):
        client = EmailClient()
        client.send_email(
            to_addresses=["bob@example.com"],
            subject="Hello",
            body="Test body",
        )

    assert fake_smtp.logged_in, "SMTP login was not called"
    assert fake_smtp.sent, "Email was not sent"

    print("✅ Send OK")


def test_email_ops_check_post():
    print_header("TEST 3: email_ops check")

    os.environ["DISCORD_MAILS_CHANNEL_ID"] = "123456"

    summary = EmailMessageSummary(
        uid="101",
        sender="Alice",
        subject="Hi",
        date="Mon, 01 Jan 2024 10:00:00 -0000",
        snippet="Hello",
        flags=["\\Seen"],
        message_id="<msg-1@example.com>",
        in_reply_to="",
        references=[],
        attachments=[],
    )

    with mock.patch("tools.email_ops.EmailClient") as mock_client_cls:
        mock_client = mock_client_cls.return_value
        mock_client.fetch_new_messages.return_value = [summary]
        with mock.patch("tools.email_ops._post_to_mails_channel", return_value=None):
            result = email_ops.execute("watari", action="check", limit=5)

    assert "Inbox update posted" in result, "Expected Discord post confirmation"
    print("✅ email_ops check OK")


def test_email_ops_send():
    print_header("TEST 4: email_ops send")

    with mock.patch("tools.email_ops.EmailClient") as mock_client_cls:
        mock_client = mock_client_cls.return_value
        result = email_ops.execute(
            "watari",
            action="send",
            to=["bob@example.com"],
            subject="Hello",
            body="Test body",
        )

    assert "Email sent" in result, "Expected send confirmation"
    assert mock_client.send_email.called, "send_email was not invoked"
    print("✅ email_ops send OK")


if __name__ == "__main__":
    test_email_fetch_parsing()
    test_email_send()
    test_email_ops_check_post()
    test_email_ops_send()
    print("\n✅ All email tests passed")
