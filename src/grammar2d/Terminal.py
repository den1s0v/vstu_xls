from dataclasses import dataclass
from typing import override

# from grammar2d import GRAMMAR
import grammar2d.Match2d as m2
from grammar2d.Pattern2d import Pattern2d, PatternRegistry
import grammar2d.Grammar as ns
from string_matching import CellType


@PatternRegistry.register
@dataclass(kw_only=True, repr=True)
class Terminal(Pattern2d):
    """Просто ячейка"""
    content_type: str = '<unknown cell_type!>'
    _cell_type: CellType = None

    @classmethod
    @override
    def get_kind(cls):
        return "cell"

    def __hash__(self) -> int:
        return hash(self.name)

    @property
    def cell_type(self) -> CellType:
        if not self._cell_type:
            self._cell_type = self._grammar.cell_types[self.content_type]
        return self._cell_type

    @override
    def dependencies(self, recursive=False) -> list['Pattern2d']:
        return []

    @override
    def max_score(self) -> float:
        return 1

    def score_of_match(self, match: m2.Match2d) -> float:
        """ Get score as precision for given match,
            since if was initialized by TerminalMatcher.
        """
        return match.precision

    def get_matcher(self, grammar_matcher):
        from grammar2d.TerminalMatcher import TerminalMatcher
        return TerminalMatcher(self, grammar_matcher)
