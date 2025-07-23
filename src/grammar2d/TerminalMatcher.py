from dataclasses import dataclass

from geom2d import Box
from grammar2d import Terminal
from grammar2d.PatternMatcher import PatternMatcher
from grammar2d.Match2d import Match2d
from grid import Region
from string_matching import StringMatch
from utils import safe_adict


@dataclass
class TerminalMatcher(PatternMatcher):
    pattern: Terminal

    def find_all(self, region: Box = None, count_limit=None) -> list[Match2d]:
        # type_name = self.element.cell_type.name
        type_name = self.pattern.cell_type.name
        gm = self.grammar_matcher  # short alias
        matches = []

        for cw in gm.type_to_cells.get(type_name) or ():

            string_match: StringMatch = cw.data['cell_matches'][type_name]

            precision = string_match.confidence
            if precision < self.pattern.precision_threshold:
                continue

            position = string_match.confidence
            if precision < self.pattern.precision_threshold:
                continue

            # make Match
            m = Match2d(self.pattern, precision=precision, box=cw, data=safe_adict(
                    string_match=string_match,
                    cell_type=type_name,
                    text=string_match.text,
                 )
            )
            matches.append(m)

        return matches
