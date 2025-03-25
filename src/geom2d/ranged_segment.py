# ranged_segment.py

from geom2d.open_range import open_range


class RangedSegment:
    a: open_range
    b: open_range

    def __init__(self, lower: open_range = None, upper: open_range = None):
        lower = open_range.make(lower)
        upper = open_range.make(upper)

        self.a = lower.trimmed_at_right(upper.stop)
        self.b = upper.trimmed_at_left(lower.start)

    def minimal_range(self) -> open_range:
        return open_range(self.a.stop, self.b.start)

    def maximal_range(self) -> open_range:
        return open_range(self.a.start, self.b.stop)

    def is_deterministic(self) -> bool:
        return self.a.is_point() and self.b.is_point()

    ...
