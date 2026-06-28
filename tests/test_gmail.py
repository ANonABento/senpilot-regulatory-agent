"""Unit tests for Gmail pure helpers (no network, no credentials)."""

from email.message import EmailMessage
from pathlib import Path

from regulatory_agent.email.gmail import build_message, parse_inbound
from regulatory_agent.email.models import OutboundEmail


def _raw_email(
    *,
    from_addr: str = "Sam Jones <sam@example.com>",
    subject: str = "Docs for M12205",
    body: str = "Can you send Other Documents from M12205?",
    msgid: str = "<orig-123@mail>",
    html: str | None = None,
) -> bytes:
    msg = EmailMessage()
    msg["From"] = from_addr
    msg["To"] = "agent@example.com"
    msg["Subject"] = subject
    msg["Message-ID"] = msgid
    msg["Date"] = "Sun, 28 Jun 2026 12:00:00 +0000"
    msg.set_content(body)
    if html:
        msg.add_alternative(html, subtype="html")
    return msg.as_bytes()


def test_parse_inbound_plain() -> None:
    inbound = parse_inbound(_raw_email(), self_address="agent@example.com")
    assert inbound is not None
    assert "sam@example.com" in inbound.sender
    assert inbound.sender_name == "Sam Jones"
    assert inbound.subject == "Docs for M12205"
    assert inbound.message_id == "<orig-123@mail>"
    assert "Other Documents from M12205" in inbound.body_text
    assert inbound.received_at.year == 2026


def test_parse_inbound_prefers_plain_over_html() -> None:
    raw = _raw_email(body="the real body", html="<p>ignore me</p>")
    inbound = parse_inbound(raw, self_address="agent@example.com")
    assert inbound is not None
    assert inbound.body_text == "the real body"


def test_parse_inbound_skips_self() -> None:
    raw = _raw_email(from_addr="agent@example.com")
    assert parse_inbound(raw, self_address="agent@example.com") is None


def test_build_message_headers_and_body() -> None:
    msg = build_message(
        OutboundEmail(
            to="user@example.com",
            subject="Re: docs",
            body_text="here you go",
            in_reply_to="<orig-123@mail>",
        ),
        "agent@example.com",
    )
    assert msg["To"] == "user@example.com"
    assert msg["From"] == "agent@example.com"
    assert msg["Subject"] == "Re: docs"
    assert msg["In-Reply-To"] == "<orig-123@mail>"
    assert msg["References"] == "<orig-123@mail>"
    assert "here you go" in msg.get_body(preferencelist=("plain",)).get_content()


def test_build_message_with_attachment(tmp_path: Path) -> None:
    zip_path = tmp_path / "M12205_other_documents.zip"
    zip_path.write_bytes(b"PK\x03\x04 fake zip bytes")
    msg = build_message(
        OutboundEmail(
            to="user@example.com",
            subject="Documents",
            body_text="attached",
            attachment_path=zip_path,
        ),
        "agent@example.com",
    )
    attachments = list(msg.iter_attachments())
    assert len(attachments) == 1
    assert attachments[0].get_filename() == "M12205_other_documents.zip"
    assert attachments[0].get_content_type() == "application/zip"
