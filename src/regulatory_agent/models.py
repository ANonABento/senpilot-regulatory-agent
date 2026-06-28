"""Domain models for scraper, email, and agent layers."""

from __future__ import annotations

from datetime import date
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field


class DocumentType(str, Enum):
    EXHIBITS = "Exhibits"
    KEY_DOCUMENTS = "Key Documents"
    OTHER_DOCUMENTS = "Other Documents"
    TRANSCRIPTS = "Transcripts"
    RECORDINGS = "Recordings"

    @classmethod
    def from_user_text(cls, text: str) -> DocumentType | None:
        normalized = text.strip().lower()
        for member in cls:
            if member.value.lower() == normalized:
                return member
        aliases = {
            "exhibit": cls.EXHIBITS,
            "key document": cls.KEY_DOCUMENTS,
            "other document": cls.OTHER_DOCUMENTS,
            "transcript": cls.TRANSCRIPTS,
            "recording": cls.RECORDINGS,
        }
        for key, value in aliases.items():
            if key in normalized:
                return value
        return None


class TabCounts(BaseModel):
    exhibits: int = 0
    key_documents: int = 0
    other_documents: int = 0
    transcripts: int = 0
    recordings: int = 0

    def for_type(self, document_type: DocumentType) -> int:
        return {
            DocumentType.EXHIBITS: self.exhibits,
            DocumentType.KEY_DOCUMENTS: self.key_documents,
            DocumentType.OTHER_DOCUMENTS: self.other_documents,
            DocumentType.TRANSCRIPTS: self.transcripts,
            DocumentType.RECORDINGS: self.recordings,
        }[document_type]


class MatterMetadata(BaseModel):
    matter_number: str
    status: str | None = None
    title_description: str | None = None
    type_category: str | None = None
    date_received: date | None = None
    date_final_submissions: date | None = None
    outcome: str | None = None


class ScrapeRequest(BaseModel):
    matter_number: str = Field(pattern=r"^M\d{5}$")
    document_type: DocumentType


class ScrapeResult(BaseModel):
    matter_number: str
    requested_document_type: DocumentType
    metadata: MatterMetadata
    tab_counts: TabCounts
    downloaded_count: int
    available_in_tab: int
    zip_path: Path | None
    downloaded_files: list[Path] = Field(default_factory=list)


class AgentError(Exception):
    """Expected failure surfaced to the user via error email."""
