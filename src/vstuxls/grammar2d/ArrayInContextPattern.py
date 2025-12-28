from dataclasses import dataclass, field
from typing import override

from loguru import logger

from grammar2d.ArrayPattern import ArrayPattern
from utils import sorted_list
from geom2d import open_range, Point
import grammar2d.Match2d as m2
from grammar2d.NonTerminal import NonTerminal
from grammar2d.Pattern2d import Pattern2d, PatternRegistry


@PatternRegistry.register
@dataclass(kw_only=True, repr=True)
class ArrayInContextPattern(ArrayPattern):
    """Массив или ряд однотипных элементов, выровненных друг относительно друга
        в контексте Area: придерживается границ Area, игнорируя подходящие элементы за его пределами.
    """

    def __hash__(self) -> int:
        return hash(self.name)

    @classmethod
    @override
    def get_kind(cls):
        return "array-in-context"  # ???

    @classmethod
    def independently_matchable(cls):
        """ Returns False as this specific patterns that cannot be matched independently,
        rather in a context of Area pattern. """
        return False

    def get_matcher(self, grammar_matcher):
        from grammar2d.ArrayInContextPatternMatcher import ArrayInContextPatternMatcher
        return ArrayInContextPatternMatcher(self, grammar_matcher)
