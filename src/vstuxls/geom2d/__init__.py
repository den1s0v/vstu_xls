# geom2d
import operator
from functools import reduce

""" Двумерные примитивы для работы на прямоугольной сетке из ячеек.

    This module exposes all public names to be imported elsewhere like `from geom2d import Box`.
"""

from vstuxls.geom2d.box import Box
from vstuxls.geom2d.direction import DOWN, LEFT, RIGHT, UP, Direction
from vstuxls.geom2d.manhattan_distance import ManhattanDistance
from vstuxls.geom2d.open_range import open_range
from vstuxls.geom2d.partial_box import PartialBox
from vstuxls.geom2d.point import Point
from vstuxls.geom2d.ranged_box import RangedBox
from vstuxls.geom2d.ranged_segment import RangedSegment
from vstuxls.geom2d.ranges import parse_range, parse_size_range
from vstuxls.geom2d.size import Size
from vstuxls.geom2d.varibox import VariBox

# def sign(a):
#     return (a > 0) - (a < 0)

MAX_FLEXIBILITY = 999_999_999

def aggregate_flexibility_estimations(estimations) -> int:
    return min(
        MAX_FLEXIBILITY,
        reduce(
            operator.mul,
            estimations or (MAX_FLEXIBILITY,),
            1  # initial
        )
    )
