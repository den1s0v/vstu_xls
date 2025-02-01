from dataclasses import dataclass

from geom2d import Box
from grammar2d.Pattern2d import Pattern2d


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
    """
    Match of a `pattern` on a specific location expressed by `box`.
    """
    pattern: Pattern2d
    box: Box = None
    precision: float = None
    component2match: dict[str|int, 'Match2d'] = None
    data: dict = None

    def calc_precision(self) -> float:
        if self.precision is None:
            self.precision = self.pattern.score_of_match(self) / self.pattern.max_score()
        return self.precision

    def clone(self):
        """Make a shallow copy"""
        return Match2d(
            self.pattern,
            self.box,
            self.precision,
            dict(self.component2match),
            dict(self.data),
        )
