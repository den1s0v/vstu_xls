from dataclasses import dataclass

import grammar2d as pt
import grammar2d.GrammarMatcher as ns
from geom2d import Box
from grammar2d.Match2d import Match2d


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
