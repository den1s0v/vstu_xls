from dataclasses import dataclass

# from grammar2d import GRAMMAR
from grammar2d.GrammarElement import GrammarElement
from grammar2d.Grammar import Grammar
from string_matching import CellType

GRAMMAR: 'Grammar'


@dataclass
class Terminal(GrammarElement):
    """Просто ячейка"""
    cell_type_name: str = '<unknown cell_type!>'
    _cell_type: CellType = None

    @property
    def cell_type(self) -> CellType:
        if not self._cell_type:
            self._cell_type = GRAMMAR.cell_types[self.cell_type_name]
        return self._cell_type

    def dependencies(self, recursive=False) -> list['GrammarElement']:
        return ()

    def max_score(self) -> float:
        return 1

    def get_matcher(self, grammar_matcher):
        from grammar2d.TerminalMatcher import TerminalMatcher
        return TerminalMatcher(self, grammar_matcher)
