"""Build ZIP archives from downloaded files."""

from __future__ import annotations

import zipfile
from pathlib import Path

from regulatory_agent.config import settings


def _snake_case_doc_type(doc_type: str) -> str:
    return doc_type.lower().replace(" ", "_")


def create_zip(files: list[Path], matter: str, doc_type: str) -> Path:
    """Create a flat ZIP archive of downloaded files."""
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    zip_path = settings.output_dir / f"{matter}_{_snake_case_doc_type(doc_type)}.zip"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for file_path in files:
            archive.write(file_path, arcname=file_path.name)

    return zip_path
