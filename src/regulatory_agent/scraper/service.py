"""Scraper orchestration — single entry point for Phase 1."""

from __future__ import annotations

import logging

from regulatory_agent.config import settings
from regulatory_agent.models import DocumentType, ScrapeResult
from regulatory_agent.scraper.browser import BrowserSession, capture_ws_frames
from regulatory_agent.scraper.download import download_documents, select_document_tab
from regulatory_agent.scraper.metadata import extract_matter_metadata, extract_tab_counts
from regulatory_agent.scraper.navigate import go_to_matter
from regulatory_agent.scraper.zipper import create_zip

logger = logging.getLogger(__name__)


def scrape_matter(
    matter_number: str,
    document_type: DocumentType,
    *,
    max_downloads: int | None = None,
    headless: bool | None = None,
) -> ScrapeResult:
    """Fetch documents from UARB and return structured result with ZIP path."""
    cap = max_downloads if max_downloads is not None else settings.max_downloads
    settings.download_dir.mkdir(parents=True, exist_ok=True)

    with BrowserSession(headless=headless) as page:
        # Register the websocket listener before navigation opens the Vaadin push channel.
        ws_frames = capture_ws_frames(page)
        go_to_matter(page, matter_number)
        metadata = extract_matter_metadata(page)
        tab_counts = extract_tab_counts(page)
        select_document_tab(page, document_type)
        available = tab_counts.for_type(document_type)
        files = download_documents(page, ws_frames, max_count=cap)
        zip_path = create_zip(files, matter_number, document_type.value)

    return ScrapeResult(
        matter_number=matter_number,
        requested_document_type=document_type,
        metadata=metadata,
        tab_counts=tab_counts,
        downloaded_count=len(files),
        available_in_tab=available,
        zip_path=zip_path,
        downloaded_files=files,
    )
