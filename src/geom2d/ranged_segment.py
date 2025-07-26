# ranged_segment.py
from typing import Self

from geom1d import LinearSegment
from geom2d.open_range import open_range


class RangedSegment:
    """ Открытый отрезок. 1D segment having open_range as each end, i.e. actual range may be not clearly determined. """
    __slots__ = ('a', 'b',)

    a: open_range
    b: open_range

    def __init__(self,
                 lower: 'open_range | int | str | list[Optional[int]] | tuple[Optional[int], Optional[int]]' = None,
                 upper: 'open_range | int | str | list[Optional[int]] | tuple[Optional[int], Optional[int]]' = None,
                 validate=True):
        lower = open_range.make(lower)
        upper = open_range.make(upper)

        assert isinstance(validate, bool), f"RangedSegment's `validate` param must be True or False, got: {validate!r}."
        if validate:
            lower, upper = self.validate_ranges(lower, upper)

        self.a = lower
        self.b = upper

    @staticmethod
    def validate_ranges(lower, upper) -> tuple[open_range, open_range]:
        """ Validate input ranges on RangedSegment creation.
         Raises ValueError or adjusts ranges as needed. """

        intersection = lower.intersect(upper)
        if intersection is not None:
            # Есть пересечение (накладка) в середине. Нужно ограничить средние границы.
            if lower.is_double_open() or upper.is_double_open():
                # Исключаем вариант, когда оба бесконечны (нечем ограничивать)
                pass
            elif lower.stop is not None and upper.start is None:
                # (_, N), (*, _)
                upper = upper.trimmed_at_left(lower.stop)
            elif upper.start is not None and lower.stop is None:
                # (_, *), (N, _)
                lower = lower.trimmed_at_right(upper.start)
            elif upper.start is not None and lower.stop is not None and not intersection.is_point():
                # (_, N), (N, _)
                raise ValueError(
                    f'RangedSegment cannot be created without valid range in the middle. Got: {lower!r}, {upper!r}.')
        elif lower > upper:
            raise ValueError(f'RangedSegment cannot be created using inverse ranges. Got: {lower!r}, {upper!r}.')

        return lower, upper

    def fix_ranges(self) -> Self:
        """ Apply validate_ranges() updating existing instance """
        try:
            self.a, self.b = self.validate_ranges(self.a, self.b)
        except ValueError:
            pass  # ignore errors
        return self

    def __bool__(self):
        """ If segment exists it should be always treated as True. """
        return True

    def __str__(self) -> str:
        """Get human-readable representation """
        return f"[{self.a}]——[{self.b}]"

    def __repr__(self) -> str:
        """Get string representation
        parseable back by direct eval """
        return f"{type(self).__name__}('{self.a}', '{self.b}')"

    def minimal_range(self) -> open_range:
        return open_range(self.a.stop, self.b.start)

    def maximal_range(self) -> open_range:
        return open_range(self.a.start, self.b.stop)

    def is_deterministic(self) -> bool:
        return self.a.is_point() and self.b.is_point()

    def is_open(self) -> bool:
        return self.a.is_open() or self.b.is_open()

    def covers(self, other: Self | LinearSegment) -> bool:
        """ Returns True iff given segment completely lies within area defined by this segment,
        i.e. other's ends belong to the probable area, including the borders."""
        return self.a.includes(other.a) and self.b.includes(other.b)

    def __eq__(self, other):
        if isinstance(other, RangedSegment):
            return self.a == other.a and self.b == other.b
        if isinstance(other, range):
            return self.a.point() == other.start and self.b.point() == other.stop - 1
        if isinstance(other, open_range):
            return self.a.point() == other.start and self.b.point() == other.stop
        return False

    @classmethod
    def make(cls,
             value: 'int | list[Optional[int]] | tuple[Optional[int], Optional[int]] | open_range | Self' = None,
             validate=True) -> Self | None:
        """ Universal single-value factory method.
             If a number is given, returns a zero-length segment.
             If a range is given, returns a deterministic segment from it.
             If an iterable is given, extracts first 2 items from it to make two ranges.
         """
        if value is None or isinstance(value, (int, float)):
            return cls(value, value)
        if isinstance(value, open_range):
            return cls(value.start, value.stop)
        if isinstance(value, cls):
            return value  # no need to clone
        try:
            it = iter(value)
            values = [t[0] for t in zip(it, range(2))]  # take up to 2 items
            assert len(values) == 2, f"Expected an iterable of exactly 2 items in RangedSegment.make(), got {values!r}"
            return cls(*values, validate=validate)
        except AttributeError:
            return None

    def with_materialized_ranges(self) -> Self:
        """ Materialize inner infinite edges of ranges"""
        lower, upper = self.a, self.b
        changed = False
        if lower.stop is None and lower.start is not None:
            lower = open_range(lower.start, lower.start)
            changed = True
        if upper.start is None and upper.stop is not None:
            upper = open_range(upper.stop, upper.stop)
            changed = True

        # make a new instance if changed
        return type(self)(lower, upper, validate=False) if changed else self

    def restricted_by_size(self, size: open_range | None) -> Self | None:
        """ Update segment to fit given size constraints:
        cut outer probable areas if too long,
        cut inner probable areas if too short.

        If the segment is not compatible with given size, return None.
        """
        if size is None or size.is_double_open():
            # no restriction
            return self

        lower, upper = self.a, self.b
        new_lower = (upper - size).intersect(lower)
        if new_lower is None:
            # invalid range for an edge
            return None
        new_upper = (lower + size).intersect(upper)
        if new_upper is None:
            # invalid range for an edge
            return None
        return RangedSegment(new_lower, new_upper)

    def intersect(self, *others: Self | None) -> Self | None:
        """Find intersection of both definite & probable areas.
        If nothing is found in common for definite area, `None` will be returned. """
        # others = [rs.with_materialized_ranges() for rs in others if rs]  # ???

        minimal_ranges = [rs.minimal_range() for rs in others if rs]
        maximal_ranges = [rs.maximal_range() for rs in others if rs]

        minimal_range = self.minimal_range().intersect(*minimal_ranges)
        if minimal_range is None:
            # Empty intersection.
            return None

        maximal_range = self.maximal_range().intersect(*maximal_ranges)
        if maximal_range is None:
            # Empty intersection.
            return None

        # Adjust intersected minimal range, so it will not go beyond the maximal range.
        minimal_range = minimal_range.intersect(maximal_range)

        if not minimal_range:
            # Empty intersection.
            return None

        lower = open_range(maximal_range.start, minimal_range.start)
        upper = open_range(minimal_range.stop, maximal_range.stop)

        return type(self)(lower, upper)

    def union(self, *others: Self | None) -> Self:
        """Find union of both definite & probable areas.
        If given segments do not overlap, the minimal segment covering all of them is returned. """
        others = [rs.with_materialized_ranges() for rs in others if rs]

        minimal_ranges = [rs.minimal_range() for rs in others if rs]
        maximal_ranges = [rs.maximal_range() for rs in others if rs]

        self_fixed = self.with_materialized_ranges()
        minimal_range = self_fixed.minimal_range().union(*minimal_ranges)
        maximal_range = self_fixed.maximal_range().union(*maximal_ranges)

        # Adjust intersected minimal range, so it will not go beyond the maximal range.
        minimal_range = minimal_range.intersect(maximal_range)

        lower = maximal_range.start, minimal_range.start
        upper = minimal_range.stop, maximal_range.stop

        return type(self)(lower, upper)

    def combine(self, *others: Self | None) -> Self | None:
        """Find combination to obtain a more well-defined segment.
          This will try to grow definite area but shrink probable area.
        If probable areas of given segments do not overlap, `None` will be returned.
        If definite areas of given segments do not overlap,
        the definite area of resulting segment will try to cover all of them,
         but the same time not to go beyond the edges of probable area.
        """
        # others = [rs.with_materialized_ranges() for rs in others if rs]  # ???

        minimal_ranges = [rs.minimal_range() for rs in others]
        maximal_ranges = [rs.maximal_range() for rs in others]

        minimal_range = self.minimal_range().union_limited(*minimal_ranges)
        if not minimal_range:
            # Empty intersection.
            return None

        maximal_range = self.maximal_range().intersect(*maximal_ranges)
        if not maximal_range:
            # Empty intersection.
            return None

        # Adjust intersected minimal range, so it will not go beyond the maximal range.
        minimal_range = minimal_range.intersect(maximal_range)

        if not minimal_range:
            # Empty intersection.
            return None

        lower = maximal_range.start, minimal_range.start
        upper = minimal_range.stop, maximal_range.stop

        return type(self)(lower, upper)
