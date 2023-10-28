# geom1d.py


from typing import Optional


# Имитирует интерфейс tuple
class LinearSegment:
    """Отрезок AB на прямой (1D) - две целых координаты (a <= b).
     Одномерный примитив для работы на координатной прямой """

    def __init__(self, a, b=None, length=None):
        if b is None:
            assert length is not None, 'LinearSegment(a, [b] [,length]) ' \
                                       'cannot be created without b or length specified.'
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

    @property
    def size(self):
        return self.b - self.a

    def intersect(self, other: 'LinearSegment') -> Optional['LinearSegment']:
        return LinearRelation(self, other).intersection()


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


# * * Внутренние * * #

class Overlaps(GenericRelation):
    description = 'пересекается с'


class Includes(Overlaps):
    description = 'включает'


class IncludedIn(Overlaps):
    description = 'входит в'


class TouchesInternally(IncludedIn):
    description = 'имеет общую стенку'


class TouchesInternallyLeft(TouchesInternally):
    description = 'имеет общую левую стенку с'


class TouchesInternallyRight(TouchesInternally):
    description = 'имеет общую правую стенку с'


class IncludesGluedLeft(TouchesInternallyLeft, Includes, ):
    description = 'включает примыкающее слева'


class IncludesGluedRight(TouchesInternallyRight, Includes, ):
    description = 'включает примыкающее справа'


class IncludedInGluesLeft(TouchesInternallyLeft, IncludedIn, ):
    description = 'включается, примыкая слева, в'


class IncludedInGluesRight(TouchesInternallyRight, IncludedIn, ):
    description = 'включается, примыкая справа, в'


class CoinsidesWith(IncludesGluedLeft, IncludesGluedRight, IncludedInGluesLeft, IncludedInGluesRight):
    description = 'совпадает с'


### Внешние ###

class NoOverlap(GenericRelation):
    description = 'не пересекается с'


class AtLeftFrom(NoOverlap):
    description = 'слева от'


class AtRightFrom(NoOverlap):
    description = 'справа от'


class Touches(NoOverlap):
    description = 'примыкает к'


class TouchesAtLeft(Touches, AtRightFrom):
    description = 'примыкает слева к'


class TouchesAtRight(Touches, AtLeftFrom):
    description = 'примыкает справа к'


class FarFrom(NoOverlap):
    description = 'на удалении от'


class FarFromAtLeft(FarFrom, AtLeftFrom):
    description = 'на удалении слева от'


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
            self.kind = TouchesAtRight  # AB касается CD левым краем, будучи при этом справа от него

        elif gr > 0:
            self.kind = FarFromAtLeft
        elif gr == 0:
            self.kind = TouchesAtLeft
        else:
            # fallback
            self.kind = Overlaps

        self.description = self.kind.description

    def intersection(self) -> Optional[LinearSegment]:
        if issubclass(self.kind, (Overlaps, Touches)):
            # get two middle points
            a, b = sorted((self.s1.a, self.s1.b, self.s2.a, self.s2.b))[1:3]
            return LinearSegment(a, b)
        return None
