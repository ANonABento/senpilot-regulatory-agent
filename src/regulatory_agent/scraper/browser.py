"""Playwright browser lifecycle and FileMaker ready-state waits."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright

from regulatory_agent.config import settings

if TYPE_CHECKING:
    from types import TracebackType

logger = logging.getLogger(__name__)


def wait_for_ready(page: Page, timeout_ms: int | None = None) -> None:
    """Wait for page load and FileMaker glass-pane overlay to clear."""
    timeout = timeout_ms or settings.page_load_timeout_ms
    try:
        page.wait_for_load_state("networkidle", timeout=timeout)
    except Exception:
        try:
            page.wait_for_load_state("domcontentloaded", timeout=timeout)
        except Exception:
            pass
        page.wait_for_timeout(2000)
    try:
        page.locator(".iwp-glass-pane").first.wait_for(state="hidden", timeout=timeout)
    except Exception:
        logger.warning("Glass pane still visible after %dms; continuing", timeout)


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
