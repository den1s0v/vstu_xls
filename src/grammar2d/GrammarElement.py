from dataclasses import dataclass

from constraints_2d import SpatialConstraint
# from grammar2d import GRAMMAR
from utils import WithCache


@dataclass
class GrammarElement(WithCache):
    """Элемент грамматики: """

    name_for_constraints = 'element'

    name: str  # имя узла грамматики (определяет тип содержимого)
    root: bool = False  # whether this element is the grammar's root.
    precision_threshold = 0.3  # [0, 1] порог допустимой точности, ниже которого элемент считается не найденным.

    @property
    def name2component(self):
        """ ??? """
        return {}

    def __hash__(self) -> int:
        return hash(self.name)

    # parent: Optional['GrammarElement'] = None # родительский узел грамматики
    # components: dict[str, 'PatternComponent']

    # Линейная иерархия переопределения базовых узлов. Перечисленные здесь элементы могут заменяться на текущий элемент.
    extends: list['GrammarElement|str'] = ()

    constraints: list[SpatialConstraint] = ()

    @property
    def global_constraints(self) -> list[SpatialConstraint]:
        """ "Глобальные" ограничения — запись координат преобразована из сокращённой формы в полную:
            'x' или 'this_x' → 'element_x' и т.п.
        """
        if not self._cache.constraints_with_full_names:
            self._cache.constraints_with_full_names = [
                ex.clone().replace_components({
                    'this': self.name_for_constraints,
                })
                for ex in self.constraints
            ]
        return self._cache.constraints_with_full_names

    def dependencies(self, recursive=False) -> list['GrammarElement']:
        """ GrammarElement must be known before this one can be matched. """
        raise NotImplementedError(type(self))

    # @property
    # def is_root(self) -> bool:
    #     return self.parent is None

    def max_score(self) -> float:
        raise NotImplementedError(type(self))

    def can_be_extended_by(self, child_element: 'GrammarElement') -> bool:
        # TODO
        # return GRAMMAR.can_extend(self, child_element)
        ...

    def get_matcher(self, grammar_matcher):
        raise NotImplementedError()
