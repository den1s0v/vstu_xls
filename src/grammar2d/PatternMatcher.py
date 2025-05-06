from dataclasses import dataclass

import grammar2d as pt
from grammar2d.Match2d import Match2d
import grammar2d.GrammarMatcher as ns
from grid import Region


@dataclass
class PatternMatcher:
    pattern: 'pt.Pattern2d'
    grammar_matcher: 'ns.GrammarMatcher'

    def find_all(self) -> list[Match2d]:
        """ Find all matches within whole document. """
        pass
        # raise TypeError(f"Unknown element type: {type(self.element)}")

    def match_exact_region(self, region: Region) -> list[Match2d]:
        """ Find all matches within given region. 
        TODO: deprecate this, add optional param `region: Region = None` to find_all()
        """
        pass
        # raise TypeError(f"Unknown element type: {type(self.element)}")
