# ranged_segment.py

from geom2d.open_range import open_range


class RangedSegment:
    a: open_range
    b: open_range

    def __init__(self,
                 lower: 'open_range | int | list[int] | tuple[int, int]' = None,
                 upper: 'open_range | int | list[int] | tuple[int, int]' = None):
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

    @classmethod
    def make(cls, value: 'int | list[int] | tuple[int, int] | open_range | RangedSegment' = None) -> 'RangedSegment':
        """ Universal single-value factory method.
             If a number is given, returns a zero-length segment.
             If a range is given, returns a deterministic segment from it.
             If an iterable is given, extracts first 2 items from it to make two ranges.
         """
        if value is None or isinstance(value, (int, float)):
            return cls(value, value)
        if isinstance(value, open_range):
            return cls(value.start, value.stop)
        if isinstance(value, RangedSegment):
            return value  # no need to clone
        try:
            it = iter(value)
            values = [t[0] for t in zip(it, range(2))]  # take up to 2 items
            assert len(values) == 2, f"Expected an iterable of exactly 2 items in RangedSegment.make(), got {values!r}"
            return cls(*values)
        except AttributeError:
            pass

    ...
