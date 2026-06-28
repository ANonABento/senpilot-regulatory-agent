"""Sanity check for LLM tool schemas (static contract for a future agentic loop)."""

from regulatory_agent.agent.tools import TOOL_SCHEMAS
from regulatory_agent.models import DocumentType


def test_tool_schemas_are_valid_and_doc_types_in_sync() -> None:
    names = [t["name"] for t in TOOL_SCHEMAS]
    assert names == ["parse_email", "scrape_documents", "format_reply"]
    for tool in TOOL_SCHEMAS:
        schema = tool["input_schema"]
        assert tool["description"]
        assert schema["type"] == "object"
        for field in schema["required"]:
            assert field in schema["properties"]
    scrape = next(t for t in TOOL_SCHEMAS if t["name"] == "scrape_documents")
    assert scrape["input_schema"]["properties"]["document_type"]["enum"] == [
        dt.value for dt in DocumentType
    ]
