# ranged_box.py
from functools import reduce
from typing import Self

from geom2d.ranged_segment import RangedSegment
from geom2d.open_range import open_range
from geom2d.box import Box


class RangedBox:
    """Прямоугольник с диапазонными сторонами. Поддерживает неопределённые границы."""

    __slots__ = ("rx", "ry")

    def __init__(self,
                 rx: RangedSegment | int | tuple[int | str | None, int | str | None] = None,
                 ry: RangedSegment | int | tuple[int | str | None, int | str | None] = None
                 ):
        self.rx = RangedSegment.make(rx)
        self.ry = RangedSegment.make(ry)

    # @classmethod
    # def from_ranges(cls, x_range, y_range) -> Self:
    #     return cls(RangedSegment(x_range), RangedSegment(y_range))

    @classmethod
    def from_box(cls, box: Box) -> Self:
        return cls(
            (box.left, box.right),
            (box.top, box.bottom),
        )
        # x = box.x
        # y = box.y
        # w = box.w
        # h = box.h
        # return cls(
        #     RangedSegment(open_range(x, x), open_range(x + w - 1, x + w - 1)),
        #     RangedSegment(open_range(y, y), open_range(y + h - 1, y + h - 1))
        # )

    def to_box(self) -> Box:
        if not self.is_deterministic():
            raise ValueError("Cannot convert non-deterministic RangedBox to Box.")
        x = self.left.point()
        y = self.top.point()
        r = self.right.point()
        b = self.bottom.point()
        return Box.from_2points(x, y, r, b)

    def is_deterministic(self) -> bool:
        return self.rx.is_deterministic() and self.ry.is_deterministic()

    def minimal_box(self) -> Self:
        return RangedBox(
            RangedSegment(
                open_range(self.rx.a.stop, self.rx.a.stop),
                open_range(self.rx.b.start, self.rx.b.start)
            ),
            RangedSegment(
                open_range(self.ry.a.stop, self.ry.a.stop),
                open_range(self.ry.b.start, self.ry.b.start)
            )
        )

    def maximal_box(self) -> Self:
        return RangedBox(
            RangedSegment(
                open_range(self.rx.a.start, self.rx.a.start),
                open_range(self.rx.b.stop, self.rx.b.stop)
            ),
            RangedSegment(
                open_range(self.ry.a.start, self.ry.a.start),
                open_range(self.ry.b.stop, self.ry.b.stop)
            )
        )

    def intersect(self, other: Self) -> Self | None:
        rx = self.rx.intersect(other.rx)
        ry = self.ry.intersect(other.ry)
        return RangedBox(rx, ry) if rx and ry else None

    def union(self, other: Self) -> Self:
        return RangedBox(
            self.rx.union(other.rx),
            self.ry.union(other.ry),
        )

    def combine(self, other: Self) -> Self | None:
        if not other or not self:
            return None
        rx = self.rx.combine(other.rx)
        if rx is None:
            return None
        ry = self.ry.combine(other.ry)
        if ry is None:
            return None
        return RangedBox(rx, ry)

    def restricted_by_size(self, hor_size: open_range, ver_size: open_range) -> Self | None:
        new_rx = self.rx.restricted_by_size(hor_size)
        if new_rx is None:
            # invalid range for an edge
            return None
        new_ry = self.ry.restricted_by_size(ver_size)
        if new_ry is None:
            # invalid range for an edge
            return None
        return RangedBox(new_rx, new_ry)

    def combine_many(self, *others: Self) -> Self | None:
        # f = RangedBox.combine
        f = type(self).combine
        return reduce(f, others, self)

    def project(self, direction: str = 'h') -> RangedSegment:
        """ direction: 'h' - horizontal or 'v' - vertical """
        if direction.startswith('h'):
            # horizontal
            return self.rx
        else:
            # vertical
            return self.ry

    def fix_ranges(self) -> Self:
        """ Apply validate_ranges() updating existing instance """
        self.rx.fix_ranges()
        self.ry.fix_ranges()
        return self

    # Свойства для совместимости с Box:
    @property
    def x(self): return self.left
    @property
    def y(self): return self.top
    @property
    def w(self): return self.width
    @property
    def h(self): return self.height

    @property
    def left(self): return self.rx.a
    @property
    def right(self): return self.rx.b
    @property
    def top(self): return self.ry.a
    @property
    def bottom(self): return self.ry.b

    @property
    def width(self): return self.rx.minimal_range()
    @property
    def height(self): return self.ry.minimal_range()

    @property
    def position(self): return (self.left, self.top)
    @property
    def size(self): return (self.width, self.height)

    def as_tuple(self):
        return self.left, self.top, self.width, self.height

    def as_dict(self):
        return {
            'x': self.left,
            'y': self.top,
            'w': self.width,
            'h': self.height,
            'right': self.right,
            'bottom': self.bottom,
        }

    def covers(self, other: Self | Box) -> bool:
        """ Returns True iff given box completely lies within area defined by this box,
        i.e. other's edges belong to the probable area, including the borders."""
        return self.rx.covers(other.rx) and self.ry.covers(other.ry)

    def __contains__(self, other):
        """ Returns True iff given box lies anywhere within probable area's outline """
        mb = self.maximal_box()
        return other.rx in mb.rx and other.ry in mb.ry

    def __hash__(self) -> int:
        return hash((hash(self.rx), hash(self.ry)))

    def __eq__(self, other):
        if isinstance(other, Box):
            other = self.from_box(other)
        if isinstance(other, type(self)):
            return self.rx == other.rx and self.ry == other.ry
        return False

    def __repr__(self):
        return f"RangedBox(rx=({self.left}, {self.right}), ry=({self.top}, {self.bottom}))"

    def __str__(self):
        if self.is_deterministic():
            return f"RangedBox(rx=({self.left}, {self.right}), ry=({self.top}, {self.bottom}) [deterministic])"
        return repr(self)

    def __bool__(self):
        """ If the box exists it should be always treated as True. """
        return True

    def empty(self):
        """ The box is empty iff at least one of its projections is empty. """
        return self.rx.is_point() or self.ry.is_point()
