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

    start: int | None
    stop: int | None
    _range: range | None  # None for infinite ranges

    @classmethod
    def make(cls, value: 'int | str | list[Optional[int]] | tuple[Optional[int], Optional[int]] | open_range' = None) -> 'open_range':
        """ Universal single-value factory method.
             If a number is given, returns a point range.
             If a str is given, parses range from it.
             If an iterable is given, extracts first 2 items from it for a new range.
         """
        if value is None or isinstance(value, (int, float)):
            return cls(value, value)
        if isinstance(value, str):
            return cls.parse(value)
        if isinstance(value, open_range):
            return value  # no need to clone
        try:
            it = iter(value)
            values = [t[0] for t in zip(it, range(2))]  # take up to 2 items
            assert len(values) == 2, f"Expected an iterable of exactly 2 items in open_range.make(), got {values!r}"
            assert all(isinstance(value, (int, float, type(None))) for value in values), \
                f"Expected an iterable of numeric items in open_range.make(), got {values!r}"
            return cls(*values)
        except AttributeError:
            pass

    @classmethod
    def parse(cls, range_str: str):
        """ See more in description of `parse_range()` """
        return ns.parse_range(str(range_str))

    def __init__(self, start: int = None, stop=None):
        self.start = start
        self.stop = stop

        if start is not None and stop is not None:
            if start > stop:
                raise ValueError(f'Invalid empty range passed to open_range({start!r}, {stop!r})')
            self._range = range(start, stop + 1)
        else:
            self._range = None

    def __contains__(self, value):
        if self._range:
            return value in self._range

        if self.start is not None and value < self.start:
            return False
        if self.stop is not None and value > self.stop:
            return False
        return True

    def __iter__(self, *args, **kwargs):
        if self._range:
            return iter(self._range)

        raise ValueError(f'Cannot iterate infinite open_range')

    def __len__(self):
        if self._range:
            return len(self._range)

        raise ValueError(f'Cannot get length of infinite open_range')

    def __eq__(self, other):
        if isinstance(other, range):
            return self.start == other.start and self.stop == other.stop - 1
        if isinstance(other, open_range):
            return self.start == other.start and self.stop == other.stop
        return False

    def __str__(self) -> str:
        """Get string representation
        parseable back by `open_range.parse( '1..5')` """
        if self._range:
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
        return not self._range

    def is_point(self) -> bool:
        """ Check if the range is finite and has the length of 0 """
        return self.start is not None and self.start == self.stop

    def point(self) -> int | None:
        """ Get point coordinate if this range is really a point """
        if self.start is not None and self.start == self.stop:
            return self.start
        else:
            return None

    def intersect(self, *others: 'open_range') -> 'open_range | None':
        ranges = [self, *others]
        try:
            return open_range(
                start=max((x.start for x in ranges if x.start is not None), default=None),
                stop=min((x.stop for x in ranges if x.stop is not None), default=None),
            )
        except ValueError:
            # Got invalid/empty range.
            return None

    def union(self, *others: 'open_range') -> 'open_range':
        ranges = [self, *others]
        return open_range(
            start=(None
                   if any(x.start is None for x in ranges)
                   else min((x.start for x in ranges))
                   ),
            stop=(None
                  if any(x.stop is None for x in ranges)
                  else max((x.stop for x in ranges))
                  ),
        )

    def trimmed_at_left(self, value: int | None) -> 'open_range | None':
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

    def trimmed_at_right(self, value: int | None) -> 'open_range | None':
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
