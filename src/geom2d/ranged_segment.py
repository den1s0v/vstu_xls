# ranged_segment.py

from geom2d.open_range import open_range


class RangedSegment:
    """ Открытый отрезок. 1D segment having open_range as each end, i.e. actual range may be not clearly determined. """
    a: open_range
    b: open_range

    def __init__(self,
                 lower: 'open_range | int | list[Optional[int]] | tuple[Optional[int], Optional[int]]' = None,
                 upper: 'open_range | int | list[Optional[int]] | tuple[Optional[int], Optional[int]]' = None,
                 validate=False):
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
        if intersection is not None and not intersection.is_point():
            # Есть пересечение (накладка) в середине. Нужно ограничить средние границы.
            # Исключаем вариант, когда оба бесконечны (нечем ограничивать)
            if lower.stop is not None and upper.start is None:
                upper = upper.trimmed_at_left(lower.stop)
            elif upper.start is not None and lower.stop is None:
                lower = lower.trimmed_at_right(upper.start)
            elif upper.start is not None and lower.stop is not None:
                raise ValueError(f'RangedSegment cannot be created without valid range in the middle. Got: {lower!r}, {upper!r}.')
        elif lower > upper:
            raise ValueError(f'RangedSegment cannot be created using inverse ranges. Got: {lower!r}, {upper!r}.')
        return lower, upper

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
             value: 'int | list[Optional[int]] | tuple[Optional[int], Optional[int]] | open_range | RangedSegment' = None,
             validate=False) -> 'RangedSegment':
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
            return cls(*values, validate=validate)
        except AttributeError:
            pass

    def intersect(self, *others: 'RangedSegment | None') -> 'RangedSegment | None':
        """Find intersection of both definite & probable areas.
        If nothing is found in common for definite area, `None` will be returned. """
        minimal_ranges = [rs.minimal_range() for rs in others if rs]
        maximal_ranges = [rs.maximal_range() for rs in others if rs]

        minimal_range = self.minimal_range().intersect(*minimal_ranges)
        maximal_range = self.maximal_range().intersect(*maximal_ranges)

        if minimal_range is None or maximal_range is None:
            # Empty intersection.
            return None

        lower = maximal_range.start, minimal_range.start
        upper = minimal_range.stop, maximal_range.stop

        return type(self)(lower, upper)

    def union(self, *others: 'RangedSegment | None') -> 'RangedSegment':
        """Find union of both definite & probable areas.
        If given segments do not overlap, the minimal segment covering all of them is returned. """
        minimal_ranges = [rs.minimal_range() for rs in others if rs]
        maximal_ranges = [rs.maximal_range() for rs in others if rs]

        minimal_range = self.minimal_range().union(*minimal_ranges)
        maximal_range = self.maximal_range().union(*maximal_ranges)

        lower = maximal_range.start, minimal_range.start
        upper = minimal_range.stop, maximal_range.stop

        return type(self)(lower, upper)

    def combine(self, *others: 'RangedSegment | None') -> 'RangedSegment | None':
        """Find combination to obtain a more well-defined segment.
          This will try to grow definite area but shrink probable area.
        If probable areas of given segments do not overlap, `None` will be returned.
        If definite areas of given segments do not overlap,
        the definite area of resulting segment will cover all of them.
        """
        minimal_ranges = [rs.minimal_range() for rs in others if rs]
        maximal_ranges = [rs.maximal_range() for rs in others if rs]

        minimal_range = self.minimal_range().union_limited(*minimal_ranges)
        maximal_range = self.maximal_range().intersect(*maximal_ranges)

        if minimal_range is None or maximal_range is None:
            # Empty intersection.
            return None

        # Adjust intersected maximal range, so it will not fall inside the minimal one.
        maximal_range = maximal_range.union(minimal_range)

        lower = maximal_range.start, minimal_range.start
        upper = minimal_range.stop, maximal_range.stop

        return type(self)(lower, upper)
