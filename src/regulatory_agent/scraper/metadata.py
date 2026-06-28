"""Extract matter header metadata and tab counts from detail page."""

from __future__ import annotations

import re
from datetime import date, datetime

from playwright.sync_api import Page

from regulatory_agent.models import DocumentType, MatterMetadata, TabCounts

MATTER_NO = re.compile(r"Matter No:\s*(M\d{5})", re.I)
STATUS = re.compile(r"Status:\s*(.+?)(?=\n)", re.I)
TITLE_DESCRIPTION = re.compile(
    r"Title\s*-\s*Description:\s*(.+?)(?=\n(?:Type|Date|Outcome|Matter|Status|Exhibits|Key Documents))",
    re.I | re.S,
)
TYPE_CATEGORY = re.compile(r"Type\s*/\s*Category:\s*(.+?)(?=\n)", re.I)
DATE_RECEIVED = re.compile(r"Date Received:\s*(.+?)(?=\n)", re.I)
DATE_FINAL_SUBMISSIONS = re.compile(r"Date Final Submissions:\s*(.+?)(?=\n)", re.I)
OUTCOME = re.compile(r"Outcome:\s*(.+?)(?=\n)", re.I)
TAB_COUNT = re.compile(
    r"^(Exhibits|Key Documents|Other Documents|Transcripts|Recordings)\s*-\s*(\d+)",
    re.I | re.M,
)

_DATE_FORMATS = (
    "%B %d, %Y",
    "%b %d, %Y",
    "%m/%d/%Y",
    "%Y-%m-%d",
)


def _parse_date(raw: str | None) -> date | None:
    if not raw:
        return None
    text = raw.strip().rstrip(".")
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = " ".join(value.split())
    return cleaned or None


def extract_tab_counts(page: Page) -> TabCounts:
    """Scan body text for tab labels with counts. Default missing tabs to 0."""
    body = page.locator("body").inner_text()
    counts = TabCounts()
    mapping = {
        "exhibits": DocumentType.EXHIBITS,
        "key documents": DocumentType.KEY_DOCUMENTS,
        "other documents": DocumentType.OTHER_DOCUMENTS,
        "transcripts": DocumentType.TRANSCRIPTS,
        "recordings": DocumentType.RECORDINGS,
    }
    for match in TAB_COUNT.finditer(body):
        label = match.group(1).lower()
        count = int(match.group(2))
        doc_type = mapping.get(label)
        if doc_type is DocumentType.EXHIBITS:
            counts.exhibits = count
        elif doc_type is DocumentType.KEY_DOCUMENTS:
            counts.key_documents = count
        elif doc_type is DocumentType.OTHER_DOCUMENTS:
            counts.other_documents = count
        elif doc_type is DocumentType.TRANSCRIPTS:
            counts.transcripts = count
        elif doc_type is DocumentType.RECORDINGS:
            counts.recordings = count
    return counts


def extract_matter_metadata(page: Page) -> MatterMetadata:
    """Parse visible text from matter header area using label-anchored regex."""
    body = page.locator("body").inner_text()

    matter_match = MATTER_NO.search(body)
    matter_number = matter_match.group(1) if matter_match else "UNKNOWN"

    status_match = STATUS.search(body)
    title_match = TITLE_DESCRIPTION.search(body)
    type_match = TYPE_CATEGORY.search(body)
    received_match = DATE_RECEIVED.search(body)
    final_match = DATE_FINAL_SUBMISSIONS.search(body)
    outcome_match = OUTCOME.search(body)

    return MatterMetadata(
        matter_number=matter_number,
        status=_clean(status_match.group(1) if status_match else None),
        title_description=_clean(title_match.group(1) if title_match else None),
        type_category=_clean(type_match.group(1) if type_match else None),
        date_received=_parse_date(received_match.group(1) if received_match else None),
        date_final_submissions=_parse_date(final_match.group(1) if final_match else None),
        outcome=_clean(outcome_match.group(1) if outcome_match else None),
    )
