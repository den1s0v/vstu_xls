from dataclasses import dataclass

import vstuxls.grammar2d as pt
import vstuxls.grammar2d.GrammarMatcher as ns
from vstuxls.geom2d import Box
from vstuxls.grammar2d.Match2d import Match2d


@dataclass
class PatternMatcher:
    pattern: 'pt.Pattern2d'
    grammar_matcher: 'ns.GrammarMatcher'

    def find_all(self, region: Box = None, match_limit: int = None) -> list[Match2d]:
        """ Find all matches within whole document.
        :param region if given, find all matches within the region.
        :param match_limit if given, the maximum count of matches returned.
        """
        pass
        # raise TypeError(f"Unknown element type: {type(self.element)}")
