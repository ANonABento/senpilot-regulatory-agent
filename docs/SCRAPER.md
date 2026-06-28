# Scraper Specification (Playwright)

Target: [UARB15 FileMaker WebDirect](https://uarb.novascotia.ca/fmi/webd/UARB15)

## UI flow (from assignment PDF)

```
1. Load UARB15 homepage
2. "Go Directly to Matter" → enter M#####
3. Click Search (matter-specific search button, not advanced search)
4. Wait for matter detail page
5. Read header metadata + tab counts
6. Click tab matching requested document type
7. For each row (up to 10): click "GO GET IT" → save download
8. Return files + metadata
```

## FileMaker WebDirect quirks

Observed during recon (2026-06-28):

| Quirk | Handling |
|-------|----------|
| Loading overlay `.iwp-glass-pane` | Wait `state=hidden` before interactions; re-wait after navigation |
| No standard `<input>` elements | Click visible placeholder `eg M01234`, then `keyboard.type(matter)` |
| Multiple "Search" buttons | Use the one in "Go Directly to Matter" section (typically last Search button) |
| Slow page transitions | `PAGE_LOAD_TIMEOUT_MS=60000`, post-action sleep 2–5s then wait for glass pane |
| Tab labels include counts | Parse `Exhibits - 13` with regex `^(.+?)\s*-\s*(\d+)$` |
| Downloads via GO GET IT | Use Playwright download API per button click |

## Module: `browser.py`

```python
class BrowserSession:
    def __enter__(self) -> Page: ...
    def __exit__(...): ...
```

Responsibilities:

- Launch Chromium (`headless` from config)
- Set default timeouts
- Provide helper: `wait_for_ready(page)` → waits for all glass panes hidden

Implementation notes:

```python
def wait_for_ready(page: Page, timeout_ms: int = 60000) -> None:
    page.wait_for_load_state("networkidle", timeout=timeout_ms)
    page.locator(".iwp-glass-pane").first.wait_for(state="hidden", timeout=timeout_ms)
```

If `networkidle` is flaky, fall back to `domcontentloaded` + fixed delay + glass pane wait.

## Module: `navigate.py`

### `go_to_matter(page, matter_number: str) -> None`

1. `page.goto(UARB_BASE_URL)`
2. `wait_for_ready(page)` + wait for body text to contain `Go Directly to Matter`
3. Fill the matter field, then click search, then wait for the detail page
4. Assert matter page loaded: body contains the matter number **and** at least one tab keyword (Exhibits, Key Documents, ...)

Raise `MatterNotFoundError` if the field can't be filled, the search yields `No Records Found`, or the detail view doesn't appear within timeout.

#### As implemented (recon-validated — do not "simplify" back to the idealized form below)

The earlier draft suggested `get_by_role("button", name="Search").last`. That did **not** work against the live FileMaker DOM. The shipped `navigate.py` uses:

- **Matter input** (`_fill_matter_number`): locate `.fm-textarea:has(.placeholder:text-is("eg M01234"))`, click its `.text`, backspace-clear (~15×), then `keyboard.type(matter, delay=30)`, and verify the typed value landed (3 attempts). FileMaker has no real `<input>`.
- **Search button** (`_click_direct_matter_search`): among `button:has-text("Search")`, pick the one whose `bounding_box().y` falls in **300–450** (the "Go Directly to Matter" button, above the advanced-search button). ⚠️ This is a viewport-dependent heuristic — the most fragile part of the scraper; revisit first if navigation breaks.
- **Detail-load wait**: `wait_for_function` polling `document.body.innerText.includes(matter_number)` with `2× page_load_timeout`, then re-`wait_for_ready`.

## Module: `metadata.py`

### `extract_matter_metadata(page) -> MatterMetadata`

Parse visible text from matter header area. Suggested approach:

1. Get full body text
2. Use label anchors from screenshot:
   - `Matter No:` → value on same/adjacent line
   - `Status:`
   - `Title - Description:` (may wrap)
   - `Type / Category:`
   - `Date Received:` → parse to ISO date
   - `Date Final Submissions:` → parse to ISO date
   - `Outcome:`

Prefer robust regex over brittle CSS selectors (FileMaker regenerates class names).

Example patterns:

```python
MATTER_NO = re.compile(r"Matter No:\s*(M\d{5})", re.I)
TAB_COUNT = re.compile(r"^(Exhibits|Key Documents|Other Documents|Transcripts|Recordings)\s*-\s*(\d+)", re.I | re.M)
```

### `extract_tab_counts(page) -> TabCounts`

Scan body text for tab labels with counts. Default missing tabs to 0.

## Module: `download.py`

### `select_document_tab(page, document_type: DocumentType) -> None`

Click tab whose visible text **starts with** the document type name (case-insensitive).

Wait `wait_for_ready(page)` after click.

### `download_documents(page, max_count: int = 10) -> list[Path]`

Algorithm:

```python
downloads: list[Path] = []
buttons = page.get_by_role("button", name=re.compile(r"go get it", re.I))
count = min(buttons.count(), max_count)
for i in range(count):
    with page.expect_download(timeout=120_000) as dl_info:
        buttons.nth(i).click(force=True)
    download = dl_info.value
    path = DOWNLOAD_DIR / sanitize(download.suggested_filename)
    download.save_as(path)
    downloads.append(path)
    wait_for_ready(page)  # FileMaker may reload between downloads
return downloads
```

**Filename sanitization:** Replace unsafe chars; prefix with doc index if collisions.

#### As implemented

The shipped `download._wait_for_download` does **not** assume a clean `expect_download` per click. GO GET IT on the live site often opens a popup instead of streaming a download, so it tries, in order:

1. `page.expect_download()` around the click (direct case).
2. Inspect already-open `context.pages` for a pending download or a fetchable PDF.
3. `page.expect_popup()` around a re-click, then `popup.expect_download()`.
4. `_fetch_from_popup`: if the popup URL is a PDF, fetch bytes via `context.request.get(url)` and wrap them in a `_FetchedDownload` shim exposing `save_as`.

⚠️ Known gap: `_fetch_from_popup` writes `_tmp_{index}_*` files into `DOWNLOAD_DIR` that are never deleted — clean these up (or use a temp dir) before zipping by directory glob.

**Edge cases:**

- Fewer than 10 rows → download all available
- GO GET IT opens new tab instead of download → popup + fetch fallback (above)
- Recording types may not be PDF → still download whatever is served

## Module: `zipper.py`

### `create_zip(files: list[Path], matter: str, doc_type: str) -> Path`

Output: `output/{matter}_{snake_case_doc_type}.zip`

- Flat structure inside ZIP (no nested folders required)
- Preserve original filenames where possible

## Module: `service.py`

### `scrape_matter(matter_number: str, document_type: DocumentType) -> ScrapeResult`

Orchestrates full pipeline inside `BrowserSession`.

Pseudo-code:

```python
with BrowserSession() as page:
    go_to_matter(page, matter_number)
    metadata = extract_matter_metadata(page)
    tab_counts = extract_tab_counts(page)
    select_document_tab(page, document_type)
    available = tab_counts.for_type(document_type)
    files = download_documents(page, max_count=settings.max_downloads)
    zip_path = create_zip(files, matter_number, document_type.value)
    return ScrapeResult(...)
```

## CLI contract

```bash
python -m regulatory_agent scrape M12205 --type "Other Documents"
python -m regulatory_agent scrape M12205 --type "Other Documents" --max 3 --json
```

Flags:

- `--max` override download cap
- `--json` print `ScrapeResult` JSON to stdout
- `--headed` set HEADLESS=false for debugging

## Validation targets (M12205)

Expected metadata (approximate — verify against live site):

| Field | Expected |
|-------|----------|
| Title contains | Halifax Regional Water Commission |
| Type / Category | Water / Capital Expenditure |
| Date Received | April 7, 2025 |
| Date Final Submissions | October 23, 2025 |
| Exhibits | 13 |
| Key Documents | 5 |
| Other Documents | 21 |
| Transcripts | 0 |
| Recordings | 0 |

When requesting Other Documents with max=10: **10 files in ZIP**, `downloaded_count=10`, `available_in_tab=21`.

## Debugging checklist

- [x] Run with `--headed` (`scrape ... --headed`)
- [ ] **Screenshot on failure → `output/debug_{timestamp}.png` — NOT yet wired.** `cli._save_debug_screenshot` only prints a path; the browser is already closed by `service.py`'s context manager when the exception surfaces. To actually capture, take the screenshot inside `BrowserSession`/`scrape_matter`'s `except` before the context exits.
- [x] Log page URL after each navigation step (`navigate.py` logs `page.url`)
- [ ] Save HTML/body-text dump → also the source for `tests/fixtures/m12205_matter_page.txt`
- [ ] `slow_mo` is not currently exposed via config — add to `BrowserSession.launch` if needed

## Performance

- Full scrape for 10 PDFs: budget **2–5 minutes** (FileMaker is slow)
- Worker should process emails sequentially (one browser at a time)
