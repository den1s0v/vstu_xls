from dataclasses import dataclass
from functools import reduce
from operator import and_
from typing import Self

from loguru import logger

import grammar2d.Pattern2d as pt
from constraints_2d import SpatialConstraint, SizeConstraint
from constraints_2d import LocationConstraint
from geom1d import LinearSegment
from geom2d import open_range, Box, RangedBox
from utils import WithCache, WithSafeCreate
from .Match2d import Match2d


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

    def calc_distance_of_match_to_box(self, match: Match2d, box: Box) -> float:

        # Use cache attached to match object
        distance_to_as: dict[tuple[Box, str], float] = match.data.get('distance_to_as') or dict()
        match.data.distance_to_as = distance_to_as  # set back if created

        key = (box, 'inner' if self.inner else 'outer')
        known_distance = distance_to_as.get(key)

        if known_distance is None:
            if self.inner:
                # Расстояние для внутреннего компонента
                # равняется росту периметра области совпадения,
                # необходимого для включения его в матч.
                known_distance = match.box.manhattan_distance_to_overlap(box)
            else:
                # Близость для внешнего компонента
                # равняется длине максимального из пересечений проекций на оси.
                # Это позволяет компоненту быть далеко, но напротив.
                # pr1_x = match.box.project('h')
                # pr2_x = box.project('h')
                # pr1_y = match.box.project('v')
                # pr2_y = box.project('v')
                # how_close = max(
                #     (pr1_x.intersect(pr2_x) or LinearSegment(0, 0)).size,
                #     (pr1_y.intersect(pr2_y) or LinearSegment(0, 0)).size,
                # )
                # Расстояние же будем считать как минимальное из смещений по проекциям
                known_distance = min(match.box.manhattan_distance_to_overlap(box, per_axis=True))
            # Записать вычисленное значение в кэш
            distance_to_as[key] = known_distance

        return known_distance

    def is_similar_to(self, other: Self) -> bool:
        """ True, если компоненты с одинаковыми ожиданиями,
        т.е. требуемым паттерном и ограничениями.
        """
        if not isinstance(other, type(self)):
            return False
        if self.inner != other.inner:
            return False
        if self.pattern != other.pattern:
            return False
        if len(self.constraints) != len(other.constraints):
            return False
        if set(self.constraints) != set(other.constraints):
            return False
        return True

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
            - незаполненные стороны не получают ограничений вовсе ('*').
            
        Значение LocationConstraint.inside для простоты принимаем всегда равным True.
        """

        mbox = component_match.box

        # Init result as default when no constraints specified
        if self.inner:
            ray = open_range(0, None)
            rbox = RangedBox(
                rx=(mbox.left - ray, mbox.right + ray),
                ry=(mbox.top - ray, mbox.bottom + ray),
            )
        else:
            # Completely unconstrained
            rbox = RangedBox()

        # Apply constraints
        for constraint in self.constraints:
            if not isinstance(constraint, LocationConstraint):
                logger.warning(f'Unsupported Constraint: pattern `{self.subpattern.name
                }` defines constraint ({constraint!r
                }) of type {constraint.__class__.__name__
                }  that is not supported yet.')
                continue

            if self.inner:
                rbox = self._apply_inside_constraint(rbox, constraint, mbox)
            else:
                rbox = self._apply_outside_constraint(rbox, constraint, mbox)

        return rbox

    def get_ranged_box_for_component_location(self, parent_partial_area: RangedBox) -> RangedBox:
        """Получить ограничения на позицию компонента (ребёнка)
         по предположениям о позиции родителя и известным ограничениям на позицию ребёнка в родителе.

        В отличие от предыдущего метода (get_ranged_box_for_parent_location),
         применение ограничений компонента работает прямолинейно, но сложность в том, что
         область родителя определена нечётко, т.к. в ней не хватает, как минимум, текущего компонента,
         и задана нечёткими границами.
         Будем считать, что ограничения на размер родителя уже заложены в параметр (parent_partial_area).

        Реализовано пока только для LocationConstraint и SizeConstraint.

        "Взаимоотношения" между компонентами в модель введены не были (на момент написания) и не рассматриваются.

        :param parent_partial_area: частичное совпадение родительской области
        :return: оценка положения компонента

        ----
        Как считать:
        Для внутренних сторон:
            - заполняется та же сторона, "отняв" от границы родителя отступ ребёнка.
            - незаполненные стороны получают ограничение как с диапазоном '0+'.
        Для внешних сторон:
            - заполняется противолежащая сторона, "прибавив" к границе одноимённой стороны родителя отступ ребёнка.
            - незаполненные стороны не получают ограничений вовсе ('*').

        На результат наложить ограничения по размеру ребёнка, если заданы.
        """
        parent = parent_partial_area

        # Init result as default when no constraints specified
        if self.inner:
            ray = open_range(0, None)
            rbox = RangedBox(
                rx=(parent.left + ray, parent.right - ray),
                ry=(parent.top + ray, parent.bottom - ray),
            )
        else:
            # Completely unconstrained
            rbox = RangedBox()

        size_constraints = []

        # Apply constraints
        for constraint in self.constraints:
            if isinstance(constraint, SizeConstraint):
                size_constraints.append(constraint)
                continue
            if not isinstance(constraint, LocationConstraint):
                continue

            if self.inner:
                #  Для внутренних сторон:
                #  заполняется та же сторона, "отняв" от границы родителя отступ ребёнка.
                for d, gap in constraint.side_to_gap.items():
                    side = d.prop_name
                    if side == 'left':
                        rbox.rx.a = parent.left + gap
                    elif side == 'right':
                        rbox.rx.b = parent.right - gap
                    elif side == 'top':
                        rbox.ry.a = parent.top + gap
                    elif side == 'bottom':
                        rbox.ry.b = parent.bottom - gap

            else:
                # Для внешних сторон:
                # заполняется противолежащая сторона, "прибавив" к границе одноимённой стороны родителя отступ ребёнка.
                for d, gap in constraint.side_to_gap.items():
                    side = d.prop_name
                    if side == 'left':
                        rbox.rx.b = parent.left - gap
                    elif side == 'right':
                        rbox.rx.a = parent.right + gap
                    elif side == 'top':
                        rbox.ry.b = parent.top - gap
                    elif side == 'bottom':
                        rbox.ry.a = parent.bottom + gap

        for sc in size_constraints:
            rbox = rbox.restricted_by_size(*sc)

        return rbox.fix_ranges()

    @staticmethod
    def _apply_inside_constraint(ranged_box: RangedBox, constraint: LocationConstraint, mbox: Box) -> RangedBox:
        # Apply constraints for inside location
        # Заполняется та же сторона, значение той же стороны матча плюс диапазон со знаком основной стороны.
        for d, gap in constraint.side_to_gap.items():
            side = d.prop_name
            if side == 'left':
                ranged_box.rx.a = mbox.left - gap
            elif side == 'right':
                ranged_box.rx.b = mbox.right + gap
            elif side == 'top':
                ranged_box.ry.a = mbox.top - gap
            elif side == 'bottom':
                ranged_box.ry.b = mbox.bottom + gap
        return ranged_box

    @staticmethod
    def _apply_outside_constraint(ranged_box: RangedBox, constraint: LocationConstraint, mbox: Box) -> RangedBox:
        # Apply constraints for outside location
        # Заполняется та же сторона, значение противолежащей стороны матча минус диапазон со знаком основной стороны.
        for d, gap in constraint.side_to_gap.items():
            side = d.prop_name
            if side == 'left':
                ranged_box.rx.a = mbox.right + gap
            elif side == 'right':
                ranged_box.rx.b = mbox.left - gap
            elif side == 'top':
                ranged_box.ry.a = mbox.bottom + gap
            elif side == 'bottom':
                ranged_box.ry.b = mbox.top - gap
        return ranged_box
