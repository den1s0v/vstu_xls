from geom2d.box import Box
from geom2d.point import Point
from geom2d.size import Size


# deprecated
class VariBox(Box):
    """ Изменяемый Прямоугольник на целочисленной координатной плоскости (2d). `VariBox(x, y, w, h)`. """
    # Dev note: using updatable list here, not tuple as parent class does.

    __slots__ = ('_tuple')
    # Dev note: using __slots__ tells CPython to not store object's data within __dict__.

    def __init__(self, x: int, y: int, w: int, h: int):
        self._tuple = [x, y, w, h]  # it's actually a list!

    def as_tuple(self):
        return tuple(self._tuple)

    # staff that mimics behavior of `list`:
    def __setitem__(self, key, value): self._tuple[key] = value
    def __hash__(self): return hash(self.as_tuple())
    def __eq__(self, other): return self._tuple.__eq__(other._tuple)
    def __ne__(self, other): return self._tuple.__ne__(other._tuple)


    @Box.x.setter
    def x(self, value): self._tuple[0] = value
    @Box.y.setter
    def y(self, value): self._tuple[1] = value
    @Box.w.setter
    def w(self, value): self._tuple[2] = value
    @Box.h.setter
    def h(self, value): self._tuple[3] = value


    @Box.position.setter
    def position(self, point: Point):
        (self.x, self.y) = point

    @Box.size.setter
    def size(self, size: Size):
        (self.w, self.h) = size

    @Box.left.setter
    def left(self, value):
        """ Change position of left side. Keep width non-negative. """
        new_val = min(value, self.right)
        self.w -= (new_val - self.left)
        self.x = new_val

    @Box.right.setter
    def right(self, value):
        """ Change position of right side. Keep width non-negative. """
        new_val = max(value, self.left)
        self.w += (new_val - self.right)

    @Box.top.setter
    def top(self, value):
        """ Change position of top side. Keep hight non-negative. """
        new_val = min(value, self.bottom)
        self.h -= (new_val - self.top)
        self.y = new_val

    @Box.bottom.setter
    def bottom(self, value):
        """ Change position of bottom side. Keep hight non-negative. """
        new_val = max(value, self.top)
        self.h += (new_val - self.bottom)

    def grow_to_cover(self, other: Box | Point):
        """ Grow size so `other` box or oint is covered by this box. """
        self.left = min(self.x, other.x)
        self.top  = min(self.y, other.y)

        if isinstance(other, Box):
            self.right  = max(self.right, other.bottom)
            self.bottom = max(self.bottom, other.bottom)

        elif isinstance(other, Point):
            self.right  = max(self.right, other.x)
            self.bottom = max(self.bottom, other.y)
