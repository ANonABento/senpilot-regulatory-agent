"""Success and error reply templates.

Pure functions over the stable ``ScrapeResult`` model — no network, no LLM, no
scraper internals. The success body matches the assignment PDF's gold example
(see docs/ACCEPTANCE_CRITERIA.md). An LLM may later rewrite this prose, but this
template is the deterministic fallback and the thing unit tests assert against.
"""

from __future__ import annotations

from datetime import date

from regulatory_agent.models import DocumentType, ScrapeResult, TabCounts

VALID_TYPES = ", ".join(dt.value for dt in DocumentType)

# Tab label order as it appears on the matter page / in the reply.
_TAB_ORDER: list[tuple[str, str]] = [
    ("exhibits", "Exhibits"),
    ("key_documents", "Key Documents"),
    ("other_documents", "Other Documents"),
    ("transcripts", "Transcripts"),
    ("recordings", "Recordings"),
]


def _format_date(value: date | None) -> str | None:
    if value is None:
        return None
    # Avoid platform-specific %-d; build "April 7, 2025" by hand.
    return f"{value:%B} {value.day}, {value.year}"


def _humanize_list(items: list[str]) -> str:
    """['A'] -> 'A'; ['A','B'] -> 'A or B'; ['A','B','C'] -> 'A, B or C'."""
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return f"{', '.join(items[:-1])} or {items[-1]}"


def _counts_sentence(counts: TabCounts) -> str:
    """Render the per-tab counts, collapsing zero tabs into 'no X or Y'.

    Matches the PDF gold: '13 Exhibits, 5 Key Documents, 21 Other Documents, and
    no Transcripts or Recordings.'
    """
    present: list[str] = []
    absent: list[str] = []
    for attr, label in _TAB_ORDER:
        n = getattr(counts, attr)
        if n > 0:
            present.append(f"{n} {label}")
        else:
            absent.append(label)

    parts = list(present)
    if absent:
        parts.append(f"no {_humanize_list(absent)}")
    if not parts:
        return "no documents"
    if len(parts) == 1:
        return parts[0]
    return ", ".join(parts[:-1]) + ", and " + parts[-1]


def build_success_reply(result: ScrapeResult, user_name: str | None = None) -> str:
    """Compose the success email body for a completed scrape."""
    meta = result.metadata
    doc_type = result.requested_document_type.value
    greeting = f"Hi {user_name}," if user_name else "Hi,"

    # Each entry is a paragraph; blocks are joined with a blank line.
    blocks: list[str] = [greeting]

    about = meta.title_description or "a matter on the UARB public docket"
    if meta.type_category:
        blocks.append(
            f"{result.matter_number} is about {about}. It relates to {meta.type_category}."
        )
    else:
        blocks.append(f"{result.matter_number} is about {about}.")

    received = _format_date(meta.date_received)
    final = _format_date(meta.date_final_submissions)
    if received and final:
        blocks.append(
            f"The matter had an initial filing on {received} "
            f"and a final filing on {final}."
        )
    elif received:
        blocks.append(f"The matter had an initial filing on {received}.")

    blocks.append(f"I found {_counts_sentence(result.tab_counts)}.")

    if result.downloaded_count > 0:
        blocks.append(
            f"I downloaded {result.downloaded_count} out of the "
            f"{result.available_in_tab} {doc_type} and am attaching them as a ZIP here."
        )
    elif result.available_in_tab == 0:
        blocks.append(
            f"There are no {doc_type} on this matter, so there's nothing to attach."
        )
    else:
        blocks.append(
            f"I wasn't able to download any of the {result.available_in_tab} "
            f"{doc_type} this time, so no ZIP is attached."
        )

    return "\n\n".join(blocks).strip() + "\n"


def build_error_reply(reason: str) -> str:
    """Compose a helpful error email body for an unprocessable request."""
    return (
        "Hi,\n\n"
        f"I couldn't process your request: {reason}\n\n"
        "Please send a matter number (e.g. M12205) and one of: "
        f"{VALID_TYPES}.\n"
    )
