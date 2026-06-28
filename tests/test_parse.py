from pathlib import Path

from regulatory_agent.agent.parse import parse_request
from regulatory_agent.models import DocumentType

SAMPLE_EMAIL = Path(__file__).parent.joinpath("fixtures/sample_request_email.txt").read_text(
    encoding="utf-8"
)


def test_parse_sample_email() -> None:
    parsed = parse_request(SAMPLE_EMAIL)
    assert parsed.ok
    assert parsed.matter_number == "M12205"
    assert parsed.document_type == DocumentType.OTHER_DOCUMENTS
    assert parsed.error_reason is None


def test_parse_normalizes_lowercase_matter() -> None:
    parsed = parse_request("get me exhibits for m12383 please")
    assert parsed.matter_number == "M12383"
    assert parsed.document_type == DocumentType.EXHIBITS


def test_key_documents_alias_not_shadowed_by_document() -> None:
    parsed = parse_request("pull the key documents for M12205")
    assert parsed.document_type == DocumentType.KEY_DOCUMENTS


def test_missing_matter_number_sets_error() -> None:
    parsed = parse_request("can you send me the transcripts?")
    assert not parsed.ok
    assert parsed.matter_number is None
    assert parsed.document_type == DocumentType.TRANSCRIPTS
    assert "matter number" in parsed.error_reason


def test_missing_document_type_sets_error() -> None:
    parsed = parse_request("anything on M12205?")
    assert not parsed.ok
    assert parsed.document_type is None
    assert parsed.error_reason is not None


def test_empty_body_reports_both_missing() -> None:
    parsed = parse_request("Hello")
    assert not parsed.ok
    assert "matter number" in parsed.error_reason
    assert "document type" in parsed.error_reason
