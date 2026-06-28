# Testing Strategy

## Test pyramid

| Level | What | How |
|-------|------|-----|
| Unit | Parsing, models, reply templates | pytest, no network |
| Integration | Scraper against live UARB | manual / marked `@pytest.mark.live` |
| E2E | Email in → ZIP out | manual demo script |

## Unit tests (`tests/`)

Current state: `test_parse.py`, `test_models.py`, `test_metadata.py` exist; 10 tests pass via `pytest -m "not live"`. The reply/parse-pipeline tests below are **planned** (Phase 2–3, not yet written).

### `test_parse.py` (exists — currently fixture sanity only)

- Sample email contains `M12205`
- Sample email mentions "Other Documents"
- _TODO once `agent/parse.py` lands:_ reject email with no matter number; reject unknown document type

### `test_models.py` (exists)

- `DocumentType.from_user_text` exact + alias match, unknown → `None`

### `test_metadata.py` (exists)

- Date parsing (`April 7, 2025` and `04/07/2025` → `2025-04-07`)
- `TAB_COUNT` / `DATE_RECEIVED` / `DATE_FINAL_SUBMISSIONS` regexes against a sample body

### `test_reply.py` (exists)

- Success body contains all tab counts
- Zero transcripts/recordings → "no Transcripts or Recordings"
- "10 out of 21" wording when partial download
- Greeting, date formatting, empty-tab "nothing to attach", error template

## Fixtures

`tests/fixtures/sample_request_email.txt` — assignment example email (exists).

`tests/fixtures/m12205_matter_page.txt` — **not yet captured.** Snapshot the matter-page body text (`page.locator("body").inner_text()`) during the first successful live scrape so `test_metadata.py` can assert against real DOM output instead of a hand-written `SAMPLE_BODY`.

## Live scraper test

```bash
pytest tests/test_scraper_live.py -m live
```

Mark as optional CI skip. Validates navigation to M12205, exact tab counts (13/5/21/0/0), 10 downloads, metadata fields, and a 10-entry ZIP.

> The test currently calls `scrape_matter(..., headless=True)` and asserts **exact** counts. For debugging, run the CLI with `--headed` instead (`scrape M12205 --type "Other Documents" --headed`); to make the test resilient to site updates, relax the exact-count asserts to ranges.

## Manual demo script (submission)

Document in README; run before submitting:

### Step 1 — CLI scrape

```powershell
python -m regulatory_agent scrape M12205 --type "Other Documents" --json
```

Verify:

- [ ] Exit code 0
- [ ] ZIP exists in `output/`
- [ ] JSON shows `downloaded_count: 10`, `available_in_tab: 21`
- [ ] ZIP contains 10 PDF files

### Step 2 — Parse only (Phase 3 — not yet implemented)

```bash
python -m regulatory_agent parse-email --file tests/fixtures/sample_request_email.txt
```

Currently exits code 2 (stub). Once `agent/parse.py` lands, verify structured output matches M12205 + Other Documents.

### Step 3 — Email E2E

```powershell
python -m regulatory_agent worker --once
```

After sending test email to agent inbox:

- [ ] Reply received within 2 poll cycles
- [ ] ZIP attached
- [ ] Body matches assignment example format

### Step 4 — Error cases

| Input | Expected |
|-------|----------|
| Matter `M99999` (invalid) | Error reply |
| Type "Briefs" | Error reply listing valid types |
| Valid matter + empty tab | Reply with counts, no attachment |

## Recording demo

- 2–3 min screen recording: send email → show reply → open ZIP
- Optional: include headed browser scrape clip

## Regression checklist before submit

- [ ] `.env` not committed
- [ ] README setup steps work on clean venv
- [ ] `requirements.txt` installs cleanly
- [ ] No hardcoded secrets
- [ ] Logs do not print full email bodies in production mode
