from dataclasses import dataclass, field
from typing import Self

from adict import adict

from utils import sorted_list, safe_adict
from geom2d import Box
from geom2d import Point
import grammar2d.Pattern2d as pt


@dataclass()
class Match2d:
    """
    Match of a `pattern` on a specific location expressed by `box`.
    """
    pattern: 'pt.Pattern2d'
    box: Box = None
    precision: float = None  # must be in range [0..1]
    component2match: dict['str|int', Self] = None
    data: adict = field(default_factory=safe_adict)

    def __post_init__(self):
        if not self.box:
            # try to infer from components
            self.recalc_box()

    def calc_precision(self, force=False) -> float:
        if self.precision is None or force:
            self.precision = self.pattern.score_of_match(self) / self.pattern.max_score()
        return self.precision

    def get_occupied_points(self) -> list[Point]:
        return self.pattern.get_points_occupied_by_match(self)

    def get_text(self) -> list[str]:
        return self.pattern.get_text_of_match(self)

    def get_content(self) -> dict | list | str:
        return self.pattern.get_content_of_match(self)

    def get_children(self) -> list[Self]:
        return list(self.component2match.values()) if self.component2match else []

    def recalc_box(self) -> Self:
        """ Calc bounding box of this match from components (Pattern-dependent).
        Returns match itself, not Box. """
        self.box = self.pattern.recalc_box_for_match(self)
        return self

    def clone(self):
        """Make a shallow copy"""
        return Match2d(
            self.pattern,
            self.box,
            self.precision,
            dict(self.component2match),
            adict(self.data),
        )

    def __contains__(self, item) -> bool:
        return item in self.component2match

    def __getitem__(self, item) -> Self:
        return self.component2match[item]

    def __str__(self) -> str:
        return "%s(%s)" % (type(self).__name__, repr(self.__dict__()))

    def __repr__(self) -> str:
        return str(self)

    def __dict__(self) -> dict:
        """ For repr / pretty printing """
        return dict(
            pattern=self.pattern.name,
            box=self.box,
            precision=self.precision,
            component2match=self.component2match,
            data=self.data,
        )

    def __lt__(self, other: Self) -> bool:
        return (self.box.position < other.box.position) if hasattr(other, 'box') else False


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

