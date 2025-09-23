class ManhattanDistance:
    """ Расстояние городских кварталов, или манхеттенское расстояние между двумя точками на плоскости.
    Для точки: Рассчитывается как минимальное число ходов ладьёй для перемещения между двумя точками
    и равно сумме модулей разностей их координат. """
    __slots__ = ('x', 'y')

    def __init__(self, tuple_or_x, y=None):
        if isinstance(tuple_or_x, (tuple, list)):
            self.x, self.y = tuple_or_x
        else:
            assert y is not None, repr(y)
            self.x, self.y = tuple_or_x, y

    def __int__(self):
        return self.x + self.y

    def __str__(self):
        return f"[dx={self.x}, dy={self.y}]"

    __repr__ = __str__

    def __iter__(self):
        return iter((self.x, self.y))

    def __eq__(self, other: 'int|ManhattanDistance'):
        if isinstance(other, int):
            return int(self) == other
        else:  # if isinstance(other, ManhattanDistance):
            return tuple(self) == tuple(other)

    def __lt__(self, other: 'int|ManhattanDistance'):
        return int(self) < int(other)

    def __gt__(self, other: 'int|ManhattanDistance'):
        return int(self) > int(other)
