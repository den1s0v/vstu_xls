from dataclasses import dataclass

# from grammar2d import GRAMMAR
from grammar2d.Pattern2d import Pattern2d, PatternRegistry
import grammar2d.Grammar as ns
from string_matching import CellType

GRAMMAR: 'ns.Grammar'


@dataclass
class Terminal(Pattern2d):
    """Просто ячейка"""
    cell_type_name: str = '<unknown cell_type!>'
    _cell_type: CellType = None

    @classmethod
    def get_kind(cls):
        return "cell"

    @property
    def cell_type(self) -> CellType:
        if not self._cell_type:
            self._cell_type = GRAMMAR.cell_types[self.cell_type_name]
        return self._cell_type

    def dependencies(self, recursive=False) -> list['Pattern2d']:
        return ()

    def max_score(self) -> float:
        return 1

    def get_matcher(self, grammar_matcher):
        from grammar2d.TerminalMatcher import TerminalMatcher
        return TerminalMatcher(self, grammar_matcher)


PatternRegistry.register(Terminal)
