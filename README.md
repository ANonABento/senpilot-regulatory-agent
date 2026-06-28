# Senpilot Regulatory Agent

An email-triggered agent that fetches utility regulatory filings from the
[Nova Scotia UARB Public Documents Database](https://uarb.novascotia.ca/fmi/webd/UARB15),
downloads up to 10 documents of a requested type, zips them, and replies by email
with the ZIP plus a summary of the matter's metadata and per-tab file counts.

Take-home for the **Senpilot Software Engineering Intern (F26 Challenge)**.

## Try it — email the live agent

The agent is deployed and polling its inbox. Email it and you'll get a reply with the documents.

- **To:** `kevins.senpilot.agent@gmail.com`
- **Body or subject:** e.g. *"Hi Agent, can you give me Other Documents files from M12205? Thanks!"*

It replies (typically within ~5–15 min — see [Deployment](#deployment)) with a ZIP of up to
10 documents from the requested tab, plus a summary like:

> M12205 is about Halifax Regional Water Commission - Windsor Street Exchange Redevelopment
> Project - $69,275,000. It relates to Water / Capital Expenditure Approvals. The matter had
> an initial filing on April 7, 2025 and a final filing on October 23, 2025. I found 13
> Exhibits, 5 Key Documents, 42 Other Documents, and no Transcripts or Recordings. I
> downloaded 10 out of the 42 Other Documents and am attaching them as a ZIP here.

Matter numbers look like `M12205`. Valid document types: **Exhibits, Key Documents,
Other Documents, Transcripts, Recordings**. Counts and metadata are scraped live, never hardcoded.

## How it works

```
your email ──▶ Gmail inbox ──▶ worker (GitHub Actions cron, every ~5 min)
                                 │  parse matter # + document type   (regex)
                                 │  scrape UARB                       (Playwright)
                                 │  download ≤10 docs → ZIP
                                 │  compose reply                     (template)
                                 └▶ reply via SMTP, ZIP attached, mark read
```

- **Scraping is deterministic** (Playwright) — an LLM never drives the browser. Reliability over autonomy.
- **Parsing and reply are deterministic too** (regex + template). The request shape (matter # +
  type) and the reply format are well-defined, so this is reliable, testable, and free.
  `agent/parse.py` + `agent/prompts.py` leave a clean seam to drop in an LLM for fuzzier
  natural language if it's ever worth it.

## Run it yourself

### Setup

```bash
git clone https://github.com/ANonABento/senpilot-regulatory-agent.git
cd senpilot-regulatory-agent
python -m venv .venv
source .venv/bin/activate          # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .
playwright install chromium
```

### Scrape from the CLI (no email or credentials needed)

```bash
python -m regulatory_agent scrape M12205 --type "Other Documents" --json
python -m regulatory_agent scrape M12205 --type "Other Documents" --max 3 --headed
```

Produces `output/M12205_other_documents.zip` and prints the structured result.

### Run the email worker locally

```bash
cp .env.example .env       # set GMAIL_ADDRESS + GMAIL_APP_PASSWORD (App Password, IMAP enabled)
python -m regulatory_agent worker --once     # one poll cycle
python -m regulatory_agent worker            # continuous (~replies in 1–2 min)
```

### Tests

```bash
pytest -m "not live"       # 34 unit tests, no network
pytest -m live             # live scrape of M12205 against UARB
```

## The scraper: the hard part

UARB is **FileMaker WebDirect** (a Vaadin app), which doesn't behave like a normal site:

- **No `Label: value` text.** The header renders labels and values as separately-positioned
  widgets, so the flat text has all labels in one cluster and all values in another. Metadata is
  recovered by **column geometry** — reading leaf-node screen coordinates and mapping each value
  to its column. (`scraper/metadata.py`)
- **Clicks don't download.** "GO GET IT" opens a Vaadin dialog that serves the file via
  `window.open`, which doesn't fire a Playwright download headlessly. The file's resource URL is
  pushed over the **websocket** — the scraper captures that frame and fetches the bytes directly
  with the session request context. (`scraper/download.py`)
- **Virtualized grid.** Only ~8 of 42 rows exist in the DOM at once; the scraper scrolls the
  Vaadin grid to materialize enough rows to reach 10.

Details: [docs/SCRAPER.md](./docs/SCRAPER.md) · [docs/SCRAPER_RECON_FINDINGS.md](./docs/SCRAPER_RECON_FINDINGS.md)

## Deployment

A [GitHub Actions workflow](./.github/workflows/agent.yml) runs the worker on a ~5-minute cron:
it polls the inbox, processes any request, and sends the reply. Gmail credentials live in
encrypted Actions secrets — never in the repo.

- **Transport:** plain **IMAP** (read) + **SMTP** (send) via a Gmail **App Password** — no OAuth
  consent screen and no token to expire, so it survives unattended.
- **Latency:** scheduled GitHub runs are rate-limited and can lag, so a reply may take ~5–15 min.
  A continuously-running worker replies in ~1–2 min (scrape time dominates).
- **Robustness:** unread messages stay unread until handled (crash-safe retry); the worker skips
  its own mail and automated `no-reply`/`mailer-daemon` senders so bounces can't loop.

## Design decisions

- **IMAP/SMTP + App Password over the Gmail API (OAuth).** No consent flow, no 7-day refresh-token
  expiry in "testing" status — far more robust for an always-on poller.
- **No LLM, by design.** Inputs and outputs are well-defined; a deterministic parser + template is
  reliable, fully unit-tested, and free. The code is structured so an LLM can be added exactly
  where it would help (ambiguous phrasing), not as a dependency for the happy path.
- **Stdlib email** (`imaplib` / `smtplib`) — zero email dependencies.

## Tech stack

Python 3.11 · Playwright (Chromium) · Typer · Pydantic / pydantic-settings · stdlib `imaplib`/`smtplib` · GitHub Actions

## Project structure

```
src/regulatory_agent/
  scraper/    Playwright automation: navigate, metadata, download, zip, service
  email/      gmail (IMAP/SMTP), reply templates, models, provider protocol
  agent/      request parser (regex), prompts/tools (LLM-ready seam)
  worker.py   poll → process → reply loop
  cli.py      scrape / worker / parse-email commands
docs/         specifications and scraper recon findings
tests/        34 unit tests + 1 live integration test
.github/      Actions cron workflow
```

## Documentation

| Doc | Contents |
|-----|----------|
| [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) | System design, data flow |
| [docs/SCRAPER.md](./docs/SCRAPER.md) · [docs/SCRAPER_RECON_FINDINGS.md](./docs/SCRAPER_RECON_FINDINGS.md) | Playwright spec + live findings |
| [docs/EMAIL.md](./docs/EMAIL.md) | Email integration |
| [docs/TESTING.md](./docs/TESTING.md) | Test & demo script |
| [docs/IMPLEMENTATION.md](./docs/IMPLEMENTATION.md) · [docs/ACCEPTANCE_CRITERIA.md](./docs/ACCEPTANCE_CRITERIA.md) | Plan & definition of done |

## License

Take-home submission for Senpilot — all rights reserved unless Senpilot specifies otherwise.
