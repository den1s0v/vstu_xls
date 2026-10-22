"""Структурированные диагностики компилятора грамматики.

Каждая диагностика имеет стабильный код (аналог кодов ошибок компилятора), серьёзность,
положение в исходном YAML и, при возможности, «свидетеля» (пример, подтверждающий проблему).

Префиксы кодов:
  G  — структура грамматики (frontend / lint),
  GEO — геометрия (противоречия ограничений),
  LEX — лексика (cell_types),
  AMB — неоднозначность альтернатив,
  POL — политика выбора (priority / overlap / confidence),
  COV — покрытие входных данных (рантайм).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Iterable, Iterator


class Severity(IntEnum):
    INFO = 10
    WARNING = 20
    ERROR = 30

    def __str__(self) -> str:
        return self.name.lower()


@dataclass(frozen=True)
class SourceLoc:
    """Положение элемента в исходном файле грамматики."""
    file: str | None = None
    line: int | None = None

    def __bool__(self) -> bool:
        return self.file is not None or self.line is not None

    def __str__(self) -> str:
        if not self:
            return '<unknown>'
        name = self.file or '<memory>'
        return f'{name}:{self.line}' if self.line else name


# Описание всех известных кодов: код -> (серьёзность по умолчанию, краткое название).
CODES: dict[str, tuple[Severity, str]] = {
    # --- структура ---
    'G001': (Severity.ERROR, 'неизвестный kind паттерна'),
    'G002': (Severity.ERROR, 'ссылка на несуществующий паттерн'),
    'G003': (Severity.ERROR, 'циклическая зависимость паттернов'),
    'G004': (Severity.WARNING, 'паттерн недостижим от корня'),
    'G005': (Severity.WARNING, 'неизвестный ключ'),
    'G006': (Severity.ERROR, 'некорректное значение (диапазон/размер/расположение)'),
    'G007': (Severity.WARNING, 'неиспользуемый тип ячейки'),
    'G008': (Severity.ERROR, 'неизвестный content_type'),
    'G009': (Severity.WARNING, 'паттерн определён повторно'),
    'G010': (Severity.ERROR, 'корень грамматики не определён или неоднозначен'),
    'G011': (Severity.INFO, 'компоненты с одинаковыми ожиданиями'),
    'G012': (Severity.ERROR, 'циклическое наследование extends'),
    'G013': (Severity.WARNING, 'абстрактный паттерн без реализаций'),
    'G014': (Severity.ERROR, 'непродуктивный паттерн (не может совпасть)'),
    'G015': (Severity.ERROR, 'ошибка чтения/разбора файла грамматики'),
    'G016': (Severity.ERROR, 'ошибка шаблона/параметров'),
    'G017': (Severity.ERROR, 'некорректная секция (структура данных)'),
    'G018': (Severity.WARNING, 'повторный импорт файла / цикл импорта'),
    'G019': (Severity.WARNING, 'обязательный компонент без ограничений расположения'),
    'G020': (Severity.WARNING, 'устаревшая трактовка v1: size компонента — это размер родителя'),
    # --- геометрия ---
    'GEO001': (Severity.ERROR, 'противоречивые ограничения расположения/размера'),
    'GEO002': (Severity.INFO, 'ограничение сужается другими ограничениями'),
    'GEO003': (Severity.INFO, 'избыточное ограничение'),
    'GEO004': (Severity.WARNING, 'размеры массива несовместимы с размером контейнера'),
    'GEO005': (Severity.INFO, 'вычисленный размер паттерна'),
    'GEO006': (Severity.WARNING, 'count_in_document противоречит окружению'),
    # --- лексика ---
    'LEX001': (Severity.WARNING, 'типы ячеек распознают общую строку'),
    'LEX002': (Severity.INFO, 'регулярное выражение не поддерживается анализом'),
    'LEX003': (Severity.WARNING, 'паттерн типа ячейки перекрыт более уверенным'),
    'LEX004': (Severity.ERROR, 'некорректное регулярное выражение'),
    'LEX005': (Severity.ERROR, 'пример строки не распознаётся своим типом'),
    # --- неоднозначность ---
    'AMB001': (Severity.WARNING, 'альтернативы могут совпасть на одном месте без правила выбора'),
    'AMB002': (Severity.INFO, 'альтернативы могут совпасть, но правило выбора задано'),
    # --- политика ---
    'POL001': (Severity.WARNING, 'отключённая фильтрация накладок скрывает конфликт'),
    'POL002': (Severity.WARNING, 'политика ссылается на неизвестный паттерн'),
    'POL003': (Severity.INFO, 'политика совпадает со значением по умолчанию'),
    'POL004': (Severity.WARNING, 'отрицательный вес вместо forbid'),
    'POL005': (Severity.ERROR, 'циклическая цепочка prefer'),
    # --- покрытие ---
    'COV001': (Severity.WARNING, 'непокрытые непустые ячейки'),
}


@dataclass
class Diagnostic:
    code: str
    message: str
    severity: Severity | None = None
    pattern: str | None = None
    component: str | None = None
    loc: SourceLoc | None = None
    hint: str | None = None
    witness: str | None = None
    related: list[str] = field(default_factory=list)

    def __post_init__(self):
        if self.severity is None:
            self.severity = CODES.get(self.code, (Severity.WARNING, ''))[0]

    @property
    def title(self) -> str:
        return CODES.get(self.code, (None, ''))[1]

    def subject(self) -> str:
        if self.pattern and self.component:
            return f'{self.pattern}.{self.component}'
        return self.pattern or self.component or ''

    def format(self) -> str:
        where = f'{self.loc}: ' if self.loc else ''
        subj = f' [{self.subject()}]' if self.subject() else ''
        lines = [f'{where}{self.severity} {self.code}{subj}: {self.message}']
        if self.witness:
            lines.append(f'    свидетель: {self.witness}')
        for r in self.related:
            lines.append(f'    см. также: {r}')
        if self.hint:
            lines.append(f'    подсказка: {self.hint}')
        return '\n'.join(lines)

    def to_dict(self) -> dict:
        return {
            'code': self.code,
            'severity': str(self.severity),
            'message': self.message,
            'pattern': self.pattern,
            'component': self.component,
            'file': self.loc.file if self.loc else None,
            'line': self.loc.line if self.loc else None,
            'hint': self.hint,
            'witness': self.witness,
            'related': list(self.related),
        }

    __str__ = format


class DiagnosticReport:
    """Накопитель диагностик; поддерживает фильтрацию и форматирование."""

    def __init__(self, items: Iterable[Diagnostic] = ()):
        self.items: list[Diagnostic] = list(items)

    def add(self, code: str, message: str, *, severity: Severity | None = None, **kwargs) -> Diagnostic:
        d = Diagnostic(code=code, message=message, severity=severity, **kwargs)
        self.items.append(d)
        return d

    def extend(self, other: 'DiagnosticReport | Iterable[Diagnostic]') -> None:
        self.items.extend(other.items if isinstance(other, DiagnosticReport) else other)

    def __iter__(self) -> Iterator[Diagnostic]:
        return iter(self.items)

    def __len__(self) -> int:
        return len(self.items)

    def by_code(self, code: str) -> list[Diagnostic]:
        return [d for d in self.items if d.code == code]

    def codes(self) -> set[str]:
        return {d.code for d in self.items}

    def at_least(self, severity: Severity) -> list[Diagnostic]:
        return [d for d in self.items if d.severity >= severity]

    @property
    def errors(self) -> list[Diagnostic]:
        return self.at_least(Severity.ERROR)

    @property
    def has_errors(self) -> bool:
        return bool(self.errors)

    def sorted(self) -> list[Diagnostic]:
        return sorted(
            self.items,
            key=lambda d: (-int(d.severity), d.loc.file or '' if d.loc else '', d.loc.line or 0 if d.loc else 0, d.code),
        )

    def format(self, min_severity: Severity = Severity.INFO) -> str:
        shown = [d for d in self.sorted() if d.severity >= min_severity]
        if not shown:
            return 'Проблем не найдено.'
        counts = {s: sum(1 for d in shown if d.severity == s) for s in Severity}
        summary = ', '.join(f'{counts[s]} {s}' for s in (Severity.ERROR, Severity.WARNING, Severity.INFO) if counts[s])
        return '\n'.join(d.format() for d in shown) + f'\n— итого: {summary}'

    def to_list(self) -> list[dict]:
        return [d.to_dict() for d in self.sorted()]

    __str__ = format
