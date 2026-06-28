from regulatory_agent.models import DocumentType


def test_document_type_from_user_text_exact() -> None:
    assert DocumentType.from_user_text("Other Documents") == DocumentType.OTHER_DOCUMENTS


def test_document_type_from_user_text_alias() -> None:
    assert DocumentType.from_user_text("other document please") == DocumentType.OTHER_DOCUMENTS


def test_document_type_unknown() -> None:
    assert DocumentType.from_user_text("briefs") is None
