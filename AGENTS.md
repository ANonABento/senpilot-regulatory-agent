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
| 0 — Repo bootstrap | **Done** | Docs + scaffold only, no working scraper yet |
| 1 — Scraper CLI | **Not started** | Highest priority |
| 2 — Email | Not started | Blocked on Phase 1 |
| 3 — AI agent | Not started | Blocked on Phase 1–2 |
| 4 — Polish | Not started | |

## Hard constraints

- **Scraping = Playwright only.** Do not use LLM for browser navigation.
- **Max 10 downloads** per request (configurable via `MAX_DOWNLOADS`).
- **Reply must include** all tab counts, metadata, and downloaded/available ratio.
- **Use live scraped data** — do not hardcode M12205 metadata from the PDF.

## Known technical context (from recon)

- Site: FileMaker WebDirect at `https://uarb.novascotia.ca/fmi/webd/UARB15`
- Loading overlays: `.iwp-glass-pane` blocks clicks until hidden
- Matter search: click `eg M01234` placeholder, type matter, click last `Search` button
- Downloads: `GO GET IT` buttons on each row in document tabs

## Suggested first PR / commit sequence

1. `config.py`, `models.py`, stub CLI
2. `browser.py` + `navigate.py` — matter page loads for M12205
3. `metadata.py` — tab counts + header fields
4. `download.py` + `zipper.py` — 10 PDFs zipped
5. `service.py` + CLI `scrape` command end-to-end
6. Unit tests for parse/reply
7. Gmail provider + worker
8. LLM parse + reply polish

## Commands (once implemented)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
copy .env.example .env

# Phase 1
python -m regulatory_agent scrape M12205 --type "Other Documents" --json

# Phase 2
python -m regulatory_agent worker --once

# Tests
pytest tests/ -m "not live"
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
