from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

from grammar2d import Grammar, GrammarMatcher
from grammar2d.Match2d import Match2d

from services.debugging import WaveDebugExporter


@dataclass
class ParsingDebugHooks:
    """Вспомогательные хуки для отладки процесса распознавания."""

    def on_wave_started(self, wave_index: int, patterns: Sequence[str]) -> None:
        """Вызывается перед запуском волны."""

    def on_wave_completed(self, wave_index: int, matches: Sequence[Match2d]) -> None:
        """Вызывается после завершения волны."""


@dataclass
class DocumentParsingService:
    """Высокоуровневый сервис для работы с грамматикой документов."""

    grammar: Grammar
    debug_hooks: ParsingDebugHooks = field(default_factory=ParsingDebugHooks)
    wave_exporter: WaveDebugExporter | None = None

    _matcher: GrammarMatcher = field(init=False)
    _last_grid: Any = field(default=None, init=False)
    _wave_patterns: dict[int, list[str]] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        self._matcher = GrammarMatcher(self.grammar, wave_observer=self)

    def parse_document(self, grid: Any) -> list[Match2d]:
        """Основная точка входа: запускает распознавание документа."""
        self._last_grid = grid
        self._wave_patterns.clear()
        return self._matcher.run_match(grid)

    def notify_wave_started(self, wave_index: int, patterns: Iterable[str]) -> None:
        """Вспомогательный метод: уведомляет хуки о запуске волны."""
        pattern_list = list(patterns)
        self._wave_patterns[wave_index] = pattern_list
        self._handle_wave_started(wave_index, pattern_list)

        if self.debug_hooks:
            self.debug_hooks.on_wave_started(wave_index, pattern_list)

    def notify_wave_completed(self, wave_index: int, matches: Iterable[Match2d]) -> None:
        """Вспомогательный метод: уведомляет хуки об успешном завершении волны."""
        matches_list = list(matches)
        self._handle_wave_completed(wave_index, matches_list)

        if self.debug_hooks:
            self.debug_hooks.on_wave_completed(wave_index, matches_list)

    @property
    def matcher(self) -> GrammarMatcher:
        """Возвращает внутренний `GrammarMatcher`."""
        return self._matcher

    def _handle_wave_started(self, wave_index: int, patterns: Sequence[str]) -> None:
        """Заглушка для расширений: подготовка перед отладкой волны."""
        # При необходимости можно подготовить экспорт или логирование

    def _handle_wave_completed(self, wave_index: int, matches: Sequence[Match2d]) -> None:
        """Экспорт результатов волны и последующие шаги отладки."""
        if self.wave_exporter:
            pattern_names = self._wave_patterns.get(wave_index, [])
            self.wave_exporter.export_wave(
                wave_index=wave_index,
                grid=self._last_grid,
                pattern_names=pattern_names,
                matches=matches,
            )

    def debug_export_wave_to_excel(self, wave_index: int, matches: Iterable[Match2d]) -> None:
        """Ручной экспорт волны в Excel."""
        if self.wave_exporter:
            self.wave_exporter.export_wave(
                wave_index=wave_index,
                grid=self._last_grid,
                pattern_names=self._wave_patterns.get(wave_index, []),
                matches=matches,
            )

    def debug_export_wave_to_json(self, wave_index: int, matches: Iterable[Match2d]) -> None:
        """Ручной экспорт волны в JSON."""
        if self.wave_exporter:
            self.wave_exporter.export_wave(
                wave_index=wave_index,
                grid=self._last_grid,
                pattern_names=self._wave_patterns.get(wave_index, []),
                matches=matches,
            )

