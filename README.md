# Senpilot Regulatory Agent

Email-triggered AI agent that fetches utility regulatory filings from the [Nova Scotia UARB Public Documents Database](https://uarb.novascotia.ca/fmi/webd/UARB15), zips up to 10 documents, and replies by email with metadata and file counts.

Take-home project for **Senpilot Software Engineering Intern (F26 Challenge)**.

## Status

**Planning / scaffold phase.** Detailed specs live in [`docs/`](./docs/). Implementation follows phased plan in [docs/IMPLEMENTATION.md](./docs/IMPLEMENTATION.md).

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Playwright scraper + CLI | Not started |
| 2 | Email receive/send | Not started |
| 3 | LLM parse + reply | Not started |
| 4 | Demo + polish | Not started |

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

```powershell
git clone https://github.com/ANonABento/senpilot-regulatory-agent.git
cd senpilot-regulatory-agent
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
copy .env.example .env
# Fill in API keys — see docs/EMAIL.md and docs/AGENT.md
```

## Usage (once implemented)

```powershell
# Scrape locally (Phase 1)
python -m regulatory_agent scrape M12205 --type "Other Documents" --json

# Process one email poll cycle (Phase 2)
python -m regulatory_agent worker --once
```

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
