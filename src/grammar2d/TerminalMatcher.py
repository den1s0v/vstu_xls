from dataclasses import dataclass

from grammar2d import Terminal
from grammar2d.PatternMatcher import PatternMatcher
from grammar2d.Match2d import Match2d


@dataclass
class TerminalMatcher(PatternMatcher):
    pattern: Terminal

    def find_all(self, region: Region = None) -> list[Match2d]:
        # type_name = self.element.cell_type.name
        type_name = self.pattern.cell_type.name
        gm = self.grammar_matcher  # short alias
        matches = []

        for cw in gm.type_to_cells.get(type_name) or ():
            precision = cw.data['cell_matches'][type_name].confidence
            if precision < self.pattern.precision_threshold:
                continue

            # make Match
            m = Match2d(self.pattern, precision=precision, box=cw, data=cw.data['cell_matches'][type_name])
            matches.append(m)

        return matches
