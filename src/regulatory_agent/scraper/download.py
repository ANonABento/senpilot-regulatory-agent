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
from urllib.parse import unquote

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
    # Resource URLs percent-encode the name (e.g. "H-4%28C%29.pdf" -> "H-4(C).pdf").
    base = _UNSAFE_CHARS.sub("_", unquote(filename)).strip() or f"document_{index}.pdf"
    if base not in used:
        used.add(base)
        return base
    stem, suffix = Path(base).stem, Path(base).suffix
    candidate = f"{index:02d}_{stem}{suffix}"
    used.add(candidate)
    return candidate


def _go_get_it_buttons(page: Page):
    return page.get_by_role("button", name=_GO_GET_IT)


def _row_signatures(page: Page) -> list[str]:
    """Row text for each rendered GO GET IT button, in the same DOM order Playwright's
    ``nth(i)`` uses. Lets us skip already-downloaded rows *without* re-clicking them
    (re-opening a download dialog resets the grid's scroll, stalling progress)."""
    return page.evaluate(
        """() => [...document.querySelectorAll('button')]
            .filter(b => /go get it/i.test(b.innerText))
            .map(b => { const tr = b.closest('tr');
                        return tr ? tr.innerText.replace(/\\s+/g, ' ').trim() : ''; })"""
    )


def _click_go_get_it(page: Page, index: int) -> bool:
    """Click the nth GO GET IT button, tolerating the glass-pane overlay.

    The ``iwp-glass-pane`` header overlay intermittently intercepts pointer events;
    a normal click then burns the full timeout. Use a short timeout and fall back to
    a forced click (which bypasses the hit-test) so a transient overlay can't stall
    the run for a minute.
    """
    try:
        _go_get_it_buttons(page).nth(index).click(timeout=12_000)
        return True
    except Exception:
        try:
            _go_get_it_buttons(page).nth(index).click(force=True, timeout=8_000)
            return True
        except Exception as exc:
            logger.warning("GO GET IT click %d failed: %s", index, str(exc).splitlines()[0])
            return False


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

    Rows are addressed by button index within the current viewport and de-duplicated
    by document filename — the stable per-file identifier. (Document IDs vary by tab:
    numeric for Other Documents, ``H-1`` style for Exhibits, so a parsed "doc number"
    is not dependable; and a re-clicked row gets a fresh connector id, so the full
    resource URL isn't stable either.) The virtualized grid is scrolled to reach rows
    beyond the rendered batch; re-clicking an already-seen row is harmless because its
    filename is skipped. ``ws_frames`` is the list from :func:`browser.capture_ws_frames`.
    """
    settings.download_dir.mkdir(parents=True, exist_ok=True)
    downloads: list[Path] = []
    used_names: set[str] = set()
    seen_rows: set[str] = set()
    seen_files: set[str] = set()
    stagnant = 0

    while len(downloads) < max_count and stagnant < 3:
        progressed = False
        signatures = _row_signatures(page)
        for i, sig in enumerate(signatures):
            if len(downloads) >= max_count:
                break
            if not sig or sig in seen_rows:  # already handled this row; don't re-click it
                continue
            seen_rows.add(sig)
            mark = len(ws_frames)
            if not _click_go_get_it(page, i):
                _close_dialog(page)
                continue
            url_path = _capture_resource_url(page, ws_frames, mark)
            # Secondary de-dupe by filename guards the rare case where the same file
            # surfaces under two rows / a fresh connector id.
            doc_name = unquote(url_path.rsplit("/", 1)[-1]) if url_path else None
            if doc_name and doc_name not in seen_files:
                seen_files.add(doc_name)
                # Fetch while the dialog is still open: closing it destroys the Vaadin
                # FileDownloader connector that serves the resource (otherwise 404).
                path = _fetch_and_save(page, url_path, len(downloads) + 1, used_names)
                if path:
                    downloads.append(path)
                    progressed = True
            _close_dialog(page)

        if len(downloads) >= max_count:
            break
        _scroll_grid(page)
        stagnant = 0 if progressed else stagnant + 1

    logger.info("Downloaded %d file(s)", len(downloads))
    return downloads
