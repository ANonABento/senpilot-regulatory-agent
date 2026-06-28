"""Extract matter header metadata and tab counts from the detail page.

FileMaker WebDirect renders the header as absolutely-positioned widgets, so the flat
``inner_text`` has every label clustered together and every value clustered separately —
there are no ``Label: value`` strings to regex. Instead we read the leaf text nodes with
their on-screen coordinates and map each value to the label sitting above it in the same
column. Reliable scalar fields (matter number, dates, dollar title) also have regex
fallbacks against the body text.
"""

from __future__ import annotations

import logging
import re
from datetime import date, datetime

from playwright.sync_api import Page

from regulatory_agent.models import MatterMetadata, TabCounts

logger = logging.getLogger(__name__)

MATTER_NO = re.compile(r"\b(M\d{5})\b")
DATE_VALUE = re.compile(r"\b(\d{1,2}/\d{1,2}/\d{4})\b")
# Retained for the body-text fallback and unit tests (synthetic "Label: value" layout).
DATE_RECEIVED = re.compile(r"Date Received:\s*(.+?)(?=\n)", re.I)
DATE_FINAL_SUBMISSIONS = re.compile(r"Date (?:Final Submissions|Decision):\s*(.+?)(?=\n)", re.I)
TAB_COUNT = re.compile(
    r"^(Exhibits|Key Documents|Other Documents|Transcripts|Recordings)\s*-\s*(\d+)",
    re.I | re.M,
)

_DATE_FORMATS = ("%m/%d/%Y", "%B %d, %Y", "%b %d, %Y", "%Y-%m-%d")
_VALUE_BAND = (165, 330)  # y-range where header values sit (below labels ~136, above tabs ~335)
_COLUMN_TOLERANCE = 60  # px: max x-gap for two values to share a column


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
    """Scan body text for tab labels with counts (e.g. ``Other Documents - 42``)."""
    body = page.locator("body").inner_text()
    counts = TabCounts()
    setters = {
        "exhibits": "exhibits",
        "key documents": "key_documents",
        "other documents": "other_documents",
        "transcripts": "transcripts",
        "recordings": "recordings",
    }
    for match in TAB_COUNT.finditer(body):
        attr = setters.get(match.group(1).lower())
        if attr:
            setattr(counts, attr, int(match.group(2)))
    return counts


def _leaf_text_nodes(page: Page) -> list[dict]:
    """Every leaf element carrying visible text, with its screen coordinates."""
    return page.evaluate(
        """() => {
            const out = [];
            document.querySelectorAll('*').forEach(el => {
                if (el.children.length) return;
                const t = (el.innerText || '').trim();
                if (!t) return;
                const r = el.getBoundingClientRect();
                if (r.width === 0 || r.height === 0) return;
                out.push({t, x: Math.round(r.x), y: Math.round(r.y)});
            });
            return out;
        }"""
    )


def _is_title(text: str) -> bool:
    return "$" in text or (" - " in text and len(text) > 40)


def _value_columns(nodes: list[dict]) -> list[list[str]]:
    """Cluster value-band leaf nodes into columns (by x), each ordered top to bottom.

    The header labels ("Matter No", "Type", ...) are two-line containers with child
    elements, so they are not leaf nodes — we identify columns by their values' content
    instead of by anchoring to a label.
    """
    band = [n for n in nodes if _VALUE_BAND[0] <= n["y"] <= _VALUE_BAND[1]]
    columns: list[dict] = []
    for n in sorted(band, key=lambda n: n["x"]):
        col = next((c for c in columns if abs(c["x"] - n["x"]) <= _COLUMN_TOLERANCE), None)
        if col is None:
            col = {"x": n["x"], "nodes": []}
            columns.append(col)
        col["nodes"].append(n)
        col["x"] = sum(m["x"] for m in col["nodes"]) / len(col["nodes"])
    result: list[list[str]] = []
    for col in columns:
        ordered = sorted(col["nodes"], key=lambda n: n["y"])
        texts: list[str] = []
        for n in ordered:
            texts.extend(part.strip() for part in n["t"].split("\n") if part.strip())
        result.append(texts)
    return result


def extract_matter_metadata(page: Page) -> MatterMetadata:
    """Map header values to fields by column geometry, with body-text fallbacks."""
    body = page.locator("body").inner_text()
    nodes = _leaf_text_nodes(page)

    matter_match = MATTER_NO.search(body)
    matter_number = matter_match.group(1) if matter_match else "UNKNOWN"

    status = type_value = category = title = None
    try:
        for texts in _value_columns(nodes):
            if not texts:
                continue
            top = texts[0]
            if MATTER_NO.fullmatch(top):  # Matter No (top) / Status (bottom) column
                status = texts[1] if len(texts) > 1 else status
            elif DATE_VALUE.fullmatch(top):  # date columns: handled via body fallback
                continue
            elif _is_title(top):  # Title - Description column
                title = top
            else:  # Type (top) / Category (bottom) column
                type_value = top
                category = texts[1] if len(texts) > 1 else None
    except Exception as exc:  # geometry is best-effort; fall back to body parsing
        logger.debug("Geometry metadata extraction failed: %s", exc)

    # Fallbacks from body text.
    if not title:
        title = next((ln.strip() for ln in body.splitlines() if _is_title(ln)), None)
    dates = DATE_VALUE.findall(body)
    received = dates[0] if dates else None
    final = dates[1] if len(dates) > 1 else None

    type_category = " / ".join(p for p in (type_value, category) if p) or None

    return MatterMetadata(
        matter_number=matter_number,
        status=_clean(status),
        title_description=_clean(title),
        type_category=_clean(type_category),
        date_received=_parse_date(received),
        date_final_submissions=_parse_date(final),
        outcome=None,
    )
