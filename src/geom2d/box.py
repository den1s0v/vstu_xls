from typing import Union, Optional, Self

from adict import adict

from geom1d import LinearRelation, LinearSegment
from geom2d.point import Point
from geom2d.size import Size
from geom2d.manhattan_distance import ManhattanDistance
from geom2d.direction import RIGHT, DOWN, Direction
from utils import reverse_if


class Box:
    """ Прямоугольник на целочисленной координатной плоскости (2d). `Box(x, y, w, h)`. """
    # Dev note: i'm avoiding subclassing namedtuple to allow usual inheritance via __init__, not __new__.

    __slots__ = ('_tuple',)

    # Dev note: using __slots__ tells CPython to not store object's data within __dict__.

    def __init__(self, x: int, y: int, w: int, h: int):
        self._tuple = (x, y, w, h)

    def as_tuple(self):
        return self._tuple

    def as_dict(self) -> dict:
        """ Get a dict representing all 6 parameters of the Box. """
        return {
            k: getattr(self, k)
            for k in ('left', 'top', 'w', 'h', 'right', 'bottom')
        }

    # staff that mimics behavior of `tuple`:
    def __len__(self):
        return 4

    def __getitem__(self, key):
        return self._tuple[key]

    def __iter__(self):
        return iter(self._tuple)

    def __hash__(self):
        return hash(self._tuple)

    def __eq__(self, other: 'Box'):
        if hasattr(other, '_tuple'):
            return self._tuple.__eq__(other._tuple)
        return other == self

    def __ne__(self, other: Self):
        return not self == other

    def __lt__(self, other: Self):
        if hasattr(other, '_tuple'):
            return self._tuple.__lt__(other._tuple)
        return NotImplemented

    def __le__(self, other: Self):
        if hasattr(other, '_tuple'):
            return self._tuple.__le__(other._tuple)
        return NotImplemented

    def __gt__(self, other: Self):
        if hasattr(other, '_tuple'):
            return self._tuple.__gt__(other._tuple)
        return NotImplemented

    def __ge__(self, other: Self):
        if hasattr(other, '_tuple'):
            return self._tuple.__ge__(other._tuple)
        return NotImplemented

    @property
    def x(self):
        return self._tuple[0]

    @property
    def y(self):
        return self._tuple[1]

    @property
    def w(self):
        return self._tuple[2]

    @property
    def h(self):
        return self._tuple[3]

    # other stuff.
    @classmethod
    def from_2points(cls, x1: int, y1: int, x2: int, y2: int) -> 'Box':
        """ Construct a new Box from two diagonal points (4 coordinates), no matter which diagonal.

        Args:
            x1 (int): left or right
            y1 (int): top or bottom
            x2 (int): right or left
            y2 (int): bottom or top

        Returns:
            Box: new instance
        """
        return cls(
            min(x1, x2),
            min(y1, y2),
            abs(x1 - x2),
            abs(y1 - y2),
        )

    @property
    def position(self):
        return Point(self.x, self.y)

    @property
    def size(self):
        return Size(self.w, self.h)

    @property
    def left(self):
        return self.x

    @property
    def right(self):
        return self.x + self.w

    @property
    def top(self):
        return self.y

    @property
    def bottom(self):
        return self.y + self.h

    def get_side_dy_direction(self, direction):
        return getattr(self, direction.prop_name)

    def __str__(self) -> str:
        return f'[({self.x},{self.y})→{self.w}x{self.h}]'

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}{str(self)}'

    def __contains__(self, other: 'Box | Point'):
        if isinstance(other, Box) or len(other) == 4 and (other := Box(*other)):
            return (
                    self.x <= other.x and
                    self.y <= other.y and
                    self.right >= other.right and
                    self.bottom >= other.bottom
            )
        if isinstance(other, Point) or len(other) == 2 and (other := Point(*other)):
            return (
                    self.x <= other.x < self.right and
                    self.y <= other.y < self.bottom
            )
        return False

    def overlaps(self, other):
        if isinstance(other, Box) or len(other) == 4 and (other := Box(*other)):
            return any(p in self for p in other.iterate_corners()) or \
                other in self or \
                self in other

        if isinstance(other, Point) or len(other) == 2 and (other := Point(*other)):
            return other in self
        return False

    def manhattan_distance_to(self, other: Union['Point', 'Box'], per_axis=False) -> int | ManhattanDistance:
        """ Расстояние городских кварталов, или манхеттенское расстояние между двумя точками на плоскости.
        Для прямоугольника: расстояние до касания, см. `Box.manhattan_distance_to_touch()`.
        Для точки: 0, если точка находится внутри прямоугольника, иначе минимальное количество единичных перемещений, чтобы точка попала на границу (внутрь) прямоугольника.
        """
        if isinstance(other, Box):
            return self.manhattan_distance_to_touch(other)

        if isinstance(other, Point):
            if other in self:
                return ManhattanDistance(0, 0) if per_axis else 0

            if (self.left <= other.x <= self.right):
                # ближе до стороны
                dy = min(abs(other.y - self.top), abs(other.y - self.bottom))
                return ManhattanDistance(0, dy) if per_axis else dy
            if (self.top <= other.y <= self.bottom):
                # ближе до стороны
                dx = min(abs(other.x - self.left), abs(other.x - self.right))
                return ManhattanDistance(dx, 0) if per_axis else dx
            # ближе до угла
            return min(
                corner.manhattan_distance_to(other, per_axis=per_axis)
                for corner in self.iterate_corners()
            )
        raise TypeError(other)

    def manhattan_distance_to_overlap(self, other: Union[Point, 'Box'], per_axis=False) -> int | ManhattanDistance:
        """ Целочисленное расстояние до максимального перекрытия:
            Для точки: 0, если точка находится внутри прямоугольника, иначе минимальное количество единичных перемещений, чтобы точка попала внутрь прямоугольника.
            Для прямоугольника: 0, если один из прямоугольников полностью вкладывается в другой, иначе минимальное количество единичных перемещений, чтобы совместить один из углов этих прямоугольников (таким образом, один оказывается внутри другого). В случае, если прямоугольники не могут быть перекрыты полностью из-за несовместимых размеров, эта метрика покажет расстояние до ближайшего максимально возможного перекрытия.
        Имеется в виду расстояние городских кварталов, или манхэттенское расстояние между двумя точками на плоскости. """
        if isinstance(other, Point):
            return other.manhattan_distance_to(self, per_axis=per_axis)

        if isinstance(other, Box):
            if other in self or self in other:
                return ManhattanDistance(0, 0) if per_axis else 0
            return min(
                corner1.manhattan_distance_to(corner2, per_axis=per_axis)
                for corner1, corner2 in zip(
                    self.iterate_corners(),
                    other.iterate_corners())
            )
        return None

    def manhattan_distance_to_touch(self, other: Union[Point, 'Box'], per_axis=False) -> int | ManhattanDistance:
        """ Целочисленное расстояние до ближайшего касания:
            Для точки: 0, если точка находится внутри прямоугольника, иначе минимальное количество единичных перемещений, чтобы точка попала на границу прямоугольника.
            Для прямоугольника: 0, если прямоугольники касаются или перекрываются, иначе минимальное количество единичных перемещений, чтобы они стали касаться сторонами или углами.
        Имеется в виду расстояние городских кварталов, или манхэттенское расстояние между двумя точками на плоскости. """
        if isinstance(other, Point):
            return other.manhattan_distance_to(self, per_axis=per_axis)

        if isinstance(other, Box):
            if other in self or self in other:
                return ManhattanDistance(0, 0) if per_axis else 0

            rel_h = LinearRelation(
                self.project('h'),
                other.project('h')
            )
            rel_v = LinearRelation(
                self.project('v'),
                other.project('v')
            )
            dx = max(0, rel_h.outer_gap)
            dy = max(0, rel_v.outer_gap)
            return ManhattanDistance(dx, dy) if per_axis else dx + dy
        return None

    def iterate_corners(self):
        yield Point(self.x, self.y)
        yield Point(self.right, self.top)
        yield Point(self.right, self.bottom)
        yield Point(self.left, self.bottom)

    def iterate_points0(self, per='rows', reverse=False, exclude_top_left=False):
        along_row = adict(range=(self.x, self.right), index=0)
        along_col = adict(range=(self.y, self.bottom), index=1)

        level1, level2 = (along_row, along_col) if per == 'rows' else (along_col, along_row)
        f = reversed if reverse else lambda x: x

        for i in f(range(*level1.range)):
            for j in f(range(*level2.range)):
                point = (i, j) if level1.index == 0 else (j, i)
                if exclude_top_left and point == (self.x, self.y):
                    continue

                yield Point(*point)

    def iterate_points(self, directions=(RIGHT, DOWN), exclude_top_left=False):
        """ Traverse all points within this rectangle.

        Args:
            directions (tuple, optional): Directions of traversal for main & secondary loop over 2D area. Second element of the 2-tuple may be omitted. Defaults to (RIGHT, DOWN).
            exclude_top_left (bool, optional): If True, top left corner won't be yielded. Defaults to False.

        Yields: Point
        """
        # repair `directions` if needed
        if not directions:
            directions = (RIGHT, DOWN)
        if isinstance(directions, Direction):
            directions = (directions,)
        if len(directions) == 1 or (directions[0].is_horizontal == directions[1].is_horizontal):
            d0 = directions[0]
            # add/set default/valid second direction
            directions = (d0, RIGHT if d0.is_vertical else DOWN)

        # Note the reversed order:
        # first direction to think about is inner loop indeed!
        level2, level1 = [
            adict(range=(
                # Границы для обратного и прямого направлений
                self.get_side_dy_direction(-abs(d)),
                self.get_side_dy_direction(abs(d)),
                # 1 # d.coordinate_sign,
            ),
                flip=(d.coordinate_sign < 0),
                index=(0 if d.is_horizontal else 1),
            )
            for d in directions
        ]

        ###
        # print((level1, level2))
        ###

        for i in reverse_if(range(*level1.range), level1.flip):
            for j in reverse_if(range(*level2.range), level2.flip):
                point = (i, j) if level1.index == 0 else (j, i)
                if exclude_top_left and point == (self.x, self.y):
                    continue
                ###
                # print(' → ', point)
                ###
                yield Point(*point)

    def project(self, direction='h') -> LinearSegment:
        """ direction: 'h' - horizontal or 'v' - vertical """
        if direction.startswith('h'):
            # horizontal
            return LinearSegment(self.x, length=self.w)
        else:
            # vertical
            return LinearSegment(self.y, length=self.h)

    def intersect(self, other: 'Box') -> Optional['Box']:
        """ Returns intersection of this and other box,
            or None if no intersection exists. """
        if (h := self.project('h').intersect(other.project('h'))) and \
                (v := self.project('v').intersect(other.project('v'))):
            return type(self)(h.a, h.size, v.a, v.size)
        return None

    def unite(self, *others: 'Box') -> 'Box':
        return type(self).union(self, *others)

    @classmethod
    def union(cls, *boxes: 'Box') -> 'Box':
        """ Returns union of given boxes,
            i.e. minimal box that contains all of them. """
        return cls.from_2points(
            min(b.x for b in boxes),
            min(b.y for b in boxes),
            max(b.right for b in boxes),
            max(b.bottom for b in boxes),
        )

    def perimeter(self) -> int:
        return (self.w + self.h) * 2
