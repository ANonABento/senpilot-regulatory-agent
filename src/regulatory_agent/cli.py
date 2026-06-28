"""Typer CLI — local dev entry points."""

from __future__ import annotations

import json

import typer
from rich.console import Console

from regulatory_agent.models import DocumentType

app = typer.Typer(help="Senpilot regulatory document agent")
console = Console()


@app.command()
def scrape(
    matter_number: str = typer.Argument(..., help="Matter number, e.g. M12205"),
    doc_type: str = typer.Option(..., "--type", help="Document type tab to download from"),
    max_downloads: int | None = typer.Option(None, "--max", help="Override MAX_DOWNLOADS"),
    as_json: bool = typer.Option(False, "--json", help="Print ScrapeResult as JSON"),
    headed: bool = typer.Option(False, "--headed", help="Run browser in headed mode"),
) -> None:
    """Scrape UARB and produce a ZIP (Phase 1)."""
    document_type = DocumentType.from_user_text(doc_type)
    if document_type is None:
        console.print(f"[red]Unknown document type:[/red] {doc_type}")
        raise typer.Exit(code=1)

    # TODO(phase-1): wire scraper.service.scrape_matter
    console.print(
        "[yellow]Not implemented yet.[/yellow] "
        f"Would scrape {matter_number} / {document_type.value}. "
        "See docs/SCRAPER.md and docs/IMPLEMENTATION.md."
    )
    raise typer.Exit(code=2)


@app.command("parse-email")
def parse_email(
    file: typer.Option(..., "--file", help="Path to plain-text email body"),
) -> None:
    """Parse matter number and document type from email text (Phase 3)."""
    body = open(file, encoding="utf-8").read()
    # TODO(phase-3): agent.parse.parse_request(body)
    console.print("[yellow]Not implemented yet.[/yellow]")
    console.print(body[:200])
    raise typer.Exit(code=2)


@app.command()
def worker(once: bool = typer.Option(False, "--once", help="Poll inbox once and exit")) -> None:
    """Poll agent inbox and process requests (Phase 2)."""
    console.print("[yellow]Not implemented yet.[/yellow] See docs/EMAIL.md.")
    raise typer.Exit(code=2)


if __name__ == "__main__":
    app()
