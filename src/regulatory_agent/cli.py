"""Typer CLI — local dev entry points."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console

from regulatory_agent.config import settings
from regulatory_agent.models import DocumentType
from regulatory_agent.scraper.navigate import MatterNotFoundError
from regulatory_agent.scraper.service import scrape_matter

app = typer.Typer(help="Senpilot regulatory document agent")
console = Console()


def _configure_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def _validate_matter_number(matter_number: str) -> None:
    if not re.fullmatch(r"M\d{5}", matter_number):
        console.print(f"[red]Invalid matter number:[/red] {matter_number} (expected M#####)")
        raise typer.Exit(code=1)


@app.command()
def scrape(
    matter_number: str = typer.Argument(..., help="Matter number, e.g. M12205"),
    doc_type: str = typer.Option(..., "--type", help="Document type tab to download from"),
    max_downloads: Annotated[
        Optional[int], typer.Option("--max", help="Override MAX_DOWNLOADS")
    ] = None,
    as_json: bool = typer.Option(False, "--json", help="Print ScrapeResult as JSON"),
    headed: bool = typer.Option(False, "--headed", help="Run browser in headed mode"),
) -> None:
    """Scrape UARB and produce a ZIP (Phase 1)."""
    _configure_logging()
    _validate_matter_number(matter_number)

    document_type = DocumentType.from_user_text(doc_type)
    if document_type is None:
        console.print(f"[red]Unknown document type:[/red] {doc_type}")
        raise typer.Exit(code=1)

    try:
        result = scrape_matter(
            matter_number,
            document_type,
            max_downloads=max_downloads,
            headless=False if headed else None,
        )
    except MatterNotFoundError as exc:
        console.print(f"[red]Matter not found:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    except Exception as exc:
        message = str(exc).encode("ascii", errors="replace").decode("ascii")
        console.print(f"[red]Scrape failed:[/red] {message}")
        if headed:
            _save_debug_screenshot()
        raise typer.Exit(code=1) from exc

    if as_json:
        console.print(json.dumps(result.model_dump(mode="json"), indent=2))
    else:
        console.print(f"[green]ZIP created:[/green] {result.zip_path}")
        console.print(
            f"Downloaded {result.downloaded_count} of {result.available_in_tab} "
            f"{document_type.value}"
        )


def _save_debug_screenshot() -> None:
    """Best-effort debug screenshot placeholder — browser already closed on failure."""
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = settings.output_dir / f"debug_{timestamp}.png"
    console.print(f"[yellow]Debug screenshot path (if captured):[/yellow] {path}")


@app.command("parse-email")
def parse_email(
    file: str = typer.Option(..., "--file", help="Path to plain-text email body"),
) -> None:
    """Parse matter number and document type from email text (Phase 3)."""
    body = Path(file).read_text(encoding="utf-8")
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
