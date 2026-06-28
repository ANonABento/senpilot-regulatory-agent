"""Unit tests for reply templates (no network).

The happy path is covered by one comprehensive test that asserts the reply
reproduces the spec's gold example; the rest cover distinct branches.
"""

from datetime import date
from pathlib import Path

from regulatory_agent.email.reply import build_error_reply, build_success_reply
from regulatory_agent.models import (
    DocumentType,
    MatterMetadata,
    ScrapeResult,
    TabCounts,
)


def _result(downloaded: int = 10, available: int = 21) -> ScrapeResult:
    return ScrapeResult(
        matter_number="M12205",
        requested_document_type=DocumentType.OTHER_DOCUMENTS,
        metadata=MatterMetadata(
            matter_number="M12205",
            title_description=(
                "Halifax Regional Water Commission - Windsor Street Exchange "
                "Redevelopment Project - $69,275,000"
            ),
            type_category="Water / Capital Expenditure Approvals",  # as the live scraper emits it
            date_received=date(2025, 4, 7),
            date_final_submissions=date(2025, 10, 23),
        ),
        tab_counts=TabCounts(
            exhibits=13, key_documents=5, other_documents=21, transcripts=0, recordings=0
        ),
        downloaded_count=downloaded,
        available_in_tab=available,
        zip_path=Path("output/M12205_other_documents.zip"),
    )


def test_gold_reply_matches_spec_example() -> None:
    """One test for the whole happy path: phrasing, counts, dates, download line."""
    body = build_success_reply(_result(), user_name="Sam")
    assert body.startswith("Hi Sam,")
    assert "It relates to Water / Capital Expenditure Approvals" in body
    assert "on April 7, 2025 and a final filing on October 23, 2025" in body
    assert (
        "13 Exhibits, 5 Key Documents, 21 Other Documents, and no Transcripts or Recordings"
        in body
    )
    assert "I downloaded 10 out of the 21 Other Documents and am attaching them as a ZIP" in body


def test_greeting_with_and_without_name() -> None:
    assert build_success_reply(_result(), user_name="Sam").startswith("Hi Sam,")
    assert build_success_reply(_result()).startswith("Hi,")


def test_empty_tab_has_no_attachment_language() -> None:
    result = _result(downloaded=0, available=0)
    result.tab_counts = TabCounts(exhibits=13, key_documents=5)
    body = build_success_reply(result)
    assert "nothing to attach" in body
    assert "attaching them as a ZIP" not in body


def test_counts_oxford_and_when_all_present() -> None:
    result = _result()
    result.tab_counts = TabCounts(
        exhibits=1, key_documents=2, other_documents=3, transcripts=4, recordings=5
    )
    body = build_success_reply(result)
    assert "1 Exhibits, 2 Key Documents, 3 Other Documents, 4 Transcripts, and 5 Recordings" in body


def test_error_reply_lists_valid_types() -> None:
    body = build_error_reply("no matter number found")
    assert "no matter number found" in body
    assert "Exhibits, Key Documents, Other Documents, Transcripts, Recordings" in body
    assert "M12205" in body
