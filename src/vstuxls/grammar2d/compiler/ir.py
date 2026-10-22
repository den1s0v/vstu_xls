"""Промежуточное представление (IR) 2D-грамматики.

IR — это «чистая» модель грамматики, не зависящая от алгоритма матчинга:

* **структура** (`PatternIR`, `ComponentIR`, `ArrayIR`, `LocationIR`, `RelationIR`):
  что из чего состоит и как расположено;
* **политика** (`PolicyIR`): как выбирать из конкурирующих разборов
  (confidence, пороги, накладки, приоритеты) — отдельно от структуры;
* **лексика** (`CellTypeIR`): типы ячеек (аналог lex).

Семантика описана в `docs/grammar_semantics.md`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable, Iterator

from vstuxls.geom2d import open_range
from vstuxls.grammar2d.compiler.diagnostics import SourceLoc

SIDES = ('left', 'right', 'top', 'bottom')
OPPOSITE = {'left': 'right', 'right': 'left', 'top': 'bottom', 'bottom': 'top'}
X_EDGES = ('left', 'right')
Y_EDGES = ('top', 'bottom')


def axis_of(edge: str) -> str:
    return 'x' if edge in X_EDGES else 'y'


class PKind(str, Enum):
    CELL = 'cell'
    AREA = 'area'
    ARRAY = 'array'
    ARRAY_IN_CONTEXT = 'array-in-context'
    GENERAL = 'general'  # абстрактная база (v1): совпадает через паттерны, которые её расширяют
    ALT = 'alt'  # явный выбор (v2): `one_of`

    @property
    def is_concrete(self) -> bool:
        return self in (PKind.CELL, PKind.AREA, PKind.ARRAY, PKind.ARRAY_IN_CONTEXT)

    @property
    def is_array(self) -> bool:
        return self in (PKind.ARRAY, PKind.ARRAY_IN_CONTEXT)


class Role(str, Enum):
    INNER = 'inner'  # образует область родителя (bbox)
    OUTER = 'outer'  # контекст: существует снаружи области родителя
    REQUIRE = 'require'  # положительный предикат: контекст обязан существовать
    FORBID = 'forbid'  # отрицательный предикат: такого контекста не должно быть

    @property
    def is_inner(self) -> bool:
        return self is Role.INNER


# --------------------------------------------------------------------------- location & relations

@dataclass
class LocationIR:
    """Эффективное ограничение расположения компонента относительно родителя.

    `padding[side]`: расстояние от стороны компонента до той же стороны родителя (внутрь), в ячейках.
    `margin[side]`: расстояние от стороны родителя до противоположной стороны компонента (наружу).
    """
    padding: dict[str, open_range] = field(default_factory=dict)
    margin: dict[str, open_range] = field(default_factory=dict)
    raw: object = None

    def is_empty(self) -> bool:
        return not self.padding and not self.margin

    def diffs(self) -> list[tuple[str, str, open_range]]:
        """Разностные ограничения вида `child.c_edge - parent.p_edge in range`.

        Возвращает тройки `(c_edge, p_edge, range)`; ось определяется именем стороны.
        """
        out: list[tuple[str, str, open_range]] = []
        for side, rng in self.padding.items():
            # (P.d - C.d) * sign(d) in rng; sign: left/top = -1, right/bottom = +1
            out.append((side, side, rng if side in ('left', 'top') else -rng))
        for side, rng in self.margin.items():
            opp = OPPOSITE[side]
            # (P.side - C.opp) * sign(opp) in rng
            out.append((opp, side, -rng if opp in ('right', 'bottom') else rng))
        return out

    def describe(self) -> str:
        parts = [f'padding-{s}: {r}' for s, r in self.padding.items()]
        parts += [f'margin-{s}: {r}' for s, r in self.margin.items()]
        return ', '.join(parts) or '(нет)'


@dataclass(frozen=True)
class EdgeRef:
    comp: str  # имя компонента либо `this` (сам паттерн)
    edge: str  # left | right | top | bottom

    def __str__(self) -> str:
        return f'{self.comp}.{self.edge}'


@dataclass
class RelationIR:
    """Отношение между рёбрами компонентов: `a - b in delta` (координаты линий сетки)."""
    a: EdgeRef
    b: EdgeRef
    delta: open_range
    text: str = ''
    loc: SourceLoc = field(default_factory=SourceLoc)

    @property
    def axis(self) -> str:
        return axis_of(self.a.edge)


# --------------------------------------------------------------------------- policy

@dataclass
class OverlapPolicy:
    mode: str = 'none'  # none | full | partial
    criteria: list[tuple[str, str]] = field(default_factory=lambda: [('area', 'max'), ('precision', 'max')])

    def decides(self) -> bool:
        return self.mode != 'none' and bool(self.criteria)


@dataclass
class PolicyIR:
    """Политика выбора между совпадениями: отделена от структуры паттерна."""
    confidence: float = 1.0
    precision_threshold: float | None = None
    overlap: OverlapPolicy | None = None
    # v1 `allows_overlapping: true` == exclusive_candidates=False:
    # не отфильтровывать пересекающиеся совпадения самого паттерна.
    exclusive_candidates: bool = True
    priority: int = 0
    prefer: list[str] = field(default_factory=list)  # имена паттернов, которых этот паттерн вытесняет
    cost: float | None = None  # явная «стоимость» разбора (для глобального выбора)
    loc: SourceLoc = field(default_factory=SourceLoc)

    def effective_threshold(self) -> float:
        return 0.3 if self.precision_threshold is None else self.precision_threshold


# --------------------------------------------------------------------------- structure

@dataclass
class ComponentIR:
    name: str
    pattern: str | None = None
    role: Role = Role.INNER
    location: LocationIR | None = None
    size: tuple[open_range, open_range] | None = None
    weight: float = 1.0
    optional: bool = False
    precision_threshold: float = 0.3
    count: open_range | None = None
    inline: 'PatternIR | None' = None
    loc: SourceLoc = field(default_factory=SourceLoc)
    # Если компонент получен разворачиванием `count`, здесь имя исходного компонента.
    group: str | None = None
    group_index: int = 0

    @property
    def inner(self) -> bool:
        return self.role.is_inner

    def effective_location(self) -> LocationIR:
        """Расположение с учётом умолчаний: внутри — `0+` по всем сторонам; снаружи — без ограничений."""
        if self.location is not None:
            return self.location
        if self.inner:
            return LocationIR(padding={s: open_range(0, None) for s in SIDES})
        return LocationIR()

    @property
    def is_predicate(self) -> bool:
        return self.role in (Role.REQUIRE, Role.FORBID)

    @property
    def must_exist(self) -> bool:
        """Нужно ли найти такой компонент, чтобы родитель считался совпавшим."""
        if self.role is Role.FORBID:
            return False
        return not self.optional


@dataclass
class ArrayIR:
    item_pattern: str | None = None
    direction: str = 'auto'  # row | column | auto | fill
    item_count: open_range = field(default_factory=lambda: open_range(1, None))
    gap: open_range = field(default_factory=lambda: open_range(0, 0))
    distance_kind: str = 'corner'
    allow_breakdown: bool = False
    index_items: bool = False
    # Выравнивание элементов по поперечной оси: both (по умолчанию в v1), start, end, none.
    align: str = 'both'


@dataclass
class PatternIR:
    name: str
    kind: PKind
    description: str | None = None
    root: bool = False
    count_in_document: open_range = field(default_factory=lambda: open_range(0, None))
    size: tuple[open_range, open_range] | None = None
    style: dict | None = None
    extends: list[str] = field(default_factory=list)
    static_data: dict | None = None
    components: list[ComponentIR] = field(default_factory=list)
    relations: list[RelationIR] = field(default_factory=list)
    array: ArrayIR | None = None
    content_type: str | None = None
    one_of: list[str] = field(default_factory=list)
    policy: PolicyIR = field(default_factory=PolicyIR)
    loc: SourceLoc = field(default_factory=SourceLoc)
    origin: str | None = None  # откуда взят (шаблон / инлайн-определение)
    unknown_keys: list[str] = field(default_factory=list)

    @property
    def is_concrete(self) -> bool:
        return self.kind.is_concrete

    @property
    def is_inline(self) -> bool:
        return self.origin == 'inline'

    def component(self, name: str) -> ComponentIR | None:
        for c in self.components:
            if c.name == name:
                return c
        return None

    def referenced(self) -> list[str]:
        """Имена паттернов, на которые ссылается этот паттерн (кроме `extends`)."""
        names: list[str] = []
        for c in self.components:
            if c.pattern:
                names.append(c.pattern)
        if self.array and self.array.item_pattern:
            names.append(self.array.item_pattern)
        names.extend(self.one_of)
        return names

    def required_components(self) -> list[ComponentIR]:
        return [c for c in self.components if c.must_exist]


@dataclass
class StringPatternIR:
    """Сырое описание одного паттерна типа ячейки (до компиляции регулярки)."""
    data: dict
    loc: SourceLoc = field(default_factory=SourceLoc)

    @property
    def confidence(self) -> float:
        return float(self.data.get('confidence', 0.5))

    @property
    def regex(self) -> str:
        return str(self.data.get('pattern', ''))


@dataclass
class CellTypeIR:
    name: str
    description: str = ''
    update_content: str | None = None
    patterns: list[StringPatternIR] = field(default_factory=list)
    loc: SourceLoc = field(default_factory=SourceLoc)
    # Приоритет типа при конфликте (lex-стиль): больше — вытесняет; v2.
    priority: int = 0
    # Типы, которые вытесняют этот тип при совпадении строки (`except`).
    except_types: list[str] = field(default_factory=list)
    # Примеры строк для генератора и самопроверки.
    examples: list[str] = field(default_factory=list)


@dataclass
class GrammarIR:
    patterns: dict[str, PatternIR] = field(default_factory=dict)
    cell_types: dict[str, CellTypeIR] = field(default_factory=dict)
    root_name: str | None = None
    files: list[str] = field(default_factory=list)
    # Политики, заданные отдельной секцией `policies:` (имя паттерна -> PolicyIR)
    policies: dict[str, PolicyIR] = field(default_factory=dict)
    target_mode: str = 'root'
    # Диалект DSL: 1 — совместимость со старым матчером, 2 — `grammar: 2` (чистая семантика).
    dialect: int = 1
    # Пары типов ячеек, имеющих общие строки (заполняется `celltypes.analyze_cell_types`).
    lexical_conflicts: set = field(default_factory=set, repr=False)

    # ---- кэши (строятся лениво) ----
    _extenders: dict[str, list[str]] | None = field(default=None, repr=False)

    def invalidate(self) -> None:
        self._extenders = None

    def __getitem__(self, name: str) -> PatternIR:
        return self.patterns[name]

    def __contains__(self, name: str) -> bool:
        return name in self.patterns

    def __iter__(self) -> Iterator[PatternIR]:
        return iter(self.patterns.values())

    @property
    def root(self) -> PatternIR | None:
        return self.patterns.get(self.root_name) if self.root_name else None

    # ---- наследование (extends) ----
    def direct_extenders(self, name: str) -> list[str]:
        if self._extenders is None:
            m: dict[str, list[str]] = {}
            for p in self.patterns.values():
                for base in p.extends:
                    m.setdefault(base, []).append(p.name)
            self._extenders = m
        return self._extenders.get(name, [])

    def extenders(self, name: str) -> list[str]:
        """Все (транзитивные) расширяющие паттерны; цикл не приводит к зависанию."""
        seen: dict[str, None] = {}
        stack = list(self.direct_extenders(name))
        while stack:
            n = stack.pop(0)
            if n in seen or n == name:
                continue
            seen[n] = None
            stack.extend(self.direct_extenders(n))
        return list(seen)

    def bases(self, name: str) -> list[str]:
        seen: dict[str, None] = {}
        stack = list(self.patterns[name].extends) if name in self.patterns else []
        while stack:
            n = stack.pop(0)
            if n in seen or n == name or n not in self.patterns:
                continue
            seen[n] = None
            stack.extend(self.patterns[n].extends)
        return list(seen)

    def choice_set(self, name: str, _seen: set[str] | None = None) -> list[str]:
        """Конкретные паттерны, которые могут стоять на месте ссылки на `name`.

        Для конкретного паттерна это он сам плюс все, кто его расширяет;
        для `general`/`alt` — только реализации.
        """
        _seen = _seen if _seen is not None else set()
        if name in _seen or name not in self.patterns:
            return []
        _seen.add(name)
        p = self.patterns[name]
        out: list[str] = []
        if p.is_concrete:
            out.append(name)
        if p.kind is PKind.ALT:
            for m in p.one_of:
                out.extend(x for x in self.choice_set(m, _seen) if x not in out)
        for ext in self.direct_extenders(name):
            out.extend(x for x in self.choice_set(ext, _seen) if x not in out)
        return out

    # ---- зависимости ----
    def dependencies(self, name: str) -> list[str]:
        """Паттерны, которые должны быть найдены прежде, чем можно искать `name`."""
        p = self.patterns[name]
        deps: dict[str, None] = {}
        for ref in p.referenced():
            if ref in self.patterns:
                deps[ref] = None
        # База ждёт всех своих расширений (как в старом матчере).
        for ext in self.extenders(name):
            deps[ext] = None
        deps.pop(name, None)
        return list(deps)

    def reverse_dependencies(self) -> dict[str, list[str]]:
        rev: dict[str, list[str]] = {n: [] for n in self.patterns}
        for n in self.patterns:
            for d in self.dependencies(n):
                rev.setdefault(d, []).append(n)
        return rev

    def waves(self) -> tuple[list[list[str]], list[str]]:
        """Топологические «волны». Возвращает (волны, оставшиеся_в_цикле)."""
        remaining = set(self.patterns)
        done: set[str] = set()
        waves: list[list[str]] = []
        while remaining:
            wave = sorted(n for n in remaining if all(d in done for d in self.dependencies(n)))
            if not wave:
                break
            waves.append(wave)
            done.update(wave)
            remaining.difference_update(wave)
        return waves, sorted(remaining)

    def effective_policy(self, name: str) -> PolicyIR:
        """Политика паттерна (секция `policies:` уже слита в `pattern.policy` фронтендом)."""
        return self.patterns[name].policy

    def iter_components(self) -> Iterable[tuple[PatternIR, ComponentIR]]:
        for p in self.patterns.values():
            for c in p.components:
                yield p, c
