class Direction:
    """ Direction in degrees.
    See constants below: 0 is Right, 90 is Up, 180 is Left, 270 is Down.
    Non-right angles not supported.
    """
    _cache = dict()
    rotation: int
    dx: int
    dy: int
    prop_name: str  # name of property that a Box instance has in this direction.

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


# define constants
RIGHT= Direction.get(0)
UP   = Direction.get(90)
LEFT = Direction.get(180)
DOWN = Direction.get(270)
