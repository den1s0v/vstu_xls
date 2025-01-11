# geom2d

""" Двумерные примитивы для работы на прямоугольной сетке из ячеек.

    This module exposes all public names to be imported elsewhere like `from geom2d import Box`.
"""

from geom2d.box import Box
from geom2d.direction import Direction, LEFT, RIGHT, UP, DOWN
from geom2d.manhattan_distance import ManhattanDistance
from geom2d.partial_box import PartialBox
from geom2d.point import Point
from geom2d.size import Size
from geom2d.varibox import VariBox
from geom2d.utils import parse_range, parse_size_range
from geom2d.open_range import open_range


# def sign(a):
#     return (a > 0) - (a < 0)


