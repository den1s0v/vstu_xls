# geom2d.py

""" Двумерные примитивы для работы на прямоугольной сетке из ячеек """

from collections import namedtuple
from dataclasses import dataclass

from adict import adict


def sign(a):
    return (a > 0) - (a < 0)


# точка на координатной плоскости
Point = namedtuple('Point', ['x', 'y'])
Point.__doc__ = 'точка на координатной плоскости'

Size = namedtuple('Size', ['w', 'h'])


# Имитирует интерфейс tuple
class LinearSegment:
    """Отрезок AB на прямой (1D) - две целых координаты (a <= b)"""

    def __init__(self, a, b=None, length=None):
        if b is None:
            assert length is not None, 'LinearSegment(a, [b] [,length]) ' \
                                       'cannot be created without b and length specified.'
            b = a + length
        assert a <= b, 'Segment [{},{}] has negative length!'.format(a, b)
        self.a = a
        self.b = b
        # super().__init__()

    def __getitem__(self, index):
        if index == 0:
            return self.a
        if index == 1:
            return self.b
        raise IndexError(index)

    def __iter__(self):
        return iter((self.a, self.b))

    def __len__(self):
        return 2


# @dataclass
class GenericRelation:
    description = 'соотносится с'

    def implies(cls, other_cls: type):
        return issubclass(cls, other_cls)

    def format_description(self, a=None, b=None, vertical=False):
        s = self.description
        if vertical:
            s = s.replace('слева', 'сверху') \
                .replace('справа', 'снизу') \
                .replace('левую', 'верхнюю') \
                .replace('правую', 'нижнюю')
        if a and b:
            if '{}' not in s:
                s = '{} %s {}' % s
            return s.format(a, b)
        return s


### Внутренние ###

# @dataclass
class Overlaps(GenericRelation):
    description = 'пересекается с'


# @dataclass
class Includes(Overlaps):
    description = 'включает'


# @dataclass
class IncludedIn(Overlaps):
    description = 'входит в'


# @dataclass
class TouchesInternally(IncludedIn):
    description = 'имеет общую стенку'


# @dataclass
class TouchesInternallyLeft(TouchesInternally):
    description = 'имеет общую левую стенку с'


# @dataclass
class TouchesInternallyRight(TouchesInternally):
    description = 'имеет общую правую стенку с'


# @dataclass
class IncludesGluedLeft(TouchesInternallyLeft, Includes, ):
    description = 'включает примыкающее слева'


# @dataclass
class IncludesGluedRight(TouchesInternallyRight, Includes, ):
    description = 'включает примыкающее справа'


# @dataclass
class IncludedInGluesLeft(TouchesInternallyLeft, IncludedIn, ):
    description = 'включается, примыкая слева, в'


# @dataclass
class IncludedInGluesRight(TouchesInternallyRight, IncludedIn, ):
    description = 'включается, примыкая справа, в'


# @dataclass
class CoinsidesWith(IncludesGluedLeft, IncludesGluedRight, IncludedInGluesLeft, IncludedInGluesRight):
    description = 'совпадает с'


### Внешние ###

# @dataclass
class NoOverlap(GenericRelation):
    description = 'не пересекается с'


# @dataclass
class AtLeftFrom(NoOverlap):
    description = 'слева от'


# @dataclass
class AtRightFrom(NoOverlap):
    description = 'справа от'


# @dataclass
class Touches(NoOverlap):
    description = 'примыкает к'


# @dataclass
class TouchesAtLeft(Touches, AtRightFrom):
    description = 'примыкает слева к'


# @dataclass
class TouchesAtRight(Touches, AtLeftFrom):
    description = 'примыкает справа к'


# @dataclass
class FarFrom(NoOverlap):
    description = 'на удалении от'


# @dataclass
class FarFromAtLeft(FarFrom, AtLeftFrom):
    description = 'на удалении слева от'


# @dataclass
class FarFromAtRight(FarFrom, AtRightFrom):
    description = 'на удалении справа от'


