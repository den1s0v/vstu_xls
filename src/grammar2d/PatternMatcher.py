from dataclasses import dataclass

from grammar2d import Pattern2d
from grammar2d.Match2d import Match2d
import grammar2d.GrammarMatcher as ns
from grid import Region


@dataclass
class PatternMatcher:
    pattern: Pattern2d
    grammar_matcher: 'ns.GrammarMatcher'

    def find_all(self) -> list[Match2d]:
        pass
        # raise TypeError(f"Unknown element type: {type(self.element)}")

    def match_exact_region(self, region: Region) -> list[Match2d]:
        pass
        # raise TypeError(f"Unknown element type: {type(self.element)}")
