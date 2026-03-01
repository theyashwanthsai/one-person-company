# Email Integration

This folder stores local state for email polling and provides setup notes.

## Required Environment Variables

IMAP (inbound):
- EMAIL_IMAP_HOST
- EMAIL_IMAP_PORT
- EMAIL_IMAP_USER
- EMAIL_IMAP_PASSWORD
- EMAIL_IMAP_SSL ("1" or "0")
- EMAIL_IMAP_FOLDER (default: INBOX)

SMTP (outbound):
- EMAIL_SMTP_HOST
- EMAIL_SMTP_PORT
- EMAIL_SMTP_USER
- EMAIL_SMTP_PASSWORD
- EMAIL_SMTP_SSL ("1" or "0")
- EMAIL_FROM (default: EMAIL_SMTP_USER)
- EMAIL_REPLY_TO (optional)

Discord updates:
- DISCORD_MAILS_CHANNEL_ID (channel id for #mails)

## State Files

- state.json holds the last seen IMAP UID per inbox user so we only send new updates.
