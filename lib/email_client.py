"""
Email client for IMAP (inbound) and SMTP (outbound).
"""

import json
import os
import re
import ssl
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import imaplib
import smtplib
from email import message_from_bytes
from email.header import decode_header, make_header
from email.message import EmailMessage
from email.utils import parseaddr
from bs4 import BeautifulSoup


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_PATH = os.path.join(PROJECT_ROOT, "email", "state.json")


@dataclass
class EmailMessageSummary:
    uid: str
    sender: str
    subject: str
    date: str
    snippet: str
    flags: List[str]
    message_id: str
    in_reply_to: str
    references: List[str]
    attachments: List[dict]


class EmailClient:
    def __init__(self):
        self.imap_host = os.getenv("EMAIL_IMAP_HOST")
        self.imap_port = int(os.getenv("EMAIL_IMAP_PORT", "993"))
        self.imap_user = os.getenv("EMAIL_IMAP_USER")
        self.imap_password = os.getenv("EMAIL_IMAP_PASSWORD")
        self.imap_ssl = os.getenv("EMAIL_IMAP_SSL", "1").strip().lower() in {"1", "true", "yes", "on"}
        self.imap_folder = os.getenv("EMAIL_IMAP_FOLDER", "INBOX")

        self.smtp_host = os.getenv("EMAIL_SMTP_HOST")
        self.smtp_port = int(os.getenv("EMAIL_SMTP_PORT", "465"))
        self.smtp_user = os.getenv("EMAIL_SMTP_USER")
        self.smtp_password = os.getenv("EMAIL_SMTP_PASSWORD")
        self.smtp_ssl = os.getenv("EMAIL_SMTP_SSL", "1").strip().lower() in {"1", "true", "yes", "on"}
        self.smtp_from = os.getenv("EMAIL_FROM") or self.smtp_user
        self.smtp_reply_to = os.getenv("EMAIL_REPLY_TO")

    def _imap_ready(self) -> bool:
        return all([self.imap_host, self.imap_user, self.imap_password])

    def _smtp_ready(self) -> bool:
        return all([self.smtp_host, self.smtp_user, self.smtp_password, self.smtp_from])

    def _load_state(self) -> Dict[str, Dict[str, str]]:
        if not os.path.exists(STATE_PATH):
            return {}
        try:
            with open(STATE_PATH, "r", encoding="utf-8") as fh:
                return json.load(fh) or {}
        except Exception:
            return {}

    def _save_state(self, state: Dict[str, Dict[str, str]]):
        os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
        with open(STATE_PATH, "w", encoding="utf-8") as fh:
            json.dump(state, fh, indent=2, sort_keys=True)

    def _get_last_uid(self) -> Optional[int]:
        state = self._load_state()
        user_key = self.imap_user or "default"
        raw = state.get("imap_last_uid", {}).get(user_key)
        try:
            return int(raw) if raw is not None else None
        except (TypeError, ValueError):
            return None

    def _set_last_uid(self, uid: int):
        state = self._load_state()
        user_key = self.imap_user or "default"
        state.setdefault("imap_last_uid", {})[user_key] = str(uid)
        self._save_state(state)

    def _decode_header(self, value: str) -> str:
        if not value:
            return ""
        try:
            return str(make_header(decode_header(value)))
        except Exception:
            return value

    def _html_to_text(self, html: str) -> str:
        if not html:
            return ""
        try:
            soup = BeautifulSoup(html, "html.parser")
            return soup.get_text(" ", strip=True)
        except Exception:
            return re.sub(r"<[^>]+>", " ", html)

    def _extract_bodies(self, msg) -> Tuple[str, str]:
        text_body = ""
        html_body = ""
        try:
            if msg.is_multipart():
                for part in msg.walk():
                    ctype = part.get_content_type()
                    disp = (part.get("Content-Disposition") or "").lower()
                    if "attachment" in disp:
                        continue
                    if ctype == "text/plain" and not text_body:
                        payload = part.get_payload(decode=True) or b""
                        charset = part.get_content_charset() or "utf-8"
                        text_body = payload.decode(charset, errors="replace").strip().replace("\r", "")
                    if ctype == "text/html" and not html_body:
                        payload = part.get_payload(decode=True) or b""
                        charset = part.get_content_charset() or "utf-8"
                        html_body = payload.decode(charset, errors="replace").strip().replace("\r", "")
            else:
                payload = msg.get_payload(decode=True) or b""
                charset = msg.get_content_charset() or "utf-8"
                text_body = payload.decode(charset, errors="replace").strip().replace("\r", "")
        except Exception:
            return "", ""
        return text_body, html_body

    def _extract_attachments(self, msg) -> List[dict]:
        attachments: List[dict] = []
        if not msg:
            return attachments
        for part in msg.walk():
            disp = (part.get("Content-Disposition") or "").lower()
            filename = part.get_filename()
            if not filename and "attachment" not in disp:
                continue
            decoded_name = self._decode_header(filename or "attachment")
            payload = part.get_payload(decode=True) or b""
            attachments.append(
                {
                    "filename": decoded_name,
                    "content_type": part.get_content_type(),
                    "size_bytes": len(payload),
                }
            )
        return attachments

    def _parse_flags(self, meta: bytes) -> List[str]:
        if not meta:
            return []
        try:
            text = meta.decode("utf-8", errors="ignore")
        except Exception:
            text = str(meta)
        match = re.search(r"FLAGS\s*\((.*?)\)", text, flags=re.IGNORECASE | re.DOTALL)
        if not match:
            return []
        raw = match.group(1).strip()
        if not raw:
            return []
        return [item.strip() for item in raw.split() if item.strip()]

    def fetch_new_messages(self, limit: int = 5, unread_only: bool = True) -> List[EmailMessageSummary]:
        if not self._imap_ready():
            raise ValueError("IMAP not configured")

        last_uid = self._get_last_uid()
        mailbox = None
        try:
            if self.imap_ssl:
                mailbox = imaplib.IMAP4_SSL(self.imap_host, self.imap_port)
            else:
                mailbox = imaplib.IMAP4(self.imap_host, self.imap_port)

            mailbox.login(self.imap_user, self.imap_password)
            mailbox.select(self.imap_folder, readonly=True)

            criteria = []
            if unread_only:
                criteria.append("UNSEEN")
            if last_uid is not None:
                criteria.extend(["UID", f"{last_uid + 1}:*"])

            search_criteria = criteria or ["ALL"]
            status, data = mailbox.uid("search", None, *search_criteria)
            if status != "OK":
                return []

            uid_list = data[0].split() if data and data[0] else []
            if not uid_list:
                return []

            # Only keep the newest N UIDs
            selected_uids = uid_list[-limit:]
            summaries: List[EmailMessageSummary] = []
            max_uid = last_uid or 0

            for uid in selected_uids:
                uid_str = uid.decode("utf-8")
                max_uid = max(max_uid, int(uid_str))

                status, msg_data = mailbox.uid("fetch", uid, "(FLAGS BODY.PEEK[])")
                if status != "OK" or not msg_data:
                    continue

                raw_message = None
                flags: List[str] = []
                for item in msg_data:
                    if not isinstance(item, tuple):
                        continue
                    meta = item[0] or b""
                    payload = item[1]
                    flags = flags or self._parse_flags(meta)
                    if payload:
                        raw_message = payload

                if raw_message is None:
                    continue

                msg = message_from_bytes(raw_message)
                sender_name, sender_email = parseaddr(msg.get("From", ""))
                sender = sender_name or sender_email or "(unknown)"
                subject = self._decode_header(msg.get("Subject", "(no subject)"))
                date = msg.get("Date", "")
                message_id = msg.get("Message-ID", "") or ""
                in_reply_to = msg.get("In-Reply-To", "") or ""
                references_raw = msg.get("References", "") or ""
                references = [r for r in references_raw.split() if r]

                text_body, html_body = self._extract_bodies(msg)
                html_text = self._html_to_text(html_body)
                snippet_source = text_body or html_text
                snippet = snippet_source[:500] if snippet_source else ""
                attachments = self._extract_attachments(msg)

                summaries.append(
                    EmailMessageSummary(
                        uid=uid_str,
                        sender=sender,
                        subject=subject,
                        date=date,
                        snippet=snippet,
                        flags=flags,
                        message_id=message_id,
                        in_reply_to=in_reply_to,
                        references=references,
                        attachments=attachments,
                    )
                )

            if summaries and max_uid:
                self._set_last_uid(max_uid)

            return summaries
        finally:
            try:
                if mailbox is not None:
                    mailbox.logout()
            except Exception:
                pass

    def send_email(
        self,
        to_addresses: List[str],
        subject: str,
        body: str,
        cc_addresses: Optional[List[str]] = None,
        bcc_addresses: Optional[List[str]] = None,
    ):
        if not self._smtp_ready():
            raise ValueError("SMTP not configured")

        message = EmailMessage()
        message["From"] = self.smtp_from
        message["To"] = ", ".join(to_addresses)
        if cc_addresses:
            message["Cc"] = ", ".join(cc_addresses)
        if self.smtp_reply_to:
            message["Reply-To"] = self.smtp_reply_to
        message["Subject"] = subject
        message.set_content(body)

        all_recipients = list(to_addresses)
        if cc_addresses:
            all_recipients += list(cc_addresses)
        if bcc_addresses:
            all_recipients += list(bcc_addresses)

        if self.smtp_ssl:
            server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=20)
        else:
            server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=20)
            server.starttls(context=ssl.create_default_context())

        try:
            server.login(self.smtp_user, self.smtp_password)
            server.send_message(message, from_addr=self.smtp_from, to_addrs=all_recipients)
        finally:
            try:
                server.quit()
            except Exception:
                pass
