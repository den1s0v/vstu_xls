from dataclasses import dataclass, field

from geom2d import open_range
from grammar2d.NonTerminal import NonTerminal
from grammar2d.Pattern2d import Pattern2d, PatternRegistry


VALID_ARRAY_DIRECTIONS = ('row', 'column', 'fill')


@dataclass(kw_only=True, repr=True)
class ArrayPattern(NonTerminal):
    """Массив или ряд однотипных элементов, выровненных друг относительно друга

    `direction`:
        'row' — по горизонтали (если не указать direction, то в любом направлении)
        'column'
        'fill': заполнение области произвольной формы вместо прямой линии
            (при этом форма самого элемента остаётся прямоугольной, охватывая всё содержимое) <--
             спорный момент: может быть, стоит отдельный вид агрегации выделить.?

    """
    item_pattern: Pattern2d  # повторяемый элемент
    direction: str = None  # направление
    item_count: open_range = None  # кратность элемента в массиве
    gap: open_range = field(default_factory=lambda: open_range(0, 0))  # зазор между элементами в массиве

    @classmethod
    def get_kind(cls):
        return "array"  # ???

    # dependencies: list[GrammarElement] = None
    def dependencies(self, recursive=False) -> list[Pattern2d]:
        if not self.item_pattern:
            return []

        if not recursive:
            return [self.item_pattern]

        return [self.item_pattern, *self.item_pattern.dependencies(recursive)]

    def max_score(self) -> float:
        """ precision = score / max_score """
        return 1

    ...

    # def get_matcher(self, grammar_macher):
    #     from grammar2d.ArrayPatternMatcher import ArrayPatternMatcher
    #     return ArrayPatternMatcher(self, grammar_macher)


PatternRegistry.register(ArrayPattern)
