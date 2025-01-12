from dataclasses import dataclass

import geom2d.ranges as ns


@dataclass(repr=True, frozen=False)
class open_range:
    """Class that mimics behaviour of `range` object with step=1, but includes `stop` in the sequence.
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
    # _range: range | None  # None for infinite ranges

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

    def intersect(self, *others: tuple['open_range']):
        ranges = [self, *others]
        return open_range(
            start=max((x.start for x in ranges if x.start is not None), default=None),
            stop=min((x.stop for x in ranges if x.stop is not None), default=None),
        )
