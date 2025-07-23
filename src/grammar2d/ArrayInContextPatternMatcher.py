from collections import defaultdict
from dataclasses import dataclass

from loguru import logger

from geom2d import Box, Direction, RIGHT, DOWN
from grammar2d import ArrayPattern
from grammar2d.ArrayPatternMatcher import ArrayPatternMatcher
from grammar2d.Match2d import Match2d
from grid import Region


@dataclass
class ArrayInContextPatternMatcher(ArrayPatternMatcher):

    def find_all(self, region: Box = None) -> list[Match2d]:
        """ Find all matches within whole document.
        If a region is given, find all matches within the region. """
        # short aliases
        item = self.pattern.subpattern
        gm = self.grammar_matcher

        item_occurrences = gm.get_pattern_matches(item, region)

        if not item_occurrences:
            return []

        matches = []

        if len(item_occurrences) == 1:
            # There is only one occurrence, no need to analyze its placement.
            item_match = item_occurrences[0]

            satisfies = self.pattern.check_constraints_for_bbox(item_match.box)

            if satisfies:
                # make a Match duplicating the only occurrence.
                m = Match2d(self.pattern,
                            precision=item_match.precision,
                            box=item_match.box,
                            component2match={0: item_match})
                matches.append(m)
            return matches

        # найти ряды элементов, одинаково выровненных вдоль заданного направления
        matches = self._find_lines(item_occurrences)

        return matches
