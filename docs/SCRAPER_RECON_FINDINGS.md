# Scraper Recon Findings (live M12205, 2026-06-28)

Captured from `output/recon/` during live investigation. These are **blockers /
corrections** for the Phase 1 scraper. Author: agent working Phase 2/3 — handed
off so the Phase 1 agent doesn't have to re-derive them.

## 1. Header metadata regexes match NOTHING on the live page ⚠️

`metadata.py` anchors on `Label: value` (e.g. `Matter No:\s*(M\d{5})`). The live
page (`output/recon/matter_body.txt`) is **value-block first, label-block last**,
with no colons:

```
Exhibits - 13
Key Documents - 5
Other Documents - 42
Transcripts - 0
Recordings - 0
Hearings
Related Matters
M12205                ← matter number (value)

Capital Expenditure Approvals   ← Type

Awaiting Compliance             ← Status

Halifax Regional Water Commission - Windsor Street Exchange ... - $69,275,000  ← Title

04/07/2025                      ← Date Received
10/23/2025                      ← Decision Date
Water                           ← Category
...
Matter No                       ← labels start here, detached from values
Status
Title - Description
Type
Category
Date Received
Decision Date
Outcome
```

Verified: all seven header regexes (`MATTER_NO`, `STATUS`, `TITLE_DESCRIPTION`,
`TYPE_CATEGORY`, `DATE_RECEIVED`, `DATE_FINAL_SUBMISSIONS`, `OUTCOME`) return
**no match**. `test_metadata.py` passes only because its `SAMPLE_BODY` is
hand-written to fit the regex — it does not reflect reality.

**Fix options:**
- Prefer **per-field DOM extraction** over body-text regex: each value sits in its
  own FileMaker field element; locate by the label or by stable field geometry.
- Or parse positionally from `inner_text`: matter number = first `M\d{5}`; the
  `MM/DD/YYYY` dates in order are Date Received then Decision Date; Title is the
  line containing `-` and `$`. Brittle but workable for the demo.
- Capture the real body into `tests/fixtures/m12205_matter_page.txt` and rewrite
  `test_metadata.py` to assert against it (replace the synthetic `SAMPLE_BODY`).

**Label naming:** the live field is **`Decision Date`**, not "Date Final
Submissions" (the model field `date_final_submissions` maps to it), and
**`Category`** is separate from **`Type`** (values: Type=`Capital Expenditure
Approvals`, Category=`Water`). The docs' `Type / Category` is a single combined
field only in the PDF screenshot.

## 2. Count drift: Other Documents is 42, not 21

Live tab counts: Exhibits 13, Key Documents 5, **Other Documents 42**,
Transcripts 0, Recordings 0. `test_scraper_live.py` asserts `21` /
`available_in_tab == 21` and will fail. Relax those asserts to ranges, or update
to 42. (Reply/template code does not hardcode this — good.)

## 3. Download blocker: GO GET IT click produces nothing ⚠️⚠️

`output/recon/download_findings.json`: clicking GO GET IT via normal click,
double click, and mouse sequence all yield `NO_DOWNLOAD (TimeoutError)` with
**no network request, no popup, no new page**. So `download._wait_for_download`'s
expect_download / expect_popup / fetch fallbacks will all time out as-is.

**Investigate:** does the click need a preceding row-select? Is the file
delivered via an iframe, a same-tab blob, or a FileMaker server push that
Playwright's download API misses? Inspect `v-grid` row handlers; try
`page.on("download")` registered before any click; watch `requestfinished`.

## 4. Virtualized grid renders only 8 rows

The document list is a **virtualized Vaadin grid** (`v-grid-body` +
`v-grid-scroller-vertical`, `scrollHeight 544 > clientHeight`). Only ~8 GO GET IT
buttons exist in the DOM at once regardless of the 42 available
(`count_after_wheel/end-key/scroll-into-view = 8`). `download_documents`'
`min(buttons.count(), max_count)` therefore caps at 8 and **cannot reach 10**.

**Fix:** scroll the grid scroller (not the window) to materialize more rows,
collecting downloads incrementally as rows render, until `max_count` is reached
or the scroller bottoms out. The recon's wheel/End-key attempts did not move it —
target `.v-grid-scroller-vertical` directly or set `scrollTop`.

## Net assessment

Navigation + tab-count extraction are sound. The remaining Phase 1 work is real:
(a) a working download mechanism, (b) grid virtualization scrolling, (c) a
metadata extractor that matches the live DOM. (a) and (b) are the recon's current
focus — correct priority. (c) is the silent one: tests are green but live
extraction returns nulls.
