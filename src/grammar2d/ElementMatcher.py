from dataclasses import dataclass

from grammar2d import GrammarElement
from grammar2d.Match2d import Match2d
from grammar2d.GrammarMatcher import GrammarMatcher


@dataclass
class ElementMatcher:
    element: GrammarElement
    grammar_matcher: 'GrammarMatcher'

    def match(self) -> list[Match2d]:
        pass
        # raise TypeError(f"Unknown element type: {type(self.element)}")
