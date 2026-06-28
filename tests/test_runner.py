"""Unit tests for process_email orchestration (scrape injected, no browser)."""

from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from regulatory_agent.agent.runner import process_email
from regulatory_agent.email.models import InboundEmail
from regulatory_agent.models import (
    DocumentType,
    MatterMetadata,
    ScrapeResult,
    TabCounts,
)


def _inbound(body: str, subject: str = "Document request") -> InboundEmail:
    return InboundEmail(
        message_id="msg-1",
        thread_id="thread-1",
        sender="Sam Jones <sam@example.com>",
        subject=subject,
        body_text=body,
        received_at=datetime(2026, 6, 28, tzinfo=timezone.utc),
    )


def _fake_result() -> ScrapeResult:
    return ScrapeResult(
        matter_number="M12205",
        requested_document_type=DocumentType.OTHER_DOCUMENTS,
        metadata=MatterMetadata(
            matter_number="M12205",
            title_description="Halifax Regional Water Commission",
            type_category="Water / Capital Expenditure",
            date_received=date(2025, 4, 7),
            date_final_submissions=date(2025, 10, 23),
        ),
        tab_counts=TabCounts(exhibits=13, key_documents=5, other_documents=21),
        downloaded_count=10,
        available_in_tab=21,
        zip_path=Path("output/M12205_other_documents.zip"),
    )


def test_success_builds_reply_with_attachment_and_threading() -> None:
    captured: list[tuple[str, DocumentType]] = []

    def fake_scrape(matter: str, doc_type: DocumentType) -> ScrapeResult:
        captured.append((matter, doc_type))
        return _fake_result()

    out = process_email(
        _inbound("Please send Other Documents for M12205"), scrape_fn=fake_scrape
    )

    assert captured == [("M12205", DocumentType.OTHER_DOCUMENTS)]
    assert out.to == "Sam Jones <sam@example.com>"
    assert out.attachment_path == Path("output/M12205_other_documents.zip")
    assert out.in_reply_to == "msg-1"
    assert out.thread_id == "thread-1"
    assert out.subject == "Re: Document request"
    assert "Hi Sam Jones," in out.body_text
    assert "10 out of the 21 Other Documents" in out.body_text


def test_bad_request_returns_error_without_scraping() -> None:
    def must_not_call(matter: str, doc_type: DocumentType) -> ScrapeResult:
        raise AssertionError("scrape should not run for an unparseable request")

    out = process_email(_inbound("hello there"), scrape_fn=must_not_call)
    assert out.attachment_path is None
    assert "matter number" in out.body_text


def test_scrape_not_found_becomes_error_reply() -> None:
    class MatterNotFoundError(Exception):
        pass

    def fake_scrape(matter: str, doc_type: DocumentType) -> ScrapeResult:
        raise MatterNotFoundError("Matter M12205 not found")

    out = process_email(
        _inbound("Other Documents for M12205"), scrape_fn=fake_scrape
    )
    assert out.attachment_path is None
    assert "not found" in out.body_text


def test_unexpected_scrape_error_is_generic() -> None:
    def boom(matter: str, doc_type: DocumentType) -> ScrapeResult:
        raise RuntimeError("playwright exploded")

    out = process_email(_inbound("Other Documents for M12205"), scrape_fn=boom)
    assert "unexpected error" in out.body_text
    assert "playwright" not in out.body_text  # don't leak internals


def test_empty_subject_falls_back_to_generated_subject() -> None:
    out = process_email(
        _inbound("Other Documents for M12205", subject=""),
        scrape_fn=lambda m, d: _fake_result(),
    )
    assert out.subject == "Documents for M12205 - Other Documents"
