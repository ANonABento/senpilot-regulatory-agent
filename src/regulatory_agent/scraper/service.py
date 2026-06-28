"""Scraper orchestration — single entry point for Phase 1."""

from __future__ import annotations

from regulatory_agent.models import DocumentType, ScrapeResult


def scrape_matter(matter_number: str, document_type: DocumentType, *, max_downloads: int | None = None) -> ScrapeResult:
    """Fetch documents from UARB and return structured result with ZIP path."""
    raise NotImplementedError("Phase 1 — implement per docs/SCRAPER.md")
