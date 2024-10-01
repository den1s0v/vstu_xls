# geom2d.py

""" Двумерные примитивы для работы на прямоугольной сетке из ячеек """

from collections import namedtuple
from typing import Optional, Union

from adict import adict

from geom1d import LinearSegment
from utils import reverse_if

# def sign(a):
#     return (a > 0) - (a < 0)

class Direction:
    """ Direction in degrees.
    See constants below: 0 is Right, 90 is Up, 180 is Left, 270 is Down.
    Non-right angles not supported.
    """
    _cache = dict()
    rotation: int
    dx: int
    dy: int 
    prop_name: str # name of property that a Box instance has in this direction.
    
    @classmethod
    def get(cls, rotation) -> 'Direction':
        obj = cls._cache.get(rotation)
        if not obj:
            cls._cache[rotation] = (obj := Direction(rotation))
        return obj
    
    def __init__(self, rotation = 0) -> None:
        self.rotation = rotation
        self.dx, self.dy, self.prop_name = {
              0: ( 1,  0, 'right'),
             90: ( 0, -1, 'top'),
            180: (-1,  0, 'left'),
            270: ( 0,  1, 'bottom'),
        }.get(rotation) or (None, None, None)
        
    @property
    def is_horizontal(self) -> bool:
        return self.dy == 0
        
    @property
    def is_vertical(self) -> bool:
        return self.dx == 0
        
    @property
    def coordinate_sign(self) -> int:
        """ Returns +1 or -1 depending on the increase or decrease of the main coordinate when moving in this direction.
        """
        return self.dx if self.dy == 0 else self.dy
        
    def __add__(self, angle) -> 'Direction':
        return self.get((self.rotation + angle + 360) % 360)
        
    def __sub__(self, angle) -> 'Direction':
        return self.get((self.rotation - angle + 360) % 360)
        
    def opposite(self) -> 'Direction':
        """ Get diametrically opposite Direction """
        return self + 180
        
    def __neg__(self) -> 'Direction':
        """ Get diametrically opposite Direction """
        return self + 180
        
    def __abs__(self) -> 'Direction':
        """ Get this or diametrically opposite Direction, whatever is positive. """
        if self.coordinate_sign < 0:
            return self.opposite()
        return self
            
        

RIGHT= Direction.get(0)
UP   = Direction.get(90)
LEFT = Direction.get(180)
DOWN = Direction.get(270)



class Point(namedtuple('Point', ['x', 'y'])):
    """Точка (x, y) на координатной плоскости (2d)"""
    def __str__(self) -> str:
        return f'({self.x},{self.y})'


class Size(namedtuple('Size', ['w', 'h'])):
    """ Размер прямоугольника (w, h) на координатной плоскости (2d) """
    def __le__(self, other):
        return self.w <= other.w and self.h <= other.h

    def __str__(self) -> str:
        return f'{self.w}x{self.h}'


class Box:
    """ Прямоугольник на целочисленной координатной плоскости (2d). `Box(x, y, w, h)`. """
    # Dev note: no more subclassing namedtuple to allow usual inheritance via __init__, not __new__.
    
    __slots__ = ('__tuple')
    # Dev note: using __slots__ tells CPython to not to store object's data within __dict__.

    def __init__(self, x: int, y: int, w: int, h: int):
        self.__tuple = (x, y, w, h)
        
    def as_tuple(self):
        return self.__tuple
        
    # staff that mimics behavior ot `tuple`:
    def __len__(self): return 4
    def __getitem__(self, key): return self.__tuple[key]
    def __iter__(self): return iter(self.__tuple)
    def __hash__(self): return hash(self.__tuple)
    def __eq__(self, other): return self.__tuple.__eq__(other)
    def __ne__(self, other): return self.__tuple.__ne__(other)
    # def __lt__(self, other): return self.__tuple.__lt__(other)
    # def __le__(self, other): return self.__tuple.__le__(other)
    # def __gt__(self, other): return self.__tuple.__gt__(other)
    # def __ge__(self, other): return self.__tuple.__ge__(other)
        
    @property
    def x(self): return self.__tuple[0]
    @property
    def y(self): return self.__tuple[1]
    @property
    def w(self): return self.__tuple[2]
    @property
    def h(self): return self.__tuple[3]

    # other stuff.
    @staticmethod
    def from_2points(x1: int, y1: int, x2: int, y2: int) -> 'Box':
        """ Construct a new Box from two diagonal points (4 coordinates), no matter which diagonal.

        Args:
            x1 (int): left or right
            y1 (int): top or bottom
            x2 (int): right or left
            y2 (int): bottom or top

        Returns:
            Box: new instance
        """
        return Box(
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
    def left(self): return self.x

    @property
    def right(self): return self.x + self.w

    @property
    def top(self): return self.y

    @property
    def bottom(self): return self.y + self.h

    def get_side_dy_direction(self, direction):
        return getattr(self, direction.prop_name)
    
    def __str__(self) -> str:
        return f'[({self.x},{self.y})→{self.w}x{self.h}]'


    def __contains__(self, other):
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

    def relates_to(self, other):
        ...

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

    def iterate_points(self, directions = (RIGHT, DOWN), exclude_top_left=False):
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
            directions = (directions, )
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
                    self.get_side_dy_direction( abs(d)),
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
            return Box(h.a, h.b, v.a, v.b)
        return None

