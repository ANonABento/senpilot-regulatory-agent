"""Navigate UARB search UI to a matter detail page."""

from __future__ import annotations

import logging

from playwright.sync_api import Page

from regulatory_agent.config import settings
from regulatory_agent.scraper.browser import wait_for_ready

logger = logging.getLogger(__name__)

TAB_KEYWORDS = ("Exhibits", "Key Documents", "Other Documents", "Transcripts", "Recordings")
MATTER_FIELD_SELECTOR = '.fm-textarea:has(.placeholder:text-is("eg M01234"))'


class MatterNotFoundError(Exception):
    """Raised when matter search does not land on a detail view."""


def _wait_for_homepage(page: Page) -> None:
    page.wait_for_function(
        "() => document.body && document.body.innerText.includes('Go Directly to Matter')",
        timeout=settings.page_load_timeout_ms,
    )


def _fill_matter_number(page: Page, matter_number: str) -> None:
    matter_box = page.locator(MATTER_FIELD_SELECTOR)
    for attempt in range(3):
        matter_box.locator(".text").click(force=True)
        page.wait_for_timeout(300)
        for _ in range(15):
            page.keyboard.press("Backspace")
        page.keyboard.type(matter_number, delay=30)
        entered = matter_box.locator(".text").inner_text().strip()
        logger.info("Entered matter number (attempt %d): %r", attempt + 1, entered)
        if matter_number in entered:
            return
    raise MatterNotFoundError(
        f"Could not enter matter number {matter_number} (field shows {entered!r})"
    )


def _click_direct_matter_search(page: Page) -> None:
    buttons = page.locator("button").filter(has_text="Search")
    chosen = None
    chosen_y = None
    for i in range(buttons.count()):
        box = buttons.nth(i).bounding_box()
        if box and 300 <= box["y"] <= 450:
            if chosen_y is None or box["y"] < chosen_y:
                chosen_y = box["y"]
                chosen = buttons.nth(i)
    if chosen is None:
        chosen = buttons.nth(1)
    chosen.click(force=True)


def go_to_matter(page: Page, matter_number: str) -> None:
    """Load UARB homepage, search by matter number, and wait for detail page."""
    logger.info("Navigating to %s", settings.uarb_base_url)
    page.goto(settings.uarb_base_url)
    wait_for_ready(page)
    _wait_for_homepage(page)
    logger.info("Loaded homepage: %s", page.url)

    _fill_matter_number(page, matter_number)
    _click_direct_matter_search(page)

    try:
        page.wait_for_function(
            f"() => document.body && document.body.innerText.includes('{matter_number}')",
            timeout=settings.page_load_timeout_ms * 2,
        )
    except Exception as exc:
        body = page.locator("body").inner_text()
        if "No Records Found" in body or "No records matched" in body:
            raise MatterNotFoundError(f"Matter {matter_number} not found") from exc
        raise MatterNotFoundError(
            f"Matter {matter_number} detail page did not load within timeout"
        ) from exc

    wait_for_ready(page)
    logger.info("Matter page loaded: %s", page.url)

    body = page.locator("body").inner_text()
    if matter_number not in body:
        raise MatterNotFoundError(f"Matter {matter_number} not found on detail page")

    if not any(keyword in body for keyword in TAB_KEYWORDS):
        raise MatterNotFoundError(
            f"Matter {matter_number} page loaded but no document tabs were found"
        )
