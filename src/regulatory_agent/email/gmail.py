"""Gmail provider over IMAP (poll) + SMTP (send), authenticated with an App Password.

App Password auth needs no OAuth consent flow and the credential doesn't expire,
so it's robust for an unattended worker. The pure builder/parser helpers
(``build_message``, ``parse_inbound``) are split out so they unit-test without a
network connection or credentials.

Threading is done purely with the ``In-Reply-To``/``References`` headers (there is
no Gmail-API ``threadId`` over SMTP). Polling uses ``BODY.PEEK`` so messages stay
unread until ``mark_processed`` explicitly flags them ``\\Seen`` — a crash mid-scrape
leaves the email to be retried next cycle.
"""

from __future__ import annotations

import imaplib
import logging
import smtplib
from datetime import datetime, timezone
from email import message_from_bytes, policy
from email.message import EmailMessage
from email.utils import parsedate_to_datetime

from regulatory_agent.config import settings
from regulatory_agent.email.models import InboundEmail, OutboundEmail

logger = logging.getLogger(__name__)


def _body_text(msg: EmailMessage) -> str:
    """First text/plain part (falling back to text/html), as text."""
    if msg.is_multipart():
        for want in ("text/plain", "text/html"):
            for part in msg.walk():
                if part.get_content_type() == want and part.get_content_disposition() != "attachment":
                    return (part.get_content() or "").strip()
        return ""
    return (msg.get_content() or "").strip()


def parse_inbound(raw: bytes, *, self_address: str | None = None) -> InboundEmail | None:
    """Parse a raw RFC822 message into an InboundEmail. Returns None for self-sent
    mail (so the worker never replies to itself)."""
    msg = message_from_bytes(raw, policy=policy.default)
    sender = str(msg["From"] or "")
    if self_address and self_address.lower() in sender.lower():
        return None
    try:
        received = parsedate_to_datetime(msg["Date"]) if msg["Date"] else None
    except (TypeError, ValueError):
        received = None
    return InboundEmail(
        message_id=str(msg["Message-ID"] or "").strip(),
        thread_id="",
        sender=sender,
        subject=str(msg["Subject"] or ""),
        body_text=_body_text(msg),
        received_at=received or datetime.now(tz=timezone.utc),
    )


def build_message(message: OutboundEmail, from_addr: str) -> EmailMessage:
    """Build a MIME message (with optional ZIP attachment) for SMTP send."""
    mime = EmailMessage()
    mime["To"] = message.to
    mime["From"] = from_addr
    mime["Subject"] = message.subject
    if message.in_reply_to:
        mime["In-Reply-To"] = message.in_reply_to
        mime["References"] = message.references or message.in_reply_to
    mime.set_content(message.body_text)
    if message.attachment_path is not None:
        data = message.attachment_path.read_bytes()
        mime.add_attachment(
            data, maintype="application", subtype="zip", filename=message.attachment_path.name
        )
    return mime


class GmailProvider:
    """Concrete :class:`EmailProvider` over Gmail IMAP + SMTP with an App Password."""

    def __init__(self) -> None:
        self._address = settings.gmail_address
        self._password = settings.gmail_app_password

    def _require_config(self) -> None:
        if not self._address or not self._password:
            raise RuntimeError(
                "Gmail not configured; set GMAIL_ADDRESS and GMAIL_APP_PASSWORD in .env"
            )

    def _imap(self) -> imaplib.IMAP4_SSL:
        imap = imaplib.IMAP4_SSL(settings.imap_host, settings.imap_port)
        imap.login(self._address, self._password)
        return imap

    def poll_unread(self) -> list[InboundEmail]:
        self._require_config()
        emails: list[InboundEmail] = []
        imap = self._imap()
        try:
            imap.select(settings.mailbox)
            typ, data = imap.uid("search", None, "UNSEEN")
            if typ != "OK" or not data or not data[0]:
                return []
            for uid in data[0].split():
                typ, fetched = imap.uid("fetch", uid, "(BODY.PEEK[])")
                if typ != "OK" or not fetched or not isinstance(fetched[0], tuple):
                    continue
                try:
                    inbound = parse_inbound(fetched[0][1], self_address=self._address)
                except Exception:  # noqa: BLE001 — a malformed message must not kill the poll
                    logger.exception("Failed to parse message uid=%s", uid)
                    continue
                if inbound is not None:
                    emails.append(inbound)
        finally:
            _quiet_logout(imap)
        return emails

    def send(self, message: OutboundEmail) -> None:
        self._require_config()
        mime = build_message(message, self._address or "")
        with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port) as smtp:
            smtp.login(self._address, self._password)
            smtp.send_message(mime)
        logger.info("Sent reply to %s", message.to)

    def mark_processed(self, message_id: str) -> None:
        self._require_config()
        if not message_id:
            return
        imap = self._imap()
        try:
            imap.select(settings.mailbox)
            typ, data = imap.uid("search", None, "HEADER", "Message-ID", message_id)
            if typ == "OK" and data and data[0]:
                for uid in data[0].split():
                    imap.uid("store", uid, "+FLAGS", "(\\Seen)")
        finally:
            _quiet_logout(imap)


def _quiet_logout(imap: imaplib.IMAP4_SSL) -> None:
    try:
        imap.logout()
    except Exception:  # noqa: BLE001
        pass
