"""LLM tool definitions (Anthropic tool-use schema). See docs/AGENT.md.

These describe the agent's capabilities for an optional tool-calling loop. The
deterministic path (agent/runner.process_email) calls the same underlying
functions directly and is what ships today; these schemas exist so a future
agentic loop can expose them to a model without re-deriving the contract.
"""

from __future__ import annotations

from regulatory_agent.models import DocumentType

_DOC_TYPE_VALUES = [dt.value for dt in DocumentType]

TOOL_SCHEMAS: list[dict] = [
    {
        "name": "parse_email",
        "description": "Extract the matter number and document type from a user's email body.",
        "input_schema": {
            "type": "object",
            "properties": {
                "body": {"type": "string", "description": "Raw plain-text email body."}
            },
            "required": ["body"],
        },
    },
    {
        "name": "scrape_documents",
        "description": "Download documents for a matter/type from the UARB portal and zip them.",
        "input_schema": {
            "type": "object",
            "properties": {
                "matter_number": {"type": "string", "pattern": r"^M\d{5}$"},
                "document_type": {"type": "string", "enum": _DOC_TYPE_VALUES},
            },
            "required": ["matter_number", "document_type"],
        },
    },
    {
        "name": "format_reply",
        "description": "Render a scrape result as a plain-text email body for the user.",
        "input_schema": {
            "type": "object",
            "properties": {
                "scrape_result": {"type": "object", "description": "A ScrapeResult JSON object."}
            },
            "required": ["scrape_result"],
        },
    },
]

TOOL_NAMES = [t["name"] for t in TOOL_SCHEMAS]
