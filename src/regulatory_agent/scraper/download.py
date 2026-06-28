"""Select a document tab and download files from the UARB matter page.

FileMaker WebDirect (a Vaadin app) does not expose plain download links. Clicking a
row's "GO GET IT" button opens a modal "Download Files" dialog, and the file's
resource URL (``app://APP/connector/0/<id>/dl/<docno>.pdf``) is pushed to the client
over the Vaadin websocket. We capture that frame, resolve the URL against the WebDirect
base, and fetch the bytes directly with the session's request context — which works
headlessly, unlike the dialog's ``window.open`` based download button.

The document list is a virtualized Vaadin Grid that only renders ~8 rows at a time, so
we scroll the grid to reach the requested number of files.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from playwright.sync_api import Page

from regulatory_agent.config import settings
from regulatory_agent.models import DocumentType
from regulatory_agent.scraper.browser import wait_for_ready

logger = logging.getLogger(__name__)

_UNSAFE_CHARS = re.compile(r'[<>:"/\\|?*]')
_GO_GET_IT = re.compile(r"go get it", re.I)
# Resource URL pushed over the websocket when the download dialog opens.
_RESOURCE_URL = re.compile(r'"uRL"\s*:\s*"app://(APP/connector/\d+/\d+/dl/[^"]+)"')
# https://uarb.novascotia.ca/fmi/webd/  (drop the trailing "UARB15" solution name)
_WEBD_BASE = settings.uarb_base_url.rsplit("/", 1)[0] + "/"


def select_document_tab(page: Page, document_type: DocumentType) -> None:
    """Click the tab whose visible text starts with the document type name."""
    pattern = re.compile(rf"^{re.escape(document_type.value)}", re.I)
    page.get_by_text(pattern).first.click()
    wait_for_ready(page)
    page.wait_for_timeout(1500)
    logger.info("Selected tab: %s", document_type.value)


def _sanitize_filename(filename: str, index: int, used: set[str]) -> str:
    base = _UNSAFE_CHARS.sub("_", filename).strip() or f"document_{index}.pdf"
    if base not in used:
        used.add(base)
        return base
    stem, suffix = Path(base).stem, Path(base).suffix
    candidate = f"{index:02d}_{stem}{suffix}"
    used.add(candidate)
    return candidate


def _visible_rows(page: Page) -> list[dict]:
    """Return [{docno, row_index}] for each rendered grid row that has a GO GET IT button."""
    return page.evaluate(
        """() => {
            const rows = [];
            document.querySelectorAll('.v-grid-body tr').forEach(tr => {
                const hasBtn = [...tr.querySelectorAll('button')].some(
                    b => /go get it/i.test(b.innerText));
                if (!hasBtn) return;
                const m = tr.innerText.match(/\\b(\\d{4,7})\\b/);
                rows.push({docno: m ? m[1] : null,
                           row_index: tr.getAttribute('aria-rowindex')});
            });
            return rows;
        }"""
    )


def _click_go_get_it_for(page: Page, docno: str) -> bool:
    """Click the GO GET IT button in the row containing ``docno``. Returns True on click."""
    button = page.locator(".v-grid-body tr", has_text=docno).get_by_role(
        "button", name=_GO_GET_IT
    )
    if button.count() == 0:
        return False
    button.first.click()
    return True


def _capture_resource_url(page: Page, frames: list[str], mark: int) -> str | None:
    """Wait for the download dialog's resource URL to arrive on the websocket."""
    for _ in range(20):
        page.wait_for_timeout(500)
        match = _RESOURCE_URL.search("\n".join(frames[mark:]))
        if match:
            return match.group(1)
    return None


def _close_dialog(page: Page) -> None:
    """Dismiss the modal "Download Files" dialog before handling the next row."""
    page.keyboard.press("Escape")
    page.wait_for_timeout(300)
    close = page.get_by_role("button", name=re.compile(r"^close$", re.I))
    if close.count() > 0:
        try:
            close.first.click(timeout=3000)
        except Exception:
            pass
    page.wait_for_timeout(500)


def _fetch_complete(page: Page, full_url: str, attempts: int = 3) -> bytes | None:
    """Fetch a resource, retrying if the body is shorter than Content-Length.

    On a slow server the streamed response can be delivered incomplete with a 200
    status, yielding a truncated PDF. Comparing against Content-Length catches this.
    """
    for attempt in range(1, attempts + 1):
        response = page.context.request.get(full_url, timeout=120_000)
        if not response.ok:
            logger.warning("Fetch failed (%d) for %s", response.status, full_url)
            return None
        body = response.body()
        declared = response.headers.get("content-length")
        if declared and int(declared) != len(body):
            logger.warning(
                "Truncated download (%d/%s bytes), retry %d/%d",
                len(body), declared, attempt, attempts,
            )
            page.wait_for_timeout(1000)
            continue
        return body
    logger.error("Gave up on truncated download after %d attempts: %s", attempts, full_url)
    return None


def _fetch_and_save(page: Page, url_path: str, index: int, used: set[str]) -> Path | None:
    """Fetch a resource URL with the session request context and write it to disk."""
    body = _fetch_complete(page, _WEBD_BASE + url_path)
    if body is None:
        return None
    filename = _sanitize_filename(url_path.rsplit("/", 1)[-1], index, used)
    path = settings.download_dir / filename
    path.write_bytes(body)
    logger.info("Saved download %d: %s (%d bytes)", index, filename, len(body))
    return path


def _scroll_grid(page: Page) -> None:
    """Scroll the virtualized Vaadin Grid down to render the next batch of rows."""
    page.evaluate(
        """() => {
            const scroller = document.querySelector('.v-grid-scroller-vertical');
            const wrapper = document.querySelector('.v-grid-tablewrapper');
            const step = 8 * 38;  // ~8 rows worth of pixels
            if (scroller) scroller.scrollTop += step;
            if (wrapper) wrapper.scrollTop += step;
        }"""
    )
    page.wait_for_timeout(1200)


def download_documents(page: Page, ws_frames: list[str], max_count: int = 10) -> list[Path]:
    """Download up to ``max_count`` files from the selected document tab.

    ``ws_frames`` is the live list returned by :func:`browser.capture_ws_frames`.
    """
    settings.download_dir.mkdir(parents=True, exist_ok=True)
    downloads: list[Path] = []
    used_names: set[str] = set()
    processed: set[str] = set()
    stagnant = 0

    while len(downloads) < max_count and stagnant < 3:
        rows = [r for r in _visible_rows(page) if r["docno"] and r["docno"] not in processed]
        if not rows:
            seen_before = {r["docno"] for r in _visible_rows(page)}
            _scroll_grid(page)
            seen_after = {r["docno"] for r in _visible_rows(page)}
            stagnant = stagnant + 1 if seen_after <= seen_before else 0
            continue

        for row in rows:
            if len(downloads) >= max_count:
                break
            docno = row["docno"]
            processed.add(docno)
            mark = len(ws_frames)
            try:
                if not _click_go_get_it_for(page, docno):
                    continue
            except Exception as exc:
                logger.warning("Click failed for doc %s: %s", docno, exc)
                _close_dialog(page)
                continue
            url_path = _capture_resource_url(page, ws_frames, mark)
            if url_path:
                path = _fetch_and_save(page, url_path, len(downloads) + 1, used_names)
                if path:
                    downloads.append(path)
            else:
                logger.warning("No resource URL captured for doc %s", docno)
            _close_dialog(page)

    logger.info("Downloaded %d file(s)", len(downloads))
    return downloads
