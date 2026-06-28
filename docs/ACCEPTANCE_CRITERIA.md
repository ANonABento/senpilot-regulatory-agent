# Acceptance Criteria

Mapped directly to the Senpilot F26 Challenge PDF.

## Phase 1 — Scraper CLI

| # | Criterion | Verify |
|---|-----------|--------|
| 1.1 | Navigate to UARB15 URL | Log shows correct URL after load |
| 1.2 | Search matter via "Go Directly to Matter" | M12205 detail page loads |
| 1.3 | Select document type tab | Other Documents tab active |
| 1.4 | Download up to 10 via GO GET IT | 10 files saved for M12205 Other Documents |
| 1.5 | Create ZIP of downloads | Single `.zip` with all downloaded files |
| 1.6 | Extract matter metadata | Title, type/category, dates present in JSON |
| 1.7 | Extract all tab counts | 13 / 5 / 21 / 0 / 0 for M12205 |

## Phase 2 — Email

| # | Criterion | Verify |
|---|-----------|--------|
| 2.1 | Receive user email | Worker picks up unread message |
| 2.2 | Parse matter + doc type from NL email | Assignment example email works |
| 2.3 | Send reply to original sender | `To` matches requester |
| 2.4 | Attach ZIP | MIME attachment present, opens correctly |
| 2.5 | Reply includes total counts per tab | All five categories mentioned |
| 2.6 | Reply includes metadata summary | Title, category, filing dates |
| 2.7 | Reply states downloaded vs available | e.g. "10 out of 21 Other Documents" |

## Phase 3 — AI agent

| # | Criterion | Verify |
|---|-----------|--------|
| 3.1 | Handles paraphrased requests | Non-template email still works |
| 3.2 | Graceful errors for bad input | Helpful error email, no crash |
| 3.3 | Reply reads naturally | Similar tone to PDF example |

## Submission quality (recommended)

| # | Criterion | Verify |
|---|-----------|--------|
| S.1 | README with setup + demo | Reviewer can run locally |
| S.2 | Clean GitHub history | Logical commits by phase |
| S.3 | `.env.example` documents all vars | No mystery config |
| S.4 | Edge cases documented | README or docs/ |

## Reference example (from PDF)

**Input email:**

> Hi Agent, Can you give me Other Documents files from M12205? Thanks!

**Expected reply content (paraphrase allowed, facts must match):**

> M12205 is about the Halifax Regional Water Commission - Windsor Street Exchange Redevelopment Project - $69,270,000. It relates to Capital Expenditure within the Water category. Initial filing April 7, 2025; final filing October 23, 2025. Counts: 13 Exhibits, 5 Key Documents, 21 Other Documents, no Transcripts or Recordings. Downloaded 10 of 21 Other Documents, ZIP attached.

Note: Dollar amount may vary slightly on live site ($69,275,000 in screenshot) — use **live scraped values**, not hardcoded PDF text.

## Definition of done

Project is **submission-ready** when Phase 1 + Phase 2 criteria pass and at least one paraphrased email succeeds (Phase 3.1).
