from collections import namedtuple


class Size(namedtuple('Size', ['w', 'h'])):
    """ Размер прямоугольника (w, h) на координатной плоскости (2d) """
    def __le__(self, other):
        return self.w <= other.w and self.h <= other.h

    def __str__(self) -> str:
        return f'{self.w}x{self.h}'
