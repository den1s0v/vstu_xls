from collections import namedtuple
from typing import Self

from geom2d.manhattan_distance import ManhattanDistance


class Point(namedtuple('Point', ['x', 'y'])):
    """Точка (x, y) на координатной плоскости (2d)"""
    def __str__(self) -> str:
        return f'({self.x},{self.y})'

    def distance_to(self, other: Self) -> float:
        """ "Диагональное" Евклидово расстояние между двумя точками на плоскости.
        Рассчитывается как длина гипотенузы. """
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5

    def manhattan_distance_to(self, other: Self, per_axis=False) -> int | ManhattanDistance:
        """ Расстояние городских кварталов, или манхеттенское расстояние между двумя точками на плоскости.
        Для точки: Рассчитывается как минимальное число ходов ладьёй для перемещения между двумя точками и равно сумме модулей разностей их координат.
        Для прямоугольника: 0, если точка находится внутри прямоугольника, иначе минимальное количество единичных перемещений, чтобы точка попала на границу (внутрь) прямоугольника.
        """
        if isinstance(other, Point):
            dx, dy = abs(self.x - other.x), abs(self.y - other.y)
            return ManhattanDistance(dx, dy) if per_axis else dx + dy
        try:
            return other.manhattan_distance_to(self, per_axis=per_axis)
        except AttributeError as exc:
            raise ValueError(f'Cannot calculate distance from `{type(self).__name__
            }` to `{type(other).__name__}`.', other, exc)
