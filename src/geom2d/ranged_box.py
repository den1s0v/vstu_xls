# ranged_box.py

from geom2d.ranged_segment import RangedSegment
from geom2d.open_range import open_range
from geom2d.box import Box


class RangedBox:
    """Прямоугольник с диапазонными сторонами. Поддерживает неопределённые границы."""

    __slots__ = ("rx", "ry")

    def __init__(self,
                 rx: RangedSegment | int | tuple[int | None, int | None] = None,
                 ry: RangedSegment | int | tuple[int | None, int | None] = None
                 ):
        self.rx = RangedSegment.make(rx)
        self.ry = RangedSegment.make(ry)

    # @classmethod
    # def from_ranges(cls, x_range, y_range) -> 'RangedBox':
    #     return cls(RangedSegment(x_range), RangedSegment(y_range))

    @classmethod
    def from_box(cls, box: Box) -> 'RangedBox':
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

    def minimal_box(self) -> 'RangedBox':
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

    def maximal_box(self) -> 'RangedBox':
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

    def intersect(self, other: 'RangedBox') -> 'RangedBox':
        return RangedBox(
            self.rx.intersect(other.rx),
            self.ry.intersect(other.ry),
        )

    def union(self, other: 'RangedBox') -> 'RangedBox':
        return RangedBox(
            self.rx.union(other.rx),
            self.ry.union(other.ry),
        )

    def project(self, direction: str = 'h') -> RangedSegment:
        """ direction: 'h' - horizontal or 'v' - vertical """
        if direction.startswith('h'):
            # horizontal
            return self.rx
        else:
            # vertical
            return self.ry

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

    def __eq__(self, other):
        if isinstance(other, Box):
            other = self.from_box(other)
        if isinstance(other, type(self)):
            return self.rx == other.rx and self.ry == other.ry
        return False

    def __repr__(self):
        return f"RangedBox(rx=({self.left}, {self.right}), ry=({self.top}, {self.bottom}))"
