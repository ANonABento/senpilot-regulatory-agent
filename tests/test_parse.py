import re
from pathlib import Path

SAMPLE_EMAIL = Path(__file__).parent.joinpath("fixtures/sample_request_email.txt").read_text(encoding="utf-8")


def test_sample_email_contains_m12205() -> None:
    assert re.search(r"\bM12205\b", SAMPLE_EMAIL)


def test_sample_email_mentions_other_documents() -> None:
    assert "Other Documents" in SAMPLE_EMAIL
