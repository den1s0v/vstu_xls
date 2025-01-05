from _operator import and_
from dataclasses import dataclass
from functools import reduce

from constraints_2d import SpatialConstraint
# from grammar2d import GRAMMAR
from grammar2d.GrammarElement import GrammarElement
from utils import WithCache


@dataclass
class PatternComponent(WithCache):
    """ Обёртка над элементом грамматики, которая позволяет задать его отношение к родительскому элементу (родитель — это контейнер для компонента).
        Точность определения этого компонента вносит вклад в точность определения родительского элемента (объём вклада также зависит от `weight`).
        Компонент может быть опциональным и отсутствовать на практике, — в этом случае он не вносит вклад в точность определения родительского элемента.
    """
    name: str  # имя компонента по отношению к родителю.

    element_name: str  # имя дочернего элемента, включаемого в родительский как компонент.

    _element: 'GrammarElement' = None  # дочерний элемент грамматики

    @property
    def element(self) -> 'GrammarElement':
        """Дочерний элемент грамматики"""
        if not self._element:
            # TODO: assign GRAMMAR before usage.
            # self._element = GRAMMAR[self.element_name]
            ...
        return self._element

    constraints: list[
        SpatialConstraint] = ()  # "Локальные" ограничения, накладываемые на расположение этого компонента по отношению к родителю. Используются координаты текущего дочернего элемента и родительского элемента. Также могут использоваться координаты других компонентов родителя, которые были определены по списку компонентов выше этого компонента. "Локальные" означает, то для записи координат может быть использована сокращёная форма: 'x' — свой 'x', '_x' — 'x' родителя, и т.п.

    weight: float = 1  # (-∞, ∞) вес компонента для регулирования вклада в точность опредления родителя. >0: наличие желательно, 0: безразлично (компонент может быть опущен без потери точности), <0: наличие нежелательно.

    optional = False  # Если True, компонент считается опциональным и может отсутствовать. Если False, то его наличие обязательно требуется для существования родительского элемента.

    precision_treshold = 0.3  # [0, 1] порог допустимой точности, ниже которого компонент считается не найденным.

    # @property
    # def max_score(self) -> float:
    #     return self.weight * max(0, self.importance)

    def dependencies(self, recursive=False) -> list['GrammarElement']:
        if not recursive:
            return self.element

        return [self.element, *self.element.dependencies(recursive=True)]

    # constraints_with_full_names: list[SpatialConstraint] = None

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
                    'parent': GrammarElement.name_for_constraints,  # 'element'
                })
                for ex in self.constraints
            ]
        return self._cache.constraints_with_full_names

    def constraints_conjunction(self) -> SpatialConstraint:
        if self._cache.constraints_conjunction is None:
            self._cache.constraints_conjunction = reduce(and_, self.global_constraints)
        return self._cache.constraints_conjunction

    def checks_components(self) -> set[str]:
        """ Find which components are checked within constraints.
        This method usually returns 'element' as parent, and `self.name` as well. """
        if self._cache.components_in_constraints is None:
            self._cache.components_in_constraints = frozenset(self.constraints_conjunction().referenced_components())
        return self._cache.components_in_constraints

    def checks_other_components(self) -> set[str]:
        """ Find which other components are checked within constraints.
        This method omits 'element' as parent, and self. """
        return self.checks_components() - {GrammarElement.name_for_constraints, self.name}
