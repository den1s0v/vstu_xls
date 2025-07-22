from typing import Self

import geom2d.ranges as ns


class open_range:
    """Class that mimics behaviour of `range` object with step=1, but includes both `start` and `stop` in the sequence.
    This extends `range` to allow infinite limits (just pass `None` as `start` and/or `stop`).

    Constructor supports only full form: `open_range(start, stop)`,
    or use convertion from a string: `open_range.parse( '1..5')`.
    Each limit is assumed to be infinity if set to `None` or not passed.

    Please use as immutable (although no error is thrown on setting to attributes).

    Note: ordinary `range` cannot express true infinite bounds,
    so use this class when checking whether a value is in an open range.
    """

    __slots__ = ('start', 'stop', )

    start: int | None
    stop: int | None

    @classmethod
    def make(cls,
             value: 'int|str | list[Optional[int]] | tuple[Optional[int], Optional[int]] | open_range' = None) -> Self:
        """ Universal single-value factory method.
             If a number is given, returns a point range.
             If a str is given, parses range from it.
             If an iterable is given, extracts first 2 items from it for a new range.
         """
        if value is None or isinstance(value, (int, float)):
            return cls(value, value)
        if isinstance(value, open_range):
            return value  # no need to clone
        if isinstance(value, str):
            return cls.parse(value)
        try:
            it = iter(value)
            values = [t[0] for t in zip(it, range(2))]  # take up to 2 items
            assert len(values) == 2, f"Expected an iterable of exactly 2 items in open_range.make(), got {values!r}"
            assert all(isinstance(value, (int, float, type(None))) for value in values), \
                f"Expected an iterable of numeric items in open_range.make(), got {values!r}"
            return cls(*values)
        except AttributeError:
            raise ValueError(value)

    @classmethod
    def parse(cls, range_str: str):
        """ See more in description of `parse_range()` """
        return ns.parse_range(str(range_str))

    def __init__(self, start: int | None = None, stop: int | None = None):
        self.start = start
        self.stop = stop

        if start is not None and stop is not None and start > stop:
            raise ValueError(f'Invalid empty range passed to open_range({start!r}, {stop!r})')

    def __contains__(self, value: int) -> bool:
        if self.start is not None and value < self.start:
            return False
        if self.stop is not None and value > self.stop:
            return False
        return True

    def __iter__(self):
        if self.start is None or self.stop is None:
            raise ValueError(f'Cannot iterate infinite open_range')
        return iter(range(self.start, self.stop + 1))

    def __len__(self) -> int:
        if self.start is None or self.stop is None:
            raise ValueError(f'Cannot get length of infinite open_range')
        return self.stop - self.start + 1

    def __bool__(self) -> bool:
        """ If range exists it should be always treated as True. """
        return True

    def __eq__(self, other) -> bool:
        if isinstance(other, range):
            return self.start == other.start and self.stop == other.stop - 1
        if isinstance(other, open_range):
            return self.start == other.start and self.stop == other.stop
        return False

    def __str__(self) -> str:
        """Get string representation
        parseable back by `open_range.parse( '1..5')` """
        if self.start is not None and self.stop is not None:
            return f"{self.start}..{self.stop}"
        if self.start is not None:
            return f"{self.start}+"
        if self.stop is not None:
            return f"{self.stop}-"
        return '*'

    def __repr__(self) -> str:
        """Get string representation
        parseable back by direct eval """
        return f"open_range({self.start!r}, {self.stop!r})"

    # Arithmetics.
    def __add__(self, other):
        if isinstance(other, int):
            return open_range(
                self.start + other if self.start is not None else None,
                self.stop + other if self.stop is not None else None
            )
        if isinstance(other, open_range):
            b, e = other.start, other.stop
            return open_range(
                self.start + b if self.start is not None and b is not None else None,
                self.stop + e if self.stop is not None and e is not None else None
            )
        if isinstance(other, range):
            b, e = other.start, other.stop - 1
            return open_range(
                self.start + b if self.start is not None else None,
                self.stop + e if self.stop is not None else None
            )
        raise TypeError("<open_range> + <?>: int, open_range or range expected!")

    __radd__ = __add__

    def __sub__(self, other):
        try:
            return self + (0 - other)
        except TypeError:
            raise TypeError("<open_range> - <?>: int, open_range or range expected!")

    def __rsub__(self, other):
        """ "Negates" & changes orientation of the range! """
        if isinstance(other, int):
            return open_range(
                other - self.stop if self.stop is not None else None,
                other - self.start if self.start is not None else None,
            )
        if isinstance(other, open_range):
            b, e = other.start, other.stop
            return open_range(
                e - self.stop if self.stop is not None and e is not None else None,
                b - self.start if self.start is not None and b is not None else None,
            )
        if isinstance(other, range):
            b, e = other.start, other.stop - 1
            return open_range(
                e - self.stop if self.stop is not None else None,
                b - self.start if self.start is not None else None,
            )
        raise TypeError("<?> - <open_range>: int, open_range or range expected!")

    def __neg__(self):
        return 0 - self

    def __pos__(self):
        """ Effectively, just the same object """
        return self
        # return 0 + other  # cloning does not make sense

    def __lt__(self, other):
        """ Self is at left of the other range, no intersection """
        other = self.make(other)
        if self.stop is None or other.start is None:
            return False
        return self.stop < other.start

    def __le__(self, other):
        """ Self is at left of the other range or touches, no intersection """
        other = self.make(other)
        if self.stop is None or other.start is None:
            return False
        return self.stop <= other.start

    def __gt__(self, other):
        """ Self is at right of the other range, no intersection """
        other = self.make(other)
        if self.start is None or other.stop is None:
            return False
        return self.start > other.stop

    def __ge__(self, other):
        """ Self is at right of the other range or touches, no intersection """
        other = self.make(other)
        if self.start is None or other.stop is None:
            return False
        return self.start >= other.stop

    def is_open(self) -> bool:
        """ Check if the range is infinite (i.e. at least one side is None) """
        return self.start is None or self.stop is None

    def is_double_open(self) -> bool:
        """ Check if the range is infinite in both directions """
        return self.start is None and self.stop is None

    def is_point(self) -> bool:
        """ Check if the range is finite and has the length of 0 """
        return self.start is not None and self.start == self.stop

    def point(self) -> int | None:
        """ Get point coordinate if this range is really a point """
        if self.start is not None and self.start == self.stop:
            return self.start
        else:
            return None

    def intersect(self, *others: Self) -> Self | None:
        # Handle zero or one other ranges efficiently
        if not others:
            return self

        if len(others) == 1:
            other = others[0]
            # Calculate new_start
            if self.start is None:
                new_start = other.start
            elif other.start is None:
                new_start = self.start
            else:
                new_start = max(self.start, other.start)

            # Calculate new_stop
            if self.stop is None:
                new_stop = other.stop
            elif other.stop is None:
                new_stop = self.stop
            else:
                new_stop = min(self.stop, other.stop)

            # Check for empty intersection
            if new_start is not None and new_stop is not None and new_start > new_stop:
                return None
            return open_range(new_start, new_stop)

        # General case: multiple ranges
        new_start = self.start
        new_stop = self.stop

        for r in others:
            # Update new_start
            if r.start is not None:
                if new_start is None:
                    new_start = r.start
                elif r.start > new_start:
                    new_start = r.start

            # Update new_stop
            if r.stop is not None:
                if new_stop is None:
                    new_stop = r.stop
                elif r.stop < new_stop:
                    new_stop = r.stop

        # Final check for empty intersection
        if new_start is not None and new_stop is not None and new_start > new_stop:
            return None

        return open_range(new_start, new_stop)

    def union(self, *others: Self) -> Self:
        """Union of ranges:
        - If any range has None as start/stop, the result will have None for that bound
        - Otherwise takes min of starts and max of stops"""
        ranges = [self, *others]

        # Special case: single range
        if len(ranges) == 1:
            return self

        # Flags and trackers
        has_none_start = False
        has_none_stop = False
        min_start = None
        max_stop = None

        for r in ranges:
            # Process start
            if not has_none_start:
                if r.start is None:
                    has_none_start = True
                    min_start = None  # Stop tracking min
                else:
                    if min_start is None or r.start < min_start:
                        min_start = r.start

            # Process stop
            if not has_none_stop:
                if r.stop is None:
                    has_none_stop = True
                    max_stop = None  # Stop tracking max
                else:
                    if max_stop is None or r.stop > max_stop:
                        max_stop = r.stop

        return open_range(
            None if has_none_start else min_start,
            None if has_none_stop else max_stop
        )

    def union_limited(self, *others: Self) -> Self:
        """Union that ignores None (infinite) bounds"""
        ranges = [self, *others]

        # Special case: single range
        if len(ranges) == 1:
            return self

        min_start = None
        max_stop = None

        for r in ranges:
            # Process start (only non-None values)
            if r.start is not None:
                if min_start is None or r.start < min_start:
                    min_start = r.start

            # Process stop (only non-None values)
            if r.stop is not None:
                if max_stop is None or r.stop > max_stop:
                    max_stop = r.stop

        return open_range(min_start, max_stop)

    def trimmed_at_left(self, value: int | None) -> Self | None:
        if value is None:
            return self
        if value in self:
            return open_range(value, self.stop)
        else:
            if value < self:
                return self
            else:
                # Got invalid/empty range.
                return None

    def trimmed_at_right(self, value: int | None) -> Self | None:
        if value is None:
            return self
        if value in self:
            return open_range(self.start, value)
        else:
            if value > self:
                return self
            else:
                # Got invalid/empty range.
                return None
