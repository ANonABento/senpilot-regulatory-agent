"""Select document tab and download files via GO GET IT buttons."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from playwright.sync_api import Download, Page, TimeoutError as PlaywrightTimeoutError

from regulatory_agent.config import settings
from regulatory_agent.models import DocumentType
from regulatory_agent.scraper.browser import wait_for_ready

logger = logging.getLogger(__name__)

_UNSAFE_CHARS = re.compile(r'[<>:"/\\|?*]')
_GO_GET_IT = re.compile(r"go get it", re.I)


def _sanitize_filename(filename: str, index: int, used: set[str]) -> str:
    base = _UNSAFE_CHARS.sub("_", filename).strip() or f"document_{index}"
    if base not in used:
        used.add(base)
        return base
    stem = Path(base).stem
    suffix = Path(base).suffix
    candidate = f"{index:02d}_{stem}{suffix}"
    used.add(candidate)
    return candidate


def select_document_tab(page: Page, document_type: DocumentType) -> None:
    """Click tab whose visible text starts with the document type name."""
    pattern = re.compile(rf"^{re.escape(document_type.value)}", re.I)
    page.get_by_text(pattern).first.click()
    wait_for_ready(page)
    page.wait_for_timeout(2000)
    logger.info("Selected tab: %s", document_type.value)


def _go_get_it_buttons(page: Page):
    role_buttons = page.get_by_role("button", name=_GO_GET_IT)
    if role_buttons.count() > 0:
        return role_buttons
    return page.locator("button").filter(has_text=_GO_GET_IT)


def download_documents(page: Page, max_count: int = 10) -> list[Path]:
    """Click GO GET IT buttons and save downloads (up to max_count)."""
    settings.download_dir.mkdir(parents=True, exist_ok=True)
    downloads: list[Path] = []
    used_names: set[str] = set()

    total = _go_get_it_buttons(page).count()
    count = min(total, max_count)
    logger.info("Downloading %d of %d available GO GET IT buttons", count, total)

    for i in range(count):
        button = _go_get_it_buttons(page).nth(i)
        path = _click_and_save(page, button, i + 1, used_names)
        downloads.append(path)
        wait_for_ready(page)

    return downloads


def _click_and_save(page: Page, button, index: int, used_names: set[str]) -> Path:
    """Click a GO GET IT button and save the resulting download."""
    download = _wait_for_download(page, button, index)
    filename = _sanitize_filename(download.suggested_filename, index, used_names)
    path = settings.download_dir / filename
    download.save_as(path)
    logger.info("Saved download %d: %s", index, path.name)
    return path


def _wait_for_download(page: Page, button, index: int) -> Download:
    """Handle direct download, popup, or fetched PDF from new tab."""
    try:
        with page.expect_download(timeout=120_000) as dl_info:
            button.click(force=True)
        return dl_info.value
    except PlaywrightTimeoutError:
        logger.info("Direct download not triggered for button %d; checking popups", index)

    for popup in page.context.pages:
        if popup is page:
            continue
        try:
            with popup.expect_download(timeout=30_000) as dl_info:
                popup.wait_for_load_state("domcontentloaded")
            download = dl_info.value
            popup.close()
            return download
        except PlaywrightTimeoutError:
            fetched = _fetch_from_popup(page, popup, index)
            if fetched is not None:
                popup.close()
                return fetched

    try:
        with page.expect_popup(timeout=60_000) as popup_info:
            button.click(force=True)
        popup = popup_info.value
        try:
            with popup.expect_download(timeout=120_000) as dl_info:
                popup.wait_for_load_state("domcontentloaded")
            return dl_info.value
        except PlaywrightTimeoutError:
            fetched = _fetch_from_popup(page, popup, index)
            if fetched is not None:
                return fetched
            raise
        finally:
            popup.close()
    except PlaywrightTimeoutError as exc:
        raise RuntimeError(f"GO GET IT button {index} did not trigger a download") from exc


def _fetch_from_popup(page: Page, popup: Page, index: int) -> Download | None:
    url = popup.url
    if not url or url == "about:blank":
        return None
    response = page.context.request.get(url)
    if not response.ok:
        return None
    content_type = response.headers.get("content-type", "")
    if "pdf" not in content_type.lower() and not url.lower().endswith(".pdf"):
        return None
    suggested = Path(url).name or f"document_{index}.pdf"
    temp_path = settings.download_dir / f"_tmp_{index}_{suggested}"
    temp_path.write_bytes(response.body())
    return _FetchedDownload(temp_path, suggested)  # type: ignore[return-value]


class _FetchedDownload:
    def __init__(self, file_path: Path, name: str) -> None:
        self._path = file_path
        self.suggested_filename = name

    def save_as(self, target: str | Path) -> None:
        Path(target).write_bytes(self._path.read_bytes())
