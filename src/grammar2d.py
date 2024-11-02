# grammar2d.py

from dataclasses import dataclass
from typing import Optional, Union

from confidence_matching import CellType
from constraints_2d import SpatialConstraint


@dataclass
class GrammarElement:
    """Элемент грамматики: """
    name: str  # имя узла (тип содержимого)
    parent: Optional['GrammarElement'] = None # родительский узел грамматики
    # components: dict[str, 'PatternComponent']

    bases: list['GrammarElement' | str] = ()  # Линейная иерархия переопределения базовых узлов. Перечисленные здесь элементы могут заменяться на текущий элемент.

    def dependencies(self, recursive=False) -> list['GrammarElement']:
        pass

    @property
    def is_root(self) -> bool:
        return self.parent is None

    @property
    def max_score(self) -> float:
        """ precision = score / max_score """
        return sum(comp.weight for comp in self.components if comp.weight > 0)




@dataclass
class PatternComponent:
    """ Обёртка над элементом грамматики, которая позволяет задать его отношение к родительскому элементу.
        Точность определения этого компонента вносит вклад в точность определения родительского элемента (объём вклада также зависит от `weight`).
    """
    element_name: str  # имя дочернего компонента (опционально; требуется для переиспользования одного и того же компонента в разных элементах)
    element: GrammarElement

    location_constraints: list[SpatialConstraint]

    weight: float = 1  # (-∞, ∞) вес компонента для регулирования вклада в точность опредления родителя. >0: наличие желательно, 0: безразлично (компонент может быть опущен без потери точности), <0: наличие нежелательно.

    precision_treshold = 0.3  # [0, 1] порог допустимой точности, ниже которого компонент считается не найденным.

    # @property
    # def max_score(self) -> float:
    #     self.weight * max(0, self.importance)

    def dependencies(self, recursive=False) -> list['GrammarElement']:
        pass





class Terminal(GrammarElement):
    """просто ячейка"""
    cell_type: CellType



class NonTerminal(GrammarElement):
    """Структура, Коллекция"""
    components: dict[str, PatternComponent]
    ...


class GrammarRoot(NonTerminal):
    """Корень грамматики — весь документ"""

    ...

