from dataclasses import dataclass


@dataclass(repr=True)
class open_range:
    """Class that mimics behaviour of `range` object with step=1, but includes `stop` in the sequence.
    This extends `range` to allow infinite limits (just pass `None` as `start` and/or `stop`).

    Constructor supports only full form: `open_range(start, stop)`.
    Each limit is assumed to be infinity if set tO None or not passed .
    Note: `range` cannot express true infinite bounds, so use practically reliable positive `inf_value`.
    """

    start: int | None
    stop: int | None
    _range: range | None  # None for infinite ranges

    def __init__(self, start=None, stop=None):
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

