# Senpilot Regulatory Agent

Email-triggered AI agent that fetches utility regulatory filings from the [Nova Scotia UARB Public Documents Database](https://uarb.novascotia.ca/fmi/webd/UARB15), zips up to 10 documents, and replies by email with metadata and file counts.

Take-home project for **Senpilot Software Engineering Intern (F26 Challenge)**.

## Status

**Phase 1 done & live-validated; email + agent layers pending.** Detailed specs live in [`docs/`](./docs/). Implementation follows phased plan in [docs/IMPLEMENTATION.md](./docs/IMPLEMENTATION.md).

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Playwright scraper + CLI | **Done** — live scrape of M12205 validated end-to-end |
| 2 | Email receive/send | Stubs only |
| 3 | LLM parse + reply | Stubs only |
| 4 | Demo + polish | Not started |

> Phase 1 is validated against the live UARB site (`pytest -m live` passes): navigation, tab counts (13/5/42/0/0), header metadata via column-geometry extraction, 10 PDFs pulled from a virtualized Vaadin grid, and a single ZIP. Downloads capture each file's resource URL from FileMaker WebDirect's websocket and fetch it directly (the GO GET IT dialog's `window.open` download does not fire headlessly). Other Documents is now **42** live (was 21 in the spec) — counts are read live, never hardcoded.

## What it does (target behavior)

1. User emails: *"Can you give me Other Documents files from M12205?"*
2. Agent parses matter number + document type
3. Agent scrapes UARB, downloads up to 10 files, zips them
4. Agent replies with ZIP attached + matter metadata + counts for all document tabs

## Documentation

| Doc | Contents |
|-----|----------|
| [docs/IMPLEMENTATION.md](./docs/IMPLEMENTATION.md) | Master plan & milestones |
| [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) | System design |
| [docs/SCRAPER.md](./docs/SCRAPER.md) | Playwright spec |
| [docs/EMAIL.md](./docs/EMAIL.md) | Gmail integration |
| [docs/AGENT.md](./docs/AGENT.md) | LLM agent layer |
| [docs/TESTING.md](./docs/TESTING.md) | Test & demo script |
| [docs/ACCEPTANCE_CRITERIA.md](./docs/ACCEPTANCE_CRITERIA.md) | Definition of done |
| [AGENTS.md](./AGENTS.md) | Handoff notes for coding agents |

## Setup (for implementers)

```bash
git clone https://github.com/ANonABento/senpilot-regulatory-agent.git
cd senpilot-regulatory-agent
python -m venv .venv
source .venv/bin/activate        # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
cp .env.example .env             # Windows: copy .env.example .env
# Fill in API keys — see docs/EMAIL.md and docs/AGENT.md
```

## Usage

```bash
# Scrape locally (Phase 1 — implemented)
python -m regulatory_agent scrape M12205 --type "Other Documents" --json
python -m regulatory_agent scrape M12205 --type "Other Documents" --max 3 --headed

# Phase 2/3 — not yet implemented (commands exit 2)
python -m regulatory_agent worker --once
python -m regulatory_agent parse-email --file tests/fixtures/sample_request_email.txt
```

Run unit tests (no network): `pytest -m "not live"`. Live scrape test: `pytest -m live`.

## Tech stack

- Python 3.11+
- Playwright (FileMaker WebDirect automation)
- Gmail API (email)
- OpenAI or Anthropic (parse + reply)
- Typer (CLI)

## Project structure

```
src/regulatory_agent/   # Application code (stubs → implementation)
docs/                   # Implementation specifications
tests/                  # Unit + live integration tests
```

## License

Private take-home submission — all rights reserved unless Senpilot specifies otherwise.
