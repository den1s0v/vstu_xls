from dataclasses import dataclass
from typing import override

from vstuxls.grammar2d.ArrayPattern import ArrayPattern
from vstuxls.grammar2d.Pattern2d import PatternRegistry


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
        from vstuxls.grammar2d.ArrayInContextPatternMatcher import ArrayInContextPatternMatcher
        return ArrayInContextPatternMatcher(self, grammar_matcher)
