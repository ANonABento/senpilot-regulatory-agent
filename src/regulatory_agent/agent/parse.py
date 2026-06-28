"""Extract matter number and document type from an email body.

Regex fast-path (deterministic, offline, unit-tested). The LLM fallback in
``parse_request_with_llm`` is an optional enhancement for paraphrased requests
the regex can't resolve — see docs/AGENT.md. Keep the fast-path authoritative:
if regex finds both fields, skip the model.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from regulatory_agent.models import DocumentType

MATTER_RE = re.compile(r"\bM\d{5}\b", re.I)

# Longest aliases first so "key document" wins over "document".
_DOC_TYPE_ALIASES: list[tuple[str, DocumentType]] = [
    ("key document", DocumentType.KEY_DOCUMENTS),
    ("other document", DocumentType.OTHER_DOCUMENTS),
    ("exhibit", DocumentType.EXHIBITS),
    ("transcript", DocumentType.TRANSCRIPTS),
    ("recording", DocumentType.RECORDINGS),
]


@dataclass
class ParsedRequest:
    matter_number: str | None = None
    document_type: DocumentType | None = None
    user_name: str | None = None
    error_reason: str | None = None

    @property
    def ok(self) -> bool:
        return self.matter_number is not None and self.document_type is not None


def _find_matter(body: str) -> str | None:
    match = MATTER_RE.search(body)
    return match.group(0).upper() if match else None


def _find_document_type(body: str) -> DocumentType | None:
    text = body.lower()
    for alias, doc_type in _DOC_TYPE_ALIASES:
        if alias in text:
            return doc_type
    return None


def parse_request(body: str, *, user_name: str | None = None) -> ParsedRequest:
    """Regex fast-path. Returns a ``ParsedRequest`` with ``error_reason`` set
    when a required field is missing."""
    matter = _find_matter(body)
    doc_type = _find_document_type(body)

    missing: list[str] = []
    if matter is None:
        missing.append("a matter number (e.g. M12205)")
    if doc_type is None:
        missing.append("a document type")
    error = f"I couldn't find {' and '.join(missing)} in your message." if missing else None

    return ParsedRequest(
        matter_number=matter,
        document_type=doc_type,
        user_name=user_name,
        error_reason=error,
    )
