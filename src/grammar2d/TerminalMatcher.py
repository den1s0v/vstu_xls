from dataclasses import dataclass

from grammar2d import Terminal
from grammar2d.PatternMatcher import PatternMatcher
from grammar2d.Match2d import Match2d


@dataclass
class TerminalMatcher(PatternMatcher):
    pattern: Terminal

    def find_all(self) -> list[Match2d]:
        # type_name = self.element.cell_type.name
        type_name = self.pattern.cell_type.name
        matches = []
        if type_name in self.grammar_matcher.type_to_cells:
            for cw in self.grammar_matcher.type_to_cells[type_name]:
                precision = cw.data['cell_matches'][type_name].confidence
                if precision < self.pattern.precision_threshold:
                    continue

                m = Match2d(self.pattern, precision=precision, box=cw, data=cw.data['cell_matches'][type_name])
                self.grammar_matcher.register_match(m)
                matches.append(m)

        return matches
