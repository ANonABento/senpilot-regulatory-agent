# Agent Handoff Guide

This repo is **spec-first**. Implementation should follow docs in order.

## Quick start for implementation agents

1. Read [docs/IMPLEMENTATION.md](./docs/IMPLEMENTATION.md) — phase order is mandatory
2. Read [docs/SCRAPER.md](./docs/SCRAPER.md) before writing any Playwright code
3. Use **M12205** + **Other Documents** as the primary test case
4. Check [docs/ACCEPTANCE_CRITERIA.md](./docs/ACCEPTANCE_CRITERIA.md) before marking a phase complete

## Current status

| Phase | Status | Notes |
|-------|--------|-------|
| 0 — Repo bootstrap | **Done** | Docs + scaffold |
| 1 — Scraper CLI | **Done** | Live scrape of M12205 validated end-to-end; `pytest -m live` passes; fixture captured |
| 2 — Email | Not started | 3-line stubs under `email/`; unblocked — Phase 1 is validated |
| 3 — AI agent | Not started | 3-line stubs under `agent/`; blocked on Phase 2 |
| 4 — Polish | Not started | |

**Phase 1 live findings (FileMaker WebDirect / Vaadin):**
- `.iwp-glass-pane` is per-widget chrome, **not** a loading overlay — waiting for it to hide hangs 60 s. Wait on `.v-loading-indicator` instead (`scraper/browser.py`).
- Header has no `Label: value` text; values and labels are separately positioned. Metadata is extracted by **column geometry** from leaf-node coordinates (`scraper/metadata.py`).
- **GO GET IT** opens a Vaadin "Download Files" modal and serves the file via `window.open`, which does not fire headlessly. The file's resource URL (`APP/connector/.../dl/<doc>.pdf`) is pushed over the **websocket** — capture it and fetch directly with the session request context (`scraper/download.py`, `capture_ws_frames`).
- The document list is a **virtualized Vaadin grid** (8 rows rendered); scroll `v-grid-scroller-vertical` to reach 10. Verify fetched bytes against `Content-Length` (slow responses truncate).
- Other Documents count is **42** live, not 21 — `test_scraper_live.py` asserts invariants, not the exact number.

## Hard constraints

- **Scraping = Playwright only.** Do not use LLM for browser navigation.
- **Max 10 downloads** per request (configurable via `MAX_DOWNLOADS`).
- **Reply must include** all tab counts, metadata, and downloaded/available ratio.
- **Use live scraped data** — do not hardcode M12205 metadata from the PDF.

## Known technical context (from recon)

- Site: FileMaker WebDirect at `https://uarb.novascotia.ca/fmi/webd/UARB15`
- Loading overlays: `.iwp-glass-pane` blocks clicks until hidden
- Matter input: `.fm-textarea` containing the `eg M01234` placeholder; backspace-clear then `keyboard.type` (see `navigate._fill_matter_number`)
- Matter search: among `button:has-text("Search")`, pick the one in the y≈300–450 band (the "Go Directly to Matter" search, not advanced search) — see `navigate._click_direct_matter_search`. **This y-coordinate heuristic is viewport-dependent; revisit if it breaks.**
- Downloads: `GO GET IT` buttons; `download._wait_for_download` handles direct download, existing/new popup, and PDF-fetch-via-request fallbacks

## Commit sequence

Phase 1 (done): `config.py`, `models.py`, `browser.py`, `navigate.py`, `metadata.py`, `download.py`, `zipper.py`, `service.py`, CLI `scrape`, unit tests. Recon scripts live under `scripts/` (`debug_navigate`, `debug_matter_input`, `debug_search_buttons`, `debug_download`) — they validated the selectors now used in `navigate.py`/`download.py`.

Remaining:

1. Validate live scrape end-to-end (M12205) + capture body-text fixture
2. Gmail provider + worker (Phase 2)
3. LLM parse + reply polish (Phase 3)

## Commands (once implemented)

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
cp .env.example .env             # Windows: copy .env.example .env

# Phase 1 (implemented)
python -m regulatory_agent scrape M12205 --type "Other Documents" --json

# Phase 2 (stub — exits 2)
python -m regulatory_agent worker --once

# Tests
pytest tests/ -m "not live"      # unit; live: pytest -m live
```

## Files you may modify freely

- Everything under `src/regulatory_agent/`
- `tests/`
- `README.md` (add demo results section)

## Files to treat as spec (change only if requirements change)

- `docs/*.md`
- This file's "Known technical context" after recon is validated

## Out of scope unless user asks

- Deployment infrastructure
- Database persistence
- Multi-tenant auth
- Non-Gmail email providers (SendGrid stub OK)

## Assignment source

PDFs saved locally by candidate:

`Downloads/Senpilot – Software Engineering Intern – Next Steps/2026-06-22 - Senpilot Software Engineering Intern - F26 Challenge (1)-*.pdf`

## Questions to ask user if blocked

1. Submission deadline and delivery method (GitHub link? email?)
2. Preferred LLM provider (OpenAI vs Anthropic)
3. Gmail account available for OAuth demo?
4. Public vs private GitHub repo?
