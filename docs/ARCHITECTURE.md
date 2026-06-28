# Architecture

## System context

Senpilot's Regulatory Agent platform needs a **data ingestion pipeline** that collects utility regulatory filings from public portals. This project implements the ingestion slice: email in → scrape → zip → email out.

## High-level diagram

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│ User email  │────▶│  Agent worker    │────▶│  Reply email    │
│ (request)   │     │                  │     │  + ZIP attach   │
└─────────────┘     │  ┌────────────┐  │     └─────────────────┘
                    │  │ LLM parse  │  │
                    │  └─────┬──────┘  │
                    │        ▼         │
                    │  ┌────────────┐  │
                    │  │  Scraper   │──┼──▶ UARB FileMaker WebDirect
                    │  │ (Playwright)│  │
                    │  └─────┬──────┘  │
                    │        ▼         │
                    │  ┌────────────┐  │
                    │  │ ZIP + meta │  │
                    │  └────────────┘  │
                    └──────────────────┘
```

## Module boundaries

| Layer | Responsibility | Must NOT do |
|-------|----------------|-------------|
| `cli.py` | Local dev entry, manual scrape | Business logic |
| `worker.py` | Poll email, dispatch jobs, error replies | DOM interaction |
| `agent/` | NL parsing, reply drafting | Direct browser control |
| `scraper/` | All UARB interaction | LLM calls |
| `email/` | Transport only | Scraping logic |

## Data models

### `DocumentType` (enum)

```
Exhibits | Key Documents | Other Documents | Transcripts | Recordings
```

Map user variants case-insensitively. Reject unknown types with a helpful error email.

### `MatterMetadata`

Fields scraped from the matter detail page header:

| Field | Example (M12205) |
|-------|------------------|
| `matter_number` | M12205 |
| `status` | Awaiting |
| `title_description` | Halifax Regional Water Commission - Windsor Street Exchange Redevelopment Project - $69,275,000 |
| `type_category` | Water / Capital Expenditure |
| `date_received` | 2025-04-07 |
| `date_final_submissions` | 2025-10-23 |
| `outcome` | (nullable) |

### `TabCounts`

Per-tab document counts from tab labels (e.g. `Exhibits - 13`):

```json
{
  "exhibits": 13,
  "key_documents": 5,
  "other_documents": 21,
  "transcripts": 0,
  "recordings": 0
}
```

### `ScrapeResult`

```json
{
  "matter_number": "M12205",
  "requested_document_type": "Other Documents",
  "metadata": { "...": "..." },
  "tab_counts": { "...": "..." },
  "downloaded_count": 10,
  "available_in_tab": 21,
  "zip_path": "output/M12205_other_documents.zip",
  "downloaded_files": ["doc1.pdf", "..."]
}
```

## Control flow

### CLI path (Phase 1)

```
cli scrape → scraper.service.scrape_matter → navigate → metadata → download → zip → stdout JSON
```

### Email worker path (Phase 2+)

```
worker.poll → agent.parse_request(email.body)
           → scraper.service.scrape_matter(...)
           → agent.compose_reply(scrape_result) OR reply.template(...)
           → email.send(outbound)
```

## Configuration

All config via `config.py` (Pydantic Settings):

- `UARB_BASE_URL`
- `MAX_DOWNLOADS` (default 10)
- `DOWNLOAD_DIR`, `OUTPUT_DIR`
- Playwright timeouts
- Email + LLM credentials

## Error handling strategy

| Failure | User-facing behavior |
|---------|---------------------|
| Invalid matter format | Error email: expected `M#####` |
| Matter not found | Error email after search yields no detail page |
| Unknown document type | Error email listing valid types |
| Tab empty | Reply with counts, no attachment, explain zero downloads |
| Scrape timeout | Error email, log stack trace |
| Send failure | Retry once; log permanently |

## Design decisions

1. **Playwright over raw HTTP** — UARB is FileMaker WebDirect; no stable public API.
2. **LLM for language, not navigation** — Reliability beats "autonomous browsing."
3. **Gmail first** — Simplest for take-home demo; abstract behind `EmailProvider`.
4. **Sync Playwright in worker** — Acceptable for intern scope; async refactor optional.

## Future improvements (out of scope)

- Persistent job queue (Redis/SQS)
- Idempotency keys per email Message-ID
- Direct FileMaker API if credentials available
- Full observability (OpenTelemetry)
