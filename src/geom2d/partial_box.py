from geom2d.box import Box
from geom2d.point import Point
from geom2d.size import Size

# deprecated
class PartialBox(Box):
    """ НЕизменяемый, но в общем случае не полностью определённый Прямоугольник на целочисленной координатной плоскости (2d).
        Изменение возможно только в части до-определения незаданных координат прямоугольника.
        `PartialBox(left, top, w, h, right, bottom)`. All args are optional. """
    # Dev note: using updatable list here, not tuple as parent class does.

    __slots__ = ('_tuple')
    # Dev note: using __slots__ tells CPython to not store object's data within __dict__.

    def __init__(self,
                 left: int = None, top: int = None,
                 w: int = None, h: int = None,
                 right: int = None, bottom: int = None):
        # Set everything from input & try to deduce unset properties.
        self._tuple = [None, None, None, None, None, None]  # it's actually a list!
        for key in ('left', 'top', 'w', 'h', 'right', 'bottom'):
            val = locals()[key]
            if val is not None:
                setattr(self, key, val)
        #### self._tuple = [left, top, w, h, right, bottom]  # don`t set directly

    def as_tuple(self):
        return tuple(self._tuple[:4])

    # staff that mimics behavior of `list`:
    def __iter__(self): return iter(self.as_tuple())
    def __hash__(self): return hash(self.as_tuple())
    def __eq__(self, other):
        if isinstance(other, Box):
            return self.as_tuple() == other.as_tuple()
        return self.as_tuple() == tuple(other)
    # def __ne__(self, other): return not self == other

    def __setitem__(self, key, value):
        """ set if empty of raise if this item was set before """
        # if self._tuple[key] is not None:
        #     raise RuntimeError(f'Attempt to set not-None element `{key}` of {repr(self)} !')
        if self._tuple[key] is not None:
            if self._tuple[key] != value:
                raise ValueError(f'Attempt to change not-None element `{key}` to `{value}` within write-once {repr(self)} !')
            # Ignore the case of setting the same value.
        else:
            self._tuple[key] = value

    def as_dict(self) -> dict:
        """ Get a dict representing all 6 parameters of the Box.
            A key is present iff this item was set before and is not None """
        dct = {}
        for k in ('left', 'top', 'w', 'h', 'right', 'bottom'):
            v = getattr(self, k)
            if v is not None:
                dct[k] = v
        return dct

    # redefine `right` & `bottom` properties (setters: see below)
    @property
    def right(self): return self._tuple[4]
    @property
    def bottom(self): return self._tuple[5]

    def __str__(self) -> str:
        return f'[({self.x},{self.y})+{self.w}x{self.h}→({self.right},{self.bottom})]'

    @Box.x.setter
    def x(self, value): self.left = value  # redirect to advanced setter (see below)
    @Box.y.setter
    def y(self, value): self.top = value  # redirect to advanced setter (see below)

    @Box.w.setter
    def w(self, value):
        assert value is not None and value >= 0, value
        self[2] = value
        # infer other coordinates if possible
        if self.left is not None:
            # self.right =
            self[4] = self.left + value
        elif self.right is not None:
            # self.left =
            self[0] = self.right - value

    @Box.h.setter
    def h(self, value):
        assert value is not None and value >= 0, value
        self[3] = value
        # infer other coordinates if possible
        if self.top is not None:
            # self.bottom =
            self[5] = self.top + value
        elif self.bottom is not None:
            # self.top =
            self[1] = self.bottom - value


    @Box.left.setter
    def left(self, value):
        """ Set position of left side. Raises if already set, or when wigth becomes < 0. """
        assert value is not None
        self[0] = value
        # infer other coordinates if possible
        if self.right is not None:
            assert value <= self.right, (value, self.right)
            # self.w =
            self[2] = self.right - value
        elif self.w is not None:
            # self.right =
            self[4] = value + self.w

    @Box.top.setter
    def top(self, value):
        """ Set position of top side. Raises if already set, or when hight becomes < 0. """
        assert value is not None
        self[1] = value
        # infer other coordinates if possible
        if self.bottom is not None:
            assert value <= self.bottom, (value, self.bottom)
            # self.h =
            self[3] = self.bottom - value
        elif self.h is not None:
            # self.bottom =
            self[5] = value + self.h

    @right.setter
    def right(self, value):
        """ Set position of right side. Raises if already set, or when wigth becomes < 0. """
        assert value is not None
        self[4] = value
        # infer other coordinates if possible
        if self.left is not None:
            assert self.left <= value, (self.left, value)
            # self.w =
            self[2] = value - self.left
        elif self.w is not None:
            # self.left =
            self[0] = value - self.w

    @bottom.setter
    def bottom(self, value):
        """ Set position of bottom side. Raises if already set, or when hight becomes < 0. """
        assert value is not None
        self[5] = value
        # infer other coordinates if possible
        if self.top is not None:
            assert self.top <= value, (self.top, value)
            # self.h =
            self[3] = value - self.top
        elif self.h is not None:
            # self.top =
            self[1] = value - self.h


    @Box.position.setter
    def position(self, point: Point):
        (self.x, self.y) = point

    @Box.size.setter
    def size(self, size: Size):
        (self.w, self.h) = size
