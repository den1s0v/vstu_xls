"""Сборщик диагностических сообщений за один прогон парсинга документа."""

from __future__ import annotations

import time
import traceback
from typing import TYPE_CHECKING

from vstuxls.services.diagnostics.schema import (
    MATCH_LIMIT_APPLIED,
    OVERLAP_RESOLUTION_UNEXPECTED_MODE,
    PARSE_EXCEPTION,
    PATTERN_COUNT_MISMATCH,
    DocumentDiagnostics,
    IssueSeverity,
    ParsingIssue,
    _utc_now_iso,
)

if TYPE_CHECKING:
    pass


class DiagnosticsCollector:
    """Накапливает issues за время parse_document; волна задаётся через set_wave_index."""

    def __init__(
        self,
        *,
        source_path: str | None = None,
        grammar_path: str | None = None,
    ) -> None:
        self._source_path = source_path
        self._grammar_path = grammar_path
        self._issues: list[ParsingIssue] = []
        self._wave_index: int | None = None
        self._started_at: str | None = None
        self._finished_at: str | None = None
        self._start_perf: float | None = None
        self._root_matches_count: int = 0

    def set_wave_index(self, wave_index: int | None) -> None:
        self._wave_index = wave_index

    def mark_started(self) -> None:
        self._started_at = _utc_now_iso()
        self._start_perf = time.perf_counter()

    def mark_finished(self) -> None:
        self._finished_at = _utc_now_iso()

    def set_root_matches_count(self, n: int) -> None:
        self._root_matches_count = n

    def record_issue(
        self,
        severity: IssueSeverity,
        code: str,
        message: str,
        *,
        pattern_name: str | None = None,
        wave_index: int | None = None,
        expected: str | None = None,
        actual: str | None = None,
        box: dict[str, int] | None = None,
        source: str | None = None,
        exception_type: str | None = None,
        detail: str | None = None,
    ) -> None:
        wi = self._wave_index if wave_index is None else wave_index
        self._issues.append(
            ParsingIssue(
                severity=severity,
                code=code,
                message=message,
                pattern_name=pattern_name,
                wave_index=wi,
                expected=expected,
                actual=actual,
                box=box,
                source=source,
                exception_type=exception_type,
                detail=detail,
            )
        )

    def record_pattern_count_mismatch(
        self,
        pattern_name: str,
        found: int,
        expected_repr: str,
    ) -> None:
        self.record_issue(
            IssueSeverity.WARNING,
            PATTERN_COUNT_MISMATCH,
            f"Найдено {found} совпадений паттерна `{pattern_name}`, ожидалось {expected_repr}.",
            pattern_name=pattern_name,
            expected=expected_repr,
            actual=str(found),
            source="GrammarMatcher._find_matches_of_pattern",
        )

    def record_match_limit_applied(
        self,
        pattern_name: str,
        limit: int,
        *,
        source: str = "GrammarMatcher._find_matches_of_pattern",
    ) -> None:
        self.record_issue(
            IssueSeverity.WARNING,
            MATCH_LIMIT_APPLIED,
            f"Результат сопоставления паттерна `{pattern_name}` усечён до {limit} совпадений.",
            pattern_name=pattern_name,
            actual=str(limit),
            source=source,
        )

    def record_unexpected_overlap_mode(
        self,
        pattern_name: str,
        mode_repr: str,
    ) -> None:
        self.record_issue(
            IssueSeverity.WARNING,
            OVERLAP_RESOLUTION_UNEXPECTED_MODE,
            f"Неожиданный режим разрешения перекрытий {mode_repr!r} для паттерна `{pattern_name}`; "
            "фильтрация не применена.",
            pattern_name=pattern_name,
            actual=mode_repr,
            source="GrammarMatcher._apply_overlap_resolution",
        )

    def record_parse_exception(self, exc: BaseException) -> None:
        self.record_issue(
            IssueSeverity.ERROR,
            PARSE_EXCEPTION,
            f"Исключение при разборе документа: {exc!s}",
            exception_type=type(exc).__name__,
            detail=traceback.format_exc(limit=12),
            source="DocumentParsingService.parse_document",
        )

    @property
    def issues(self) -> list[ParsingIssue]:
        return list(self._issues)

    def build_document_diagnostics(self) -> DocumentDiagnostics:
        duration_ms: float | None = None
        if self._start_perf is not None:
            duration_ms = (time.perf_counter() - self._start_perf) * 1000.0
        return DocumentDiagnostics.from_collector(
            issues=self._issues,
            source_path=self._source_path,
            grammar_path=self._grammar_path,
            started_at=self._started_at,
            finished_at=self._finished_at,
            duration_ms=duration_ms,
            root_matches_count=self._root_matches_count,
        )
