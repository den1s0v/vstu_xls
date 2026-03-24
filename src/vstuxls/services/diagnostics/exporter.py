"""Запись отчёта parsing_diagnostics.json на диск."""

from __future__ import annotations

import json
from pathlib import Path

from vstuxls.services.diagnostics.schema import DocumentDiagnostics


def export_parsing_diagnostics_json(
    diagnostics: DocumentDiagnostics,
    output_dir: Path,
    filename: str = "parsing_diagnostics.json",
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / filename
    path.write_text(
        json.dumps(diagnostics.to_json_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path
