from dataclasses import dataclass
from typing import TYPE_CHECKING

from vstuxls.geom2d import Box

if TYPE_CHECKING:
    from vstuxls.grammar2d.Match2d import Match2d
    from vstuxls.grammar2d.GrammarMatcher import GrammarMatcher
    from vstuxls.grammar2d.Pattern2d import Pattern2d

@dataclass
class PatternMatcher:
    pattern: 'Pattern2d'
    grammar_matcher: 'GrammarMatcher'

    def find_all(self, region: Box = None, match_limit: int = None) -> list['Match2d']:
        """ Find all matches within whole document.
        :param region if given, find all matches within the region.
        :param match_limit if given, the maximum count of matches returned.
        """
        pass
        # raise TypeError(f"Unknown element type: {type(self.element)}")
