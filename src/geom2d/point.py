from collections import namedtuple
from typing import Union

if False: from geom2d.box import Box
from geom2d.manhattan_distance import ManhattanDistance

class Point(namedtuple('Point', ['x', 'y'])):
    """Точка (x, y) на координатной плоскости (2d)"""
    def __str__(self) -> str:
        return f'({self.x},{self.y})'

    def distance_to(self, other: 'Point') -> float:
        """ "Диагональное" Евклидово расстояние между двумя точками на плоскости.
        Рассчитывается как длина гипотенузы. """
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5

    def manhattan_distance_to(self, other: Union['Point', 'Box'], per_axis=False) -> int:
        """ Расстояние городских кварталов, или манхеттенское расстояние между двумя точками на плоскости.
        Для точки: Рассчитывается как минимальное число ходов ладьёй для перемещения между двумя точками и равно сумме модулей разностей их координат.
        Для прямоугольника: 0, если точка находится внутри прямоугольника, иначе минимальное количество единичных перемещений, чтобы точка попала на границу (внутрь) прямоугольника.
        """
        if isinstance(other, Point):
            dx, dy = abs(self.x - other.x), abs(self.y - other.y)
            return ManhattanDistance(dx, dy) if per_axis else dx + dy

        from geom2d.box import Box

        if isinstance(other, Box):
            if self in other:
                return ManhattanDistance(0, 0) if per_axis else 0

            if (other.left <= self.x <= other.right):
                # ближе до стороны
                dy = min(abs(self.y - other.top), abs(self.y - other.bottom))
                return ManhattanDistance(0, dy) if per_axis else dy
            if (other.top <= self.y <= other.bottom):
                # ближе до стороны
                dx = min(abs(self.x - other.left), abs(self.x - other.right))
                return ManhattanDistance(dx, 0) if per_axis else dx
            # ближе до угла
            return min(
                corner.manhattan_distance_to(self, per_axis=per_axis)
                for corner in other.iterate_corners()
            )
