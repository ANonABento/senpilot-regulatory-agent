"""Playwright browser lifecycle and FileMaker ready-state waits."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright

from regulatory_agent.config import settings

if TYPE_CHECKING:
    from types import TracebackType

logger = logging.getLogger(__name__)


# Vaadin (FileMaker WebDirect is built on Vaadin) shows a `.v-loading-indicator`
# element during server round-trips. Note: `.iwp-glass-pane` is NOT a single loading
# overlay — it is a class applied to dozens of permanently-visible widgets, so waiting
# for it to become "hidden" never succeeds. Use the loading indicator instead.
_LOADING_IDLE_JS = """() => {
    const els = document.querySelectorAll('.v-loading-indicator');
    for (const el of els) {
        if (getComputedStyle(el).display !== 'none') return false;
    }
    return true;
}"""


def wait_for_ready(page: Page, timeout_ms: int | None = None) -> None:
    """Wait until FileMaker/Vaadin has finished its current server round-trip."""
    timeout = timeout_ms or settings.action_timeout_ms
    try:
        page.wait_for_load_state("networkidle", timeout=timeout)
    except Exception:
        try:
            page.wait_for_load_state("domcontentloaded", timeout=timeout)
        except Exception:
            pass
    try:
        page.wait_for_function(_LOADING_IDLE_JS, timeout=timeout)
    except Exception:
        logger.debug("Vaadin loading indicator still active after %dms; continuing", timeout)
    page.wait_for_timeout(800)


def capture_ws_frames(page: Page) -> list[str]:
    """Record inbound Vaadin push frames so the downloader can recover file URLs.

    FileMaker WebDirect delivers the "GO GET IT" download dialog — including the
    resource URL of each file — over a websocket, not HTTP. Must be called before
    the page navigates, while the websocket is still being opened.
    """
    frames: list[str] = []

    def on_websocket(ws) -> None:
        ws.on(
            "framereceived",
            lambda payload: frames.append(
                payload if isinstance(payload, str) else str(payload)
            ),
        )

    page.on("websocket", on_websocket)
    return frames


class BrowserSession:
    """Context manager that launches Chromium and yields a configured Page."""

    def __init__(self, *, headless: bool | None = None) -> None:
        self._headless = headless if headless is not None else settings.headless
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self.page: Page | None = None

    def __enter__(self) -> Page:
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=self._headless)
        self._context = self._browser.new_context(accept_downloads=True)
        self._context.set_default_timeout(settings.action_timeout_ms)
        self.page = self._context.new_page()
        self.page.set_default_timeout(settings.page_load_timeout_ms)
        logger.info("Browser launched (headless=%s)", self._headless)
        return self.page

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self._context:
            self._context.close()
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()
        self.page = None
