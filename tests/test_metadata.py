"""Unit tests for metadata parsing from body text."""

from datetime import date

from regulatory_agent.scraper.metadata import (
    DATE_FINAL_SUBMISSIONS,
    DATE_RECEIVED,
    TAB_COUNT,
    _parse_date,
)

SAMPLE_BODY = """
Matter No: M12205
Status: Active
Title - Description: Halifax Regional Water Commission - Windsor Street Exchange Redevelopment Project - $69,275,000
Type / Category: Water / Capital Expenditure
Date Received: April 7, 2025
Date Final Submissions: October 23, 2025
Outcome: Pending

Exhibits - 13
Key Documents - 5
Other Documents - 21
Transcripts - 0
Recordings - 0
"""


def test_parse_date_april_format() -> None:
    assert _parse_date("April 7, 2025") == date(2025, 4, 7)


def test_parse_date_slash_format() -> None:
    assert _parse_date("04/07/2025") == date(2025, 4, 7)


def test_tab_count_regex() -> None:
    matches = {m.group(1).lower(): int(m.group(2)) for m in TAB_COUNT.finditer(SAMPLE_BODY)}
    assert matches["exhibits"] == 13
    assert matches["key documents"] == 5
    assert matches["other documents"] == 21
    assert matches["transcripts"] == 0
    assert matches["recordings"] == 0


def test_date_received_regex() -> None:
    match = DATE_RECEIVED.search(SAMPLE_BODY)
    assert match is not None
    assert _parse_date(match.group(1)) == date(2025, 4, 7)


def test_date_final_submissions_regex() -> None:
    match = DATE_FINAL_SUBMISSIONS.search(SAMPLE_BODY)
    assert match is not None
    assert _parse_date(match.group(1)) == date(2025, 10, 23)