class LinearRelation:
    """" Способ описать пространственное взаимоотношение
    одного отрезка на прямой (AB) по отношению к другому (CD)
        Равны:
            a----b
            c----d
        Включает:
            a------b
              c-d
        Включается:
              a-b
            c-----d
        Слева на расстоянии:
            a----b
                    c----d
        Справа на расстоянии:
                    a----b
            c----d
        Слева, примыкая:
            a----b
                 c----d
        Справа, примыкая:
                 a----b
            c----d
        Пересекает слева:
            a-----b
               c----d
        Пересекает справа:
               a----b
            c----d

    kind: class
    description: str
    equals: bool = None
    includes: bool = None
    included: bool = None
    overlaps: bool = None

    outer_gap: int = None
    outer_gap_left: int = None
    outer_gap_right: int = None
    indent_inner_left: int = None
    indent_inner_right: int = None
    """

    def __init__(self, s1: LinearSegment, s2: LinearSegment):
        self.s1 = s1
        self.s2 = s2
        a, b = s1
        c, d = s2
        # find distance between points: c-a, b-d (inside)
        # Внутренние отступы (левый и правый): >= 0, когда AB включает CD
        il = c - a
        ir = b - d
        # find distance between points: a-d, c-b (outside)
        # Внешние зазоры: >= 0, когда AB и CD не пересекаются (== 0: примыкают)
        gl = a - d
        gr = c - b

        self.inner_offset_left = il
        self.inner_offset_right = ir
        self.outer_gap_left = gl
        self.outer_gap_right = gr
        self.outer_gap = max(gl, gr)
        self.kind = GenericRelation
        self.description = None

        if il >= 0 <= ir:
            self.includes = True
            self.kind = Includes

            if il == 0 and ir == 0:
                self.included = True
                self.equals = True
                self.kind = CoinsidesWith
            if il == 0 and ir > 0:
                self.kind = IncludesGluedLeft
            elif il > 0 and ir == 0:
                self.kind = IncludesGluedRight

        elif il <= 0 >= ir:
            self.included = True
            self.kind = IncludedIn

            if il == 0 and ir < 0:
                self.kind = IncludedInGluesLeft
            elif il < 0 and ir == 0:
                self.kind = IncludedInGluesRight

        elif gl > 0:
            self.kind = FarFromAtRight
        elif gl == 0:
            self.kind = TouchesAtRight  # AB касается левого края CD, будучи при этом справа от него

        elif gr > 0:
            self.kind = FarFromAtLeft
        elif gr == 0:
            self.kind = TouchesAtLeft
        else:
            # fallback
            self.kind = Overlaps

        self.description = self.kind.description


class Box(namedtuple('Box', ['x', 'y', 'w', 'h'], defaults=(0, 0, 1, 1))):
    """ Прямоугольник на координатной плоскости (2d) """

    def __getattr__(self, key):
        if key in ('point', 'p', 'xy'):
            return Point(self.x, self.y)
        if key in ('size', 'wh'):
            return Size(self.w, self.h)
        return super().__getattr__(key)

    def __contains__(self, other):
        if isinstance(other, Box) or len(other) == 4 and (other := Box(other)):
            return (
                    self.x <= other.x and
                    self.y <= other.y and
                    self.x + self.w >= other.x + other.w and
                    self.y + self.h >= other.y + other.h
            )
        if isinstance(other, Point) or len(other) == 2 and (other := Point(other)):
            return (
                    self.x <= other.x < self.x + self.w and
                    self.y <= other.y < self.y + self.h
            )

    def overlaps(self, other):
        if isinstance(other, Box) or len(other) == 4 and (other := Box(*other)):
            return any(p in self for p in other.iterate_corners())

        if isinstance(other, Point) or len(other) == 2 and (other := Point(*other)):
            return other in self

    def relates_to(self, other):
        ...

    def iterate_corners(self):
        yield Point(self.x, self.y)
        yield Point(self.x + self.w, self.y)
        yield Point(self.x + self.w, self.y + self.h)
        yield Point(self.x, self.y + self.h)

    def iterate_points(self, per='rows', reverse=False, exclude_top_left=False):
        along_row = adict(range=(self.x, self.x + self.w), index=0)
        along_col = adict(range=(self.y, self.y + self.h), index=1)

        level1, level2 = (along_row, along_col) if per == 'rows' else (along_col, along_row)
        f = reversed if reverse else lambda x: x

        for i in f(range(*level1.range)):
            for j in f(range(*level2.range)):
                point = (i, j) if level1.index == 0 else (j, i)
                if exclude_top_left and point == (self.x, self.y):
                    continue

                yield Point(*point)

    def project(self, direction='horizontal') -> LinearSegment:
        if direction == 'horizontal':
            return LinearSegment(self.x, length=self.w)
        else:
            return LinearSegment(self.y, length=self.h)
