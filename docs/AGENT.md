# AI Agent Specification

Senpilot expects an **AI agent**, not just a cron script. The LLM should handle ambiguous language; scraping stays deterministic.

## Agent responsibilities

| Task | LLM? | Fallback |
|------|------|----------|
| Extract matter number from email | Yes | Regex `\bM\d{5}\b` |
| Extract document type | Yes | Keyword map |
| Compose reply prose | Yes (optional) | Template in `email/reply.py` |
| Navigate UARB website | **No** | Playwright only |
| Decide download count cap | **No** | Config `MAX_DOWNLOADS=10` |

## Module: `agent/parse.py`

### Fast path (regex)

```python
MATTER_RE = re.compile(r"\b(M\d{5})\b", re.I)

DOC_TYPE_ALIASES = {
    "exhibit": DocumentType.EXHIBITS,
    "key document": DocumentType.KEY_DOCUMENTS,
    "other document": DocumentType.OTHER_DOCUMENTS,
    "transcript": DocumentType.TRANSCRIPTS,
    "recording": DocumentType.RECORDINGS,
}
```

If both matter and type found with high confidence → skip LLM.

### LLM path

Structured output schema:

```json
{
  "matter_number": "M12205",
  "document_type": "Other Documents",
  "confidence": "high",
  "user_name": "User"
}
```

Prompt instructions:

- Matter numbers always `M` + exactly 5 digits
- Document type must be one of the five allowed values
- If missing fields → return nulls + `error_reason`

Use OpenAI `response_format` JSON schema or Anthropic tool use.

## Module: `agent/tools.py`

Tools exposed to agent (for full agentic demo / future extension):

| Tool | Description |
|------|-------------|
| `parse_email(body: str)` | Extract request fields |
| `scrape_documents(matter, doc_type)` | Runs scraper service |
| `format_reply(result)` | Returns email body string |

For minimal scope, `runner.py` can call these as Python functions without a multi-turn loop.

## Module: `agent/prompts.py`

### System prompt (sketch)

```
You are a regulatory document retrieval agent for Senpilot.
You help users fetch public utility filing documents from the Nova Scotia UARB portal.
You never invent matter numbers or document counts — only use tool results.
When document types are ambiguous, prefer the closest exact match from:
Exhibits, Key Documents, Other Documents, Transcripts, Recordings.
```

### Reply drafting prompt

Input: `ScrapeResult` JSON + original user tone.

Output: Plain-text email body matching assignment example style (professional, concise, factual).

## Module: `agent/runner.py`

### `process_email(email: InboundEmail) -> OutboundEmail`

```
1. request = parse_request(email.body_text)  # parse.py with LLM fallback
2. result = scrape_matter(request.matter_number, request.document_type)
3. body = compose_reply_with_llm(result) OR template_reply(result)
4. return OutboundEmail(to=email.sender, body=body, attachment=result.zip_path, ...)
```

### Optional: full agent loop

For extra polish, use tool-calling loop:

```
while not done:
    model chooses tool → execute → append result → continue
```

Cap at 5 turns. Overkill for take-home unless time permits.

## Model selection

| Provider | Model suggestion | Use |
|----------|------------------|-----|
| OpenAI | gpt-4o-mini | Parse + reply (cheap, fast) |
| Anthropic | claude-sonnet-4 | Parse + reply (higher quality prose) |

Configure via env: `LLM_PROVIDER=openai|anthropic`, `LLM_MODEL=...`

## Cost control

- Parse calls: ~500 tokens/email
- Reply calls: ~800 tokens/email
- Disable LLM reply → template only for zero API cost demo

## What NOT to do

- Do not let LLM click browser or generate URLs
- Do not hallucinate tab counts — always from scraper
- Do not skip ZIP when downloads succeeded

## Example inputs to test parsing

```
"Other Documents files from M12205 please"
"Can you pull exhibits for matter M12383?"
"Get me transcripts for M12205"  # expect 0 downloads but valid reply
"Hello"  # expect error reply
"m12205 other docs"  # should normalize case
```
