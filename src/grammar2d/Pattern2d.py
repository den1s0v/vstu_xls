from dataclasses import dataclass

from constraints_2d import SpatialConstraint
import grammar2d.Grammar as ns
from utils import WithCache

GRAMMAR: 'ns.Grammar'


@dataclass
class Pattern2d(WithCache):
    """Элемент грамматики:
    Базовый класс для терминала и нетерминалов грамматики """

    name_for_constraints = 'element'

    name: str  # имя узла грамматики (определяет тип содержимого)
    root: bool = False  # whether this element is the grammar's root.
    precision_threshold = 0.3  # [0, 1] порог допустимой точности, ниже которого элемент считается не найденным.

    description: str = None  # текстовое описание

    # Линейная иерархия переопределения базовых узлов. Перечисленные здесь элементы могут заменяться на текущий элемент.
    extends: list['Pattern2d|str'] = ()

    constraints: list[SpatialConstraint] = ()

    @property
    def name2component(self):
        """ ??? """
        return {}

    def __hash__(self) -> int:
        return hash(self.name)

    @classmethod
    def get_kind(cls):
        return "Base 2D pattern"

    # parent: Optional['Pattern2d'] = None # родительский узел грамматики
    # components: dict[str, 'PatternComponent']

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

    def dependencies(self, recursive=False) -> list['Pattern2d']:
        """ Pattern2d must be known before this one can be matched. """
        raise NotImplementedError(type(self))

    # @property
    # def is_root(self) -> bool:
    #     return self.parent is None

    def max_score(self) -> float:
        raise NotImplementedError(type(self))

    def can_be_extended_by(self, child_element: 'Pattern2d') -> bool:
        return GRAMMAR.can_extend(self, child_element)

    def get_matcher(self, grammar_matcher):
        raise NotImplementedError()


class PatternRegistry:
    registry = {}

    @classmethod
    def register(cls, pattern_cls):
        # Регистрация подкласса в реестре по его kind
        kind = pattern_cls.get_kind()
        cls.registry[kind] = pattern_cls

    @classmethod
    def get_pattern_class_by_kind(cls, kind: str) -> 'type|None':
        pattern_cls = cls.registry.get(kind)
        if not pattern_cls:
            print('WARN: no pattern having kind = `%s`' % kind)
        return pattern_cls


def read_pattern(data: dict) -> Pattern2d | None:
    # find kind of pattern
    try:
        kind = data['kind']
    except KeyError:
        raise ValueError('Format error: `kind` key expected for any pattern of grammar.')

    pattern_cls = PatternRegistry.get_pattern_class_by_kind(kind)

    # Silently ignore unknown kinds. TODO
    if not pattern_cls:
        return None

    components = []
    constraints = []

    if 'inner' in data:
        ...

    # create new Pattern of specific subclass.
    return pattern_cls(**data)
