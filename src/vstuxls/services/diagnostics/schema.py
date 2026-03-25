"""Схема структурированной диагностики парсинга (MVP)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

# Стабильные коды для машинной обработки отчётов
PATTERN_COUNT_MISMATCH = "PATTERN_COUNT_MISMATCH"
MATCH_LIMIT_APPLIED = "MATCH_LIMIT_APPLIED"
OVERLAP_RESOLUTION_UNEXPECTED_MODE = "OVERLAP_RESOLUTION_UNEXPECTED_MODE"
PARSE_EXCEPTION = "PARSE_EXCEPTION"


class IssueSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(slots=True)
class ParsingIssue:
    severity: IssueSeverity
    code: str
    message: str
    pattern_name: str | None = None
    wave_index: int | None = None
    expected: str | None = None
    actual: str | None = None
    box: dict[str, int] | None = None
    source: str | None = None
    exception_type: str | None = None
    detail: str | None = None

    def to_json_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "severity": self.severity.value,
            "code": self.code,
            "message": self.message,
        }
        if self.pattern_name is not None:
            d["pattern_name"] = self.pattern_name
        if self.wave_index is not None:
            d["wave_index"] = self.wave_index
        if self.expected is not None:
            d["expected"] = self.expected
        if self.actual is not None:
            d["actual"] = self.actual
        if self.box is not None:
            d["box"] = self.box
        if self.source is not None:
            d["source"] = self.source
        if self.exception_type is not None:
            d["exception_type"] = self.exception_type
        if self.detail is not None:
            d["detail"] = self.detail
        return d


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class DocumentDiagnostics:
    """Итоговый отчёт по одному документу."""

    document: dict[str, Any]
    summary: dict[str, Any]
    issues: list[ParsingIssue] = field(default_factory=list)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "document": dict(self.document),
            "summary": dict(self.summary),
            "issues": [i.to_json_dict() for i in self.issues],
        }

    @classmethod
    def from_collector(
        cls,
        *,
        issues: list[ParsingIssue],
        source_path: str | None,
        grammar_path: str | None,
        started_at: str | None,
        finished_at: str | None,
        duration_ms: float | None,
        root_matches_count: int,
    ) -> DocumentDiagnostics:
        errors = sum(1 for i in issues if i.severity == IssueSeverity.ERROR)
        warnings = sum(1 for i in issues if i.severity == IssueSeverity.WARNING)
        infos = sum(1 for i in issues if i.severity == IssueSeverity.INFO)
        doc: dict[str, Any] = {
            "source_path": source_path,
            "grammar_path": grammar_path,
            "started_at": started_at,
            "finished_at": finished_at,
        }
        if duration_ms is not None:
            doc["duration_ms"] = round(duration_ms, 3)
        summary = {
            "errors_count": errors,
            "warnings_count": warnings,
            "infos_count": infos,
            "root_matches_count": root_matches_count,
        }
        return cls(document=doc, summary=summary, issues=list(issues))
