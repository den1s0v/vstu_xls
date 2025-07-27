from dataclasses import dataclass, field
from typing import override

from loguru import logger

from utils import sorted_list
from geom2d import open_range, Point
import grammar2d.Match2d as m2
from grammar2d.NonTerminal import NonTerminal
from grammar2d.Pattern2d import Pattern2d, PatternRegistry


VALID_ARRAY_DIRECTIONS = ('row', 'column', 'auto', 'fill')
DISTANCE_KINDS = ('corner', 'side')


@PatternRegistry.register
@dataclass(kw_only=True, repr=True)
class ArrayPattern(NonTerminal):
    """Массив или ряд однотипных элементов, выровненных друг относительно друга.

    `direction`:
        'row' — по горизонтали.
        'column' — по горизонтали.
        'auto' or None — ряд в любом направлении,
            т.е. автоматический выбор из 'row' или 'column', — что оптимальнее (даёт меньше разрывных областей).
        'fill' — заполнение области произвольной формы вместо прямой линии
            (при этом форма самого элемента остаётся прямоугольной, охватывая всё содержимое) <--
             спорный момент: может быть, стоит отдельный вид агрегации выделить.?
    """

    item_pattern: str  # повторяемый элемент
    direction: str = None  # направление
    item_count: open_range = None  # кратность элемента в массиве

    # зазор между элементами в массиве,
    # по умолчанию нулевой
    gap: open_range = field(default_factory=lambda: open_range(0, 0))

    # Если найденное пятно превышает item_count или выходит за пределы size,
    # то при allow_breakdown==True область совпадения может быть разбита на части;
    # иначе (False) такое пятно не считается совпадением (целиком).
    allow_breakdown: bool = False
    distance_kind: str = 'corner'

    _subpattern: Pattern2d = None  # дочерний элемент грамматики

    def __post_init__(self):
        super().__post_init__()

        if self.distance_kind not in DISTANCE_KINDS:
            raise ValueError(f'ArrayPattern\'s `distance_kind` must be one of `{DISTANCE_KINDS
            }`, but got: `{self.distance_kind}`.')

        # convert attributes to usable types
        if not isinstance(self.gap, open_range):
            self.gap = open_range.parse(str(self.gap))

        if self.item_count is None:
            self.item_count = open_range.parse('1+')

        given_range = open_range.make(self.item_count)
        self.item_count = given_range.intersect(open_range.parse('1+'))
        if self.item_count is None:
            raise ValueError(f"Array pattern `{self.name
                }` defines invalid range for item count: {given_range}")

        if not isinstance(self.direction, str):
            self.direction = 'auto'
            logger.info(f'Assuming the default value `{self.direction}` for direction of ArrayPattern with name `{self.name}`.')
        elif self.direction not in VALID_ARRAY_DIRECTIONS:
            msg = f'ArrayPattern with name `{self.name}` has direction set to `{self.direction}`, but expected one of `{VALID_ARRAY_DIRECTIONS}`.'
            logger.critical(msg)
            raise ValueError(msg)

    def __hash__(self) -> int:
        return hash(self.name)

    @classmethod
    @override
    def get_kind(cls):
        return "array"  # ???

    def get_points_occupied_by_match(self, match: 'm2.Match2d') -> list[Point]:
        """ For arrays: transparent.
        Реализация по умолчанию: взять все занятые компонентами позиции.
        """
        component_points = set()
        for comp_match in match.component2match.values():
            component_points |= set(comp_match.get_occupied_points())

        # Отсечь наружные части, если таковые есть (могут быть при отрицательных отступах).
        inner_points = set(match.box.iterate_points())
        return sorted_list(inner_points & component_points)

    def get_content_of_match(self, match: 'm2.Match2d') -> dict | list | str:
        """ Компактные данные для экспорта в JSON.
        """
        return [
            m.get_content()
            for m in match.component2match.values()
        ]

    @property
    def subpattern(self) -> Pattern2d:
        """Дочерний элемент грамматики.
        This method is intended to be called after the grammar has fully initialized.
        """
        if not self._subpattern:
            self._subpattern = self._grammar[self.item_pattern]
        return self._subpattern


    @override
    def dependencies(self, recursive=False) -> list[Pattern2d]:
        if not self.item_pattern:
            return []

        if not recursive:
            return [self.subpattern]

        return [self.subpattern, *self.subpattern.dependencies(recursive)]

    @override
    def max_score(self) -> float:
        """ precision = score / max_score """
        return 1

    def score_of_match(self, match: m2.Match2d) -> float:
        """ Calc score for given match """
        raise NotImplementedError(type(self))

    ...

    def get_matcher(self, grammar_matcher):
        from grammar2d.ArrayPatternMatcher import ArrayPatternMatcher
        return ArrayPatternMatcher(self, grammar_matcher)
