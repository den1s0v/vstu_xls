from operator import and_
from dataclasses import dataclass
from functools import reduce

from constraints_2d import SpatialConstraint, LocationConstraint
from geom2d import open_range
from geom2d.ranged_box import RangedBox
import grammar2d.Grammar as ns
import grammar2d.Match2d as m2
import grammar2d.Pattern2d as pt
from utils import WithCache, WithSafeCreate



@dataclass
class PatternComponent(WithCache, WithSafeCreate):
    """ Обёртка над элементом грамматики, которая позволяет задать его отношение к родительскому элементу
        (родитель — это контейнер для компонента).
        Точность определения этого компонента вносит вклад в точность определения родительского элемента
        (объём вклада также зависит от `weight`).
        Компонент может быть опциональным и отсутствовать на практике, —
            в последнем случае он не вносит вклад в точность определения родительского элемента.
    """
    name: str  # имя компонента по отношению к родителю.

    pattern: str  # имя дочернего элемента, включаемого в родительский как компонент.

    inner: bool = True  # Является ли внутренним и образующим размер родителя

    # "Локальные" ограничения, накладываемые на расположение этого компонента по отношению к родителю.
        # Используются координаты текущего дочернего элемента и родительского элемента.
        # Также могут использоваться координаты других компонентов родителя, которые были определены по списку компонентов выше этого компонента.
        # "Локальные" означает, то для записи координат может быть использована сокращёная форма:
        # 'x' — свой 'x', '_x' — 'x' родителя, и т.п.
    constraints: list[
        SpatialConstraint] = ()

    count: open_range = None  # кратность элемента в родителе

    weight: float = 1  # (-∞, ∞) вес компонента для регулирования вклада в точность опредления родителя. >0: наличие желательно, 0: безразлично (компонент может быть опущен без потери точности), <0: наличие нежелательно (в этом случае должен быть опциональным!).

    optional = False  # Если True, компонент считается опциональным и может отсутствовать. Если False, то его наличие обязательно требуется для существования родительского элемента.

    # TODO: add type to be recognized as annotation
    precision_threshold = 0.3  # [0, 1] порог допустимой точности, ниже которого компонент считается не найденным.

    _subpattern: 'pt.Pattern2d' = None  # дочерний элемент грамматики

    _grammar: 'ns.Grammar' = None

    @property
    def subpattern(self) -> 'pt.Pattern2d':
        """Дочерний элемент грамматики"""
        if not self._subpattern:
            self._subpattern = self._grammar[self.pattern]

        return self._subpattern

    def set_grammar(self, grammar: 'ns.Grammar'):
        self._grammar = grammar

    # @property
    # def max_score(self) -> float:
    #     return self.weight * max(0, self.importance)

    def dependencies(self, recursive=False) -> list['pt.Pattern2d']:
        if not recursive:
            return [self.subpattern]

        return [self.subpattern, *self.subpattern.dependencies(recursive=True)]

    # constraints_with_full_names: list[SpatialConstraint] = None

    # @property
    # def is_optional(self) -> bool:
    #     return self.weight <= 0

    @property
    def global_constraints(self) -> list[SpatialConstraint]:
        """ "Глобальные" ограничения — запись координат преобразована из сокращённой формы в полную:
        'x' или 'this_x' → '<self.name>_x';
        '_x' или 'parent_x' → 'element_x' (координата родителя),
        и т.п. """
        if not self._cache.constraints_with_full_names:
            self._cache.constraints_with_full_names = [
                ex.clone().replace_components({
                    'this': self.name,
                    'parent': pt.Pattern2d.name_for_constraints,  # 'element'
                })
                for ex in self.constraints
            ]
        return self._cache.constraints_with_full_names

    def constraints_conjunction(self) -> SpatialConstraint:
        if self._cache.constraints_conjunction is None:
            self._cache.constraints_conjunction = reduce(and_, self.global_constraints)
        return self._cache.constraints_conjunction

    def checks_components(self) -> frozenset[str]:
        """ Find which components are checked within constraints.
        This method usually returns 'element' as parent, and `self.name` as well. """
        if self._cache.components_in_constraints is None:
            self._cache.components_in_constraints = frozenset(self.constraints_conjunction().referenced_components())
        return self._cache.components_in_constraints

    def checks_other_components(self) -> frozenset[str]:
        """ Find which other components are checked within constraints.
        This method omits 'element' as parent, and self. """
        return self.checks_components() - {pt.Pattern2d.name_for_constraints, self.name}

    def get_ranged_box_for_parent_location(self, component_match: Match2d) -> RangedBox:
        """Получить ограничения на позицию родителя
         по известной позиции компонента (ребёнка) и известным ограничениям на позицию ребёнка в родителе.

        Реализовано пока только для LocationConstraint.

        Если одна из сторон в location компонента не задана,
            её диапазон по умолчанию считается равным:
            - '0+' для внутренних компонентов,
            - '*' для внешних компонентов.

        Args:
            component_match (Match2d): позиция компонента (ребёнка).
                Паттерн этого компонента (`self.pattern`) должен совпадать или быть совместимым с паттерном переданного "матча" (`component_match.pattern`).


        Примеры работы алгоритма.
        Пусть координаты component_match.box: Box.from_2points(20, 1, 40, 5)
        
    Для расположения inner:
    -----------------------
        
    1)  {location: left} →
            RangedBox(
                rx=(20  ,'40+'),
                ry=('1-', '5+'),
            )

    2)  {location: {}  # пустое ограничение: просто внутри
        } →
            RangedBox(
                rx=('20-', '40+'),
                ry=('1-' , '5+'),
            )

    3)  {location: left, right, bottom
            # (кратко заданные внутренние стороны равняются 0)
        } →
            RangedBox(
                rx=(20  , 40),
                ry=('1-', 5),
            )

    4)  {location: right, bottom} →
            RangedBox(
                rx=('20-', 40),
                ry=('1-' , 5),
            )

    5)  {location:
          top: 0,         # примыкает кверху,
          left: '0..1',   # слева и справа может
          right: '0..2',  # отстоять на 0..2 ячеек (внутрь)
        } →
            RangedBox(
                rx=('19..20', '40..42'),
                ry=(1, '5+'),
            )

    6)  {location:
          top: -2,         # выступает ровно на 2 вверх
          right: '-3..3',  # может выступать до 3 наружу
        } →
            RangedBox(
                rx=('*..20', '37..43'),
                ry=(3, '5+'),
            )

    7)  {location:  # явно сняты все ограничения
          top:    '*',
          left:   '*',
          right:  '*',
          bottom: '*',
        } →
            RangedBox(
                rx=('*', '*'),
                ry=('*', '*'),
            )


    Для расположения outer:
    -----------------------

    1)  {location: left} →
            RangedBox(
                rx=('40+', '*'),
                ry=('*' , '*'),
            )

    2)  {location: {}  # пустое ограничение: просто внутри
        } →
            RangedBox(
                rx=('*' , '*'),
                ry=('*' , '*'),
            )

    3)  {location:
            top: 7,  # на строго заданном расстоянии
        } →
            RangedBox(
                rx=('*','*'),
                ry=(12 ,'*'),
            )

    4)  {location:
          top: '0..2',  # примыкает сверху с возможным отступом до 2,
          left: '0-',   # слева есть "заступ" внутрь
          right: '0-',  # справа есть "заступ" внутрь
        } →
            RangedBox(
                rx=('40-', '20+'),
                ry=('5..7', '*'),
            )

    5)  {location: right} →
            RangedBox(
                rx=('*', '20-'),
                ry=('*', '*'),
            )

    6)  {location:
          right: '3..10',
        } →
            RangedBox(
                rx=('*', '10..17'),
                ry=('*', '*'),
            )

    7)  {location:
            top: '-1-',  # сверху и
            bottom: '-1-', # снизу есть "заступ" внутрь c обязательным пересечением
        } →
            RangedBox(
                rx=('*', '*'),
                ry=('4-', '2+'),
            )

        Returns:
            RangedBox: Область, в которой может находиться родительский area для этого компонента, найденного в позиции переданного Match'а.
        """
        # Initialize the result box with the component match box
        """ Как считать:
        Для внутренних сторон:
            - заполняется та же сторона, значение той же стороны матча плюс диапазон со знаком основной стороны.
            - незаполненные стороны получают ограничение как с диапазоном '0+'.
        Для внешних сторон:
            - заполняется та же сторона, значение противолежащей стороны матча минус диапазон со знаком основной стороны.
            - незаполненные стороны не получают ограничений вовсе (*).
            
        Значение LocationConstraint.inside для простоты принимаем всегда равным True.
        """

        for constraint in self.constraints:
            if isinstance(constraint, LocationConstraint):
                ...
        
        ...  # TODO

        return RangedBox()