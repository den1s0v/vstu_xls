"""Интерфейс приёма диагностики без зависимости grammar2d от services."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ParsingDiagnosticSink(Protocol):
    """Структурный контракт для `DiagnosticsCollector` и тестовых заглушек."""

    def record_pattern_count_mismatch(
        self, pattern_name: str, found: int, expected_repr: str
    ) -> None: ...

    def record_match_limit_applied(
        self, pattern_name: str, limit: int, *, source: str = ...
    ) -> None: ...

    def record_unexpected_overlap_mode(
        self, pattern_name: str, mode_repr: str
    ) -> None: ...
