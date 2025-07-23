from dataclasses import dataclass

import grammar2d as pt
import grammar2d.GrammarMatcher as ns
from geom2d import Box
from grammar2d.Match2d import Match2d


@dataclass
class PatternMatcher:
    pattern: 'pt.Pattern2d'
    grammar_matcher: 'ns.GrammarMatcher'

    def find_all(self, region: Box = None) -> list[Match2d]:
        """ Find all matches within whole document.
        If a region is given, find all matches within the region. """
        pass
        # raise TypeError(f"Unknown element type: {type(self.element)}")
