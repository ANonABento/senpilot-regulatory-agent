"""End-to-end email processing orchestration. See docs/AGENT.md.

``process_email`` is the seam between transport (email/) and the scraper. It is
pure with respect to I/O except for the scrape call, which is injectable
(``scrape_fn``) so the orchestration can be unit-tested without a browser.
"""

from __future__ import annotations

import logging
from typing import Callable

from regulatory_agent.agent.parse import parse_request
from regulatory_agent.email.models import InboundEmail, OutboundEmail
from regulatory_agent.email.reply import build_error_reply, build_success_reply
from regulatory_agent.models import DocumentType, ScrapeResult

logger = logging.getLogger(__name__)

ScrapeFn = Callable[[str, DocumentType], ScrapeResult]


def _scrape_error_reason(exc: Exception) -> str:
    """User-facing reason for a scrape failure, without importing the scraper."""
    name = type(exc).__name__
    if "NotFound" in name:
        return str(exc) or "I couldn't find that matter on the UARB portal."
    return "an unexpected error occurred while fetching the documents. Please try again."


def _reply_subject(inbound: InboundEmail, matter: str | None, doc_type: str | None) -> str:
    if inbound.subject.strip():
        return f"Re: {inbound.subject.strip()}"
    if matter and doc_type:
        return f"Documents for {matter} - {doc_type}"
    return "Re: your document request"


def _error_email(inbound: InboundEmail, reason: str) -> OutboundEmail:
    return OutboundEmail(
        to=inbound.sender,
        subject=_reply_subject(inbound, None, None),
        body_text=build_error_reply(reason),
        in_reply_to=inbound.message_id or None,
        references=inbound.message_id or None,
        thread_id=inbound.thread_id or None,
    )


def process_email(
    inbound: InboundEmail, *, scrape_fn: ScrapeFn | None = None
) -> OutboundEmail:
    """Parse → scrape → compose. Always returns an OutboundEmail (errors become
    error replies, never exceptions)."""
    if scrape_fn is None:
        from regulatory_agent.scraper.service import scrape_matter  # noqa: PLC0415

        scrape_fn = scrape_matter

    parsed = parse_request(inbound.body_text, user_name=inbound.sender_name)
    if not parsed.ok:
        logger.info("Unparseable request from %s: %s", inbound.sender, parsed.error_reason)
        return _error_email(inbound, parsed.error_reason or "request could not be understood")

    assert parsed.matter_number is not None and parsed.document_type is not None
    try:
        result = scrape_fn(parsed.matter_number, parsed.document_type)
    except Exception as exc:  # noqa: BLE001 — surface as an error email, don't crash the worker
        logger.exception("Scrape failed for %s", parsed.matter_number)
        return _error_email(inbound, _scrape_error_reason(exc))

    return OutboundEmail(
        to=inbound.sender,
        subject=_reply_subject(inbound, parsed.matter_number, parsed.document_type.value),
        body_text=build_success_reply(result, parsed.user_name),
        attachment_path=result.zip_path,
        in_reply_to=inbound.message_id or None,
        references=inbound.message_id or None,
        thread_id=inbound.thread_id or None,
    )
