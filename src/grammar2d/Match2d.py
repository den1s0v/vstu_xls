from dataclasses import dataclass

from geom2d import Box
from grammar2d import GrammarElement


def filter_best_matches(matches: list['Match2d'], precision_ratio_cutoff=0.9) -> list['Match2d']:
    """Leave best matches only (default precision_ratio_cutoff == 0.9,
    i.e. matches having precision within top 10% from the best of the list)"""
    if len(matches) > 1:
        # drop worst matches…
        top_precision = max(m.precision for m in matches)
        precision_threshold = top_precision * precision_ratio_cutoff
        # reassign filtered list
        matches = [m for m in matches if m.precision >= precision_threshold]

    return matches


@dataclass()
class Match2d:
    element: GrammarElement
    component2match: dict[str, 'Match2d'] = None
    precision = None
    box: Box = None
    data: dict = None

    def calc_precision(self) -> float:
        if self.precision is None:
            self.precision = sum(
                comp_m.precision * self.element.component_by_name[name].weight
                for name, comp_m in self.component2match.items()
            ) / self.element.max_score()
        return self.precision

    def clone(self):
        """Make a shallow copy"""
        return Match2d(
            self.element,
            dict(self.component2match),
            self.precision,
            self.box,
            dict(self.data),
        )
