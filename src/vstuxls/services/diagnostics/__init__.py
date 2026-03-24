"""Диагностика парсинга: структурированные отчёты по документу."""

from vstuxls.services.diagnostics.collector import DiagnosticsCollector
from vstuxls.services.diagnostics.exporter import export_parsing_diagnostics_json
from vstuxls.services.diagnostics.schema import (
    MATCH_LIMIT_APPLIED,
    OVERLAP_RESOLUTION_UNEXPECTED_MODE,
    PARSE_EXCEPTION,
    PATTERN_COUNT_MISMATCH,
    DocumentDiagnostics,
    IssueSeverity,
    ParsingIssue,
)

__all__ = [
    "MATCH_LIMIT_APPLIED",
    "OVERLAP_RESOLUTION_UNEXPECTED_MODE",
    "PARSE_EXCEPTION",
    "PATTERN_COUNT_MISMATCH",
    "DiagnosticsCollector",
    "DocumentDiagnostics",
    "IssueSeverity",
    "ParsingIssue",
    "export_parsing_diagnostics_json",
]
