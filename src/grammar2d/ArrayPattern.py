from dataclasses import dataclass, field
from typing import override

from geom2d import open_range
import grammar2d.Match2d as m2
from grammar2d.NonTerminal import NonTerminal
from grammar2d.Pattern2d import Pattern2d, PatternRegistry


VALID_ARRAY_DIRECTIONS = ('row', 'column', 'fill')


@PatternRegistry.register
@dataclass(kw_only=True, repr=True)
class ArrayPattern(NonTerminal):
    """Массив или ряд однотипных элементов, выровненных друг относительно друга

    `direction`:
        'row' — по горизонтали.
        'column' — по горизонтали.
        None — ряд в любом направлении,
            т.е. автоматический выбор из 'row' или 'column', — что оптимальнее (даёт меньше разрывных областей).
        'fill' — заполнение области произвольной формы вместо прямой линии
            (при этом форма самого элемента остаётся прямоугольной, охватывая всё содержимое) <--
             спорный момент: может быть, стоит отдельный вид агрегации выделить.?

    """
    item_pattern: str  # повторяемый элемент
    direction: str = None  # направление
    item_count: open_range = None  # кратность элемента в массиве
    gap: open_range = field(default_factory=lambda: open_range(0, 0))  # зазор между элементами в массиве

    _subpattern: Pattern2d = None  # дочерний элемент грамматики

    def __post_init__(self):
        super().__post_init__()

        # convert attributes to usable types
        if not isinstance(self.gap, open_range):
            self.gap = open_range.parse(str(self.gap))

        if not isinstance(self.item_count, open_range):
            self.item_count = open_range.parse(str(self.item_count)) if self.item_count is not None else open_range(1, None)

    def __hash__(self) -> int:
        return hash(self.name)

    @classmethod
    @override
    def get_kind(cls):
        return "array"  # ???

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
