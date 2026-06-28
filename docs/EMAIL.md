# Email Integration Specification

## Requirements (from assignment)

1. User **emails** the agent with matter number + document type (natural language OK)
2. Agent **replies by email** with:
   - ZIP attachment
   - Total file counts for all tabs on that matter
   - Metadata summary (title, category, dates, etc.)

## Recommended approach: Gmail API

Best balance for a take-home: OAuth to a dedicated Gmail account, poll inbox, send replies.

### Setup steps (document in README)

1. Create Google Cloud project
2. Enable Gmail API
3. Create OAuth 2.0 Desktop credentials
4. Run one-time auth script → store `GMAIL_REFRESH_TOKEN` in `.env`
5. Use dedicated inbox (e.g. `regulatory-agent-demo@gmail.com`)

### Scopes

```
https://www.googleapis.com/auth/gmail.modify
```

(`modify` allows mark-as-read after processing)

## Module: `email/provider.py`

```python
class EmailProvider(Protocol):
    def poll_unread(self) -> list[InboundEmail]: ...
    def send(self, message: OutboundEmail) -> None: ...
    def mark_processed(self, message_id: str) -> None: ...
```

## Module: `email/models.py`

```python
@dataclass
class InboundEmail:
    message_id: str
    thread_id: str
    sender: str
    subject: str
    body_text: str
    received_at: datetime

@dataclass
class OutboundEmail:
    to: str
    subject: str
    body_text: str
    attachment_path: Path | None
    in_reply_to: str | None  # for threading
```

## Module: `email/gmail.py`

### Polling

- Query: `label:INBOX is:unread`
- Fetch `format=full`, extract plain text body (handle multipart)
- Skip emails from self (avoid loops)

### Sending with attachment

- Build `multipart/mixed` MIME
- Attach ZIP as `application/zip`
- Set `In-Reply-To` and `References` headers for threading
- Subject: `Re: {original subject}` or `Documents for {matter} - {doc type}`

### Mark processed

- Remove `UNREAD` label
- Optional: add `PROCESSED` user label

## Module: `email/reply.py`

### Success template

Use assignment example as gold standard:

```
Hi {user_name},

{matter_number} is about {title_description}. It relates to {type_category}.

The matter had an initial filing on {date_received} and a final filing on {date_final_submissions}.

I found {exhibits} Exhibits, {key_documents} Key Documents, {other_documents} Other Documents,
{transcripts_text} Transcripts, and {recordings_text} Recordings.

I downloaded {downloaded_count} out of the {available_in_tab} {document_type} and am attaching them as a ZIP here.
```

Handle zero counts: "no Transcripts or Recordings" (assignment wording).

### Error template

```
Hi,

I couldn't process your request: {reason}

Please send a matter number (e.g. M12205) and one of: Exhibits, Key Documents, Other Documents, Transcripts, Recordings.
```

## Worker loop (`worker.py`)

```python
while True:
    for email in provider.poll_unread():
        try:
            request = parse_request(email.body_text)
            result = scrape_matter(request.matter, request.document_type)
            body = compose_reply(result, email.sender)
            provider.send(OutboundEmail(..., attachment_path=result.zip_path))
        except AgentError as e:
            provider.send(error_reply(email, str(e)))
        finally:
            provider.mark_processed(email.message_id)
    sleep(POLL_INTERVAL_SEC)
```

`POLL_INTERVAL_SEC`: 30–60 for demo; configurable.

## Alternative: SendGrid Inbound Parse

If Gmail OAuth is painful:

- Inbound Parse webhook → FastAPI endpoint
- Requires public URL (ngrok for local dev)
- More moving parts; only use if Gmail blocked

## Security notes

- Never commit `.env` or OAuth tokens
- Validate sender allowlist optional for demo
- Sanitize attachment filenames
- Max attachment size: Gmail ~25MB; warn if ZIP exceeds 20MB

## Testing without full OAuth

Phase 1 bypass:

```python
# tests/manual_email_fixture.py
SAMPLE_REQUEST = """Hi Agent,
Can you give me Other Documents files from M12205?
Thanks!"""
```

Pipe fixture through `parse_request` + `scrape_matter` + print reply body (no send).

## Demo script for submission

1. Send email to agent inbox from personal account
2. Wait for poll cycle (or run worker once)
3. Verify reply received with ZIP
4. Open ZIP — confirm PDF count matches body text
