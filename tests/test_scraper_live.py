"""Live UARB integration test — see docs/TESTING.md."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from regulatory_agent.models import DocumentType
from regulatory_agent.scraper.service import scrape_matter


@pytest.mark.live
def test_scrape_m12205_other_documents() -> None:
    result = scrape_matter("M12205", DocumentType.OTHER_DOCUMENTS, max_downloads=10, headless=True)

    assert result.matter_number == "M12205"
    assert result.requested_document_type == DocumentType.OTHER_DOCUMENTS

    # Live counts drift as filings are added (Other Documents was 21 in the spec, 42
    # as of 2026-06); assert the invariants, not the exact live numbers.
    assert result.downloaded_count == 10
    assert result.available_in_tab >= 10
    assert result.available_in_tab == result.tab_counts.other_documents
    assert result.tab_counts.exhibits > 0
    assert result.tab_counts.key_documents > 0
    assert result.tab_counts.transcripts == 0
    assert result.tab_counts.recordings == 0

    assert result.metadata.title_description is not None
    assert "Halifax Regional Water Commission" in result.metadata.title_description
    assert result.metadata.status is not None
    assert result.metadata.type_category is not None
    assert "Water" in result.metadata.type_category
    assert result.metadata.date_received is not None
    assert result.metadata.date_final_submissions is not None

    assert result.zip_path is not None
    assert result.zip_path.exists()

    with zipfile.ZipFile(result.zip_path, "r") as archive:
        names = archive.namelist()
        assert len(names) == 10
        for name in names:
            assert Path(name).suffix.lower() in {".pdf", ""}
