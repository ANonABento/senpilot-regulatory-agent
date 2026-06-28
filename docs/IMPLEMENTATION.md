# Implementation Plan

## Assignment summary

Build an **email-triggered AI agent** that:

1. Parses a user's email for a **matter number** (`M#####`) and **document type**
2. Scrapes the [UARB Public Documents Database](https://uarb.novascotia.ca/fmi/webd/UARB15)
3. Downloads up to **10** documents from the requested tab
4. Zips downloads and **replies by email** with attachment + metadata summary + per-tab file counts

Reference matter for development and demo: **`M12205`**, document type **`Other Documents`**.

---

## Implementation phases

Implement in this order. Do **not** start with email — the scraper is the highest-risk component.

### Phase 0 — Repo bootstrap (done)

- [x] GitHub repo with docs and scaffold
- [ ] Python venv + `pip install -r requirements.txt`
- [ ] `playwright install chromium`
- [ ] Copy `.env.example` → `.env`

### Phase 1 — Core scraper (CLI)

**Goal:** `python -m regulatory_agent scrape M12205 --type "Other Documents"` produces a ZIP + JSON metadata.

| Task | Module | Notes |
|------|--------|-------|
| Config & paths | `src/regulatory_agent/config.py` | Pydantic settings from env |
| Domain models | `src/regulatory_agent/models.py` | `MatterMetadata`, `DocumentType`, `ScrapeResult` |
| Browser session | `src/regulatory_agent/scraper/browser.py` | Playwright lifecycle, glass-pane waits |
| Matter navigation | `src/regulatory_agent/scraper/navigate.py` | Search by matter number |
| Metadata extraction | `src/regulatory_agent/scraper/metadata.py` | Title, type/category, dates, tab counts |
| Tab + download | `src/regulatory_agent/scraper/download.py` | Select tab, click GO GET IT (max 10) |
| ZIP builder | `src/regulatory_agent/scraper/zipper.py` | Stable filenames inside archive |
| Orchestrator | `src/regulatory_agent/scraper/service.py` | `scrape_matter(matter, doc_type) -> ScrapeResult` |
| CLI | `src/regulatory_agent/cli.py` | Typer commands for local testing |

**Exit criteria:** See [ACCEPTANCE_CRITERIA.md](./ACCEPTANCE_CRITERIA.md) Phase 1.

**Estimated effort:** 4–8 hours.

### Phase 2 — Email integration

**Goal:** Agent inbox receives request email → triggers scrape → sends reply with ZIP.

| Task | Module | Notes |
|------|--------|-------|
| Email models | `src/regulatory_agent/email/models.py` | `InboundEmail`, `OutboundEmail` |
| Provider abstraction | `src/regulatory_agent/email/provider.py` | Protocol: poll/send |
| Gmail implementation | `src/regulatory_agent/email/gmail.py` | OAuth + poll + send with attachment |
| Reply builder | `src/regulatory_agent/email/reply.py` | Subject, body template, attach ZIP |
| Worker loop | `src/regulatory_agent/worker.py` | Poll → process → mark read |

**Exit criteria:** See [ACCEPTANCE_CRITERIA.md](./ACCEPTANCE_CRITERIA.md) Phase 2.

**Estimated effort:** 2–4 hours.

### Phase 3 — AI agent layer

**Goal:** Natural-language email parsing + polished reply prose via tool-calling agent.

| Task | Module | Notes |
|------|--------|-------|
| Tool definitions | `src/regulatory_agent/agent/tools.py` | Structured functions exposed to LLM |
| Prompts | `src/regulatory_agent/agent/prompts.py` | System + extraction + reply templates |
| Agent loop | `src/regulatory_agent/agent/runner.py` | Parse email OR orchestrate full pipeline |
| Request parser fallback | `src/regulatory_agent/agent/parse.py` | Regex fast-path before LLM |

**Exit criteria:** See [ACCEPTANCE_CRITERIA.md](./ACCEPTANCE_CRITERIA.md) Phase 3.

**Estimated effort:** 2–3 hours.

### Phase 4 — Polish & submission

| Task | Notes |
|------|-------|
| README demo section | Screen recording or step-by-step email test |
| Error emails | Invalid matter, zero docs, scrape timeout |
| Logging | Structured logs for demo debugging |
| Optional deploy | Render/Railway cron or always-on worker |
| Final review | Run manual demo script in [TESTING.md](./TESTING.md) |

**Estimated effort:** 2–3 hours.

---

## Repository layout (target)

```
senpilot-regulatory-agent/
├── AGENTS.md                 # Handoff notes for implementation agents
├── README.md
├── docs/                     # Specs (you are here)
├── src/regulatory_agent/
│   ├── __init__.py
│   ├── __main__.py           # python -m regulatory_agent
│   ├── cli.py
│   ├── config.py
│   ├── models.py
│   ├── worker.py
│   ├── scraper/
│   │   ├── browser.py
│   │   ├── navigate.py
│   │   ├── metadata.py
│   │   ├── download.py
│   │   ├── zipper.py
│   │   └── service.py
│   ├── email/
│   │   ├── models.py
│   │   ├── provider.py
│   │   ├── gmail.py
│   │   └── reply.py
│   └── agent/
│       ├── tools.py
│       ├── prompts.py
│       ├── parse.py
│       └── runner.py
├── tests/
│   ├── test_parse.py
│   ├── test_models.py
│   └── fixtures/
├── requirements.txt
└── .env.example
```

---

## Key technical risks

| Risk | Mitigation |
|------|------------|
| FileMaker WebDirect slow / blocking overlays | Wait for `.iwp-glass-pane` hidden; generous timeouts; retry clicks |
| Non-standard inputs | Click placeholder text (`eg M01234`), type via keyboard |
| Download handling | Playwright `page.expect_download()` per GO GET IT click |
| Large attachments | Cap at 10 files; note size in README |
| LLM misparsing matter/type | Regex validation + structured output schema |

---

## Environment setup (implementer)

```powershell
cd senpilot-regulatory-agent
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
copy .env.example .env
# Edit .env with API keys
python -m regulatory_agent scrape M12205 --type "Other Documents"
```

---

## Handoff for smarter implementation model

When resuming implementation:

1. Read [AGENTS.md](../AGENTS.md) at repo root
2. Confirm Phase 1 exit criteria before moving to Phase 2
3. Use `M12205` + `Other Documents` as the primary integration test case
4. Keep scraping **deterministic** (Playwright); use LLM only for parse + reply prose
5. Do not refactor docs unless requirements change
