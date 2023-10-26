# geom2d.py

""" Двумерные примитивы для работы на прямоугольной сетке из ячеек """

from collections import namedtuple

from adict import adict

from geom1d import LinearSegment


# def sign(a):
#     return (a > 0) - (a < 0)


# точка на координатной плоскости
Point = namedtuple('Point', ['x', 'y'])
Point.__doc__ = 'точка на координатной плоскости'

Size = namedtuple('Size', ['w', 'h'])


class Box(namedtuple('Box', ['x', 'y', 'w', 'h'], defaults=(0, 0, 1, 1))):
    """ Прямоугольник на координатной плоскости (2d) """

    def __getattr__(self, key):
        if key in ('point', 'p', 'xy'):
            return Point(self.x, self.y)
        if key in ('size', 'wh'):
            return Size(self.w, self.h)
        return super().__getattr__(key)

    def __contains__(self, other):
        if isinstance(other, Box) or len(other) == 4 and (other := Box(other)):
            return (
                    self.x <= other.x and
                    self.y <= other.y and
                    self.x + self.w >= other.x + other.w and
                    self.y + self.h >= other.y + other.h
            )
        if isinstance(other, Point) or len(other) == 2 and (other := Point(other)):
            return (
                    self.x <= other.x < self.x + self.w and
                    self.y <= other.y < self.y + self.h
            )

    def overlaps(self, other):
        if isinstance(other, Box) or len(other) == 4 and (other := Box(*other)):
            return any(p in self for p in other.iterate_corners()) or \
                   other in self or \
                   self in other

        if isinstance(other, Point) or len(other) == 2 and (other := Point(*other)):
            return other in self

    def relates_to(self, other):
        ...

    def iterate_corners(self):
        yield Point(self.x, self.y)
        yield Point(self.x + self.w, self.y)
        yield Point(self.x + self.w, self.y + self.h)
        yield Point(self.x, self.y + self.h)

    def iterate_points(self, per='rows', reverse=False, exclude_top_left=False):
        along_row = adict(range=(self.x, self.x + self.w), index=0)
        along_col = adict(range=(self.y, self.y + self.h), index=1)

        level1, level2 = (along_row, along_col) if per == 'rows' else (along_col, along_row)
        f = reversed if reverse else lambda x: x

        for i in f(range(*level1.range)):
            for j in f(range(*level2.range)):
                point = (i, j) if level1.index == 0 else (j, i)
                if exclude_top_left and point == (self.x, self.y):
                    continue

                yield Point(*point)

    def project(self, direction='horizontal') -> LinearSegment:
        if direction.startswith('h'):
            # horizontal
            return LinearSegment(self.x, length=self.w)
        else:
            # vertical
            return LinearSegment(self.y, length=self.h)
