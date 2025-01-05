from grammar2d import Terminal
from grammar2d.ElementMatcher import ElementMatcher
from grammar2d.Match2d import Match2d


class TerminalMatcher(ElementMatcher):
    element: Terminal

    def match(self) -> list[Match2d]:
        type_name = self.element.cell_type.name
        type_name = self.element.cell_type.name
        matches = []
        if type_name in self.grammar_matcher.type_to_cells:
            for cw in self.grammar_matcher.type_to_cells[type_name]:
                precision = cw.data['cell_matches'][type_name].confidence
                if precision < self.element.precision_threshold:
                    continue

                m = Match2d(self.element, precision=precision, box=cw, data=cw.data['cell_matches'][type_name])
                self.grammar_matcher.register_match(m)
                matches.append(m)

        return matches
