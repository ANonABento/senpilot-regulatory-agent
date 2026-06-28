# Testing Strategy

## Test pyramid

| Level | What | How |
|-------|------|-----|
| Unit | Parsing, models, reply templates | pytest, no network |
| Integration | Scraper against live UARB | manual / marked `@pytest.mark.live` |
| E2E | Email in → ZIP out | manual demo script |

## Unit tests (`tests/`)

### `test_parse.py`

- Extract `M12205` from sample email
- Map "other documents" → `DocumentType.OTHER_DOCUMENTS`
- Reject email with no matter number
- Reject unknown document type

### `test_models.py`

- Tab count parsing from sample text fixture
- Date parsing `04/07/2025` → `2025-04-07`

### `test_reply.py`

- Success body contains all tab counts
- Zero transcripts/recordings → "no Transcripts or Recordings"
- "10 out of 21" wording when partial download

## Fixtures

`tests/fixtures/m12205_matter_page.txt` — snapshot of body text from matter page (capture during first successful scrape).

`tests/fixtures/sample_request_email.txt` — assignment example email.

## Live scraper test

```bash
pytest tests/test_scraper_live.py -m live --headed
```

Mark as optional CI skip. Validates:

- Navigation to M12205
- Tab counts match expected ranges (not exact if site updates)
- At least 1 download from Other Documents with `--max 1`

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

### Step 2 — Parse only

```powershell
python -m regulatory_agent parse-email --file tests/fixtures/sample_request_email.txt
```

Verify structured output matches M12205 + Other Documents.

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
