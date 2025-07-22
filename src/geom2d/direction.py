from collections.abc import Iterable


class Direction:
    """ Direction in degrees.
    See constants below: 0 is Right, 90 is Up, 180 is Left, 270 is Down.
    Non-right angles not supported.
    """

    __slots__ = ('rotation', 'dx', 'dy', 'prop_name', )

    rotation: int
    dx: int
    dy: int
    prop_name: str  # name of property that a Box instance has in this direction.
    _instances: dict[int, 'Direction'] = {}

    @classmethod
    def get(cls, rotation) -> 'Direction':
        obj = cls._instances.get(rotation)
        if not obj:
            cls._instances[rotation] = (obj := Direction(rotation))
        return obj

    @classmethod
    def get_by_name(cls, prop_name) -> 'Direction | None':
        # Note: this assumes that all instances have been already registered.
        for d in cls.known_instances():
            if d.prop_name == prop_name:
                return d
        return None

    @classmethod
    def known_instances(cls) -> Iterable['Direction']:
        return cls._instances.values()

    def __init__(self, rotation=0) -> None:
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

    def __str__(self) -> str:
        return f'[{self.rotation}:{self.prop_name}]'

    def __repr__(self) -> str:
        return f'Direction(rotation={self.rotation}, prop_name={self.prop_name})'

    def __hash__(self):
        return self.rotation

    def __lt__(self, other):
        return isinstance(other, type(self)) and self.rotation < other.rotation


# define constants
RIGHT= Direction.get(0)
UP   = Direction.get(90)
LEFT = Direction.get(180)
DOWN = Direction.get(270)
