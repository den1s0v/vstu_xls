from dataclasses import dataclass

from constraints_2d import SpatialConstraint
from constraints_2d import BoolExprRegistry
import grammar2d.Grammar as ns
import grammar2d.PatternComponent as pc
from geom2d import open_range
from utils import WithCache

GRAMMAR: 'ns.Grammar'


@dataclass(kw_only=True, repr=True)
class Pattern2d(WithCache):
    """Элемент грамматики:
    Базовый класс для терминала и нетерминалов грамматики """

    name_for_constraints = 'element'

    name: str  # имя узла грамматики (определяет тип содержимого)
    root: bool = False  # whether this element is the grammar's root.
    precision_threshold = 0.3  # [0, 1] порог допустимой точности, ниже которого элемент считается не найденным.

    description: str = None  # текстовое описание
    style: dict = None  # оформление области; пока только `borders`
    count: open_range = None  # open_range(0, 999)  # кратность элемента в документе (1 = уникален)

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
        del data['kind']
    except KeyError:
        raise ValueError('Format error: `kind` key expected for any pattern of grammar.')

    pattern_cls = PatternRegistry.get_pattern_class_by_kind(kind)

    # Silently ignore unknown kinds. TODO
    if not pattern_cls:
        return None

    pattern_name = data.get('name')
    components = read_pattern_components(data, pattern_name)
    constraints = extract_pattern_constraints(data, pattern_name)

    if components:
        data['components'] = components
    if constraints:
        data['constraints'] = constraints

    # create new Pattern of specific subclass.
    try:
        return pattern_cls(**data)
    except TypeError as e:
        print(repr(e))
    return None


def read_pattern_components(data: dict, pattern_name=None) -> list[pc.PatternComponent]:
    components = []

    for component_section_key in ('inner', 'outer'):
        if component_section_key not in data:
            continue
        component_dict: dict = data.get(component_section_key)
        # Note: remove used key from data!
        del data[component_section_key]
        if not isinstance(component_dict, dict):
            print(f"SYNTAX WARN: grammar pattern `{pattern_name}` has invalid/empty `{component_section_key}` section.")
            continue

        for name, fields in component_dict.items():
            component = read_pattern_component(name, fields, component_section_key, pattern_name)
            if component:
                components.append(component)
            else:
                print(f"SYNTAX WARN: grammar pattern `{pattern_name}` has invalid/empty `{name}` component.")
    return components


def read_pattern_component(
        name: str,
        data: dict,
        role: str = 'outer',
        pattern_name: str = None) -> pc.PatternComponent | None:

    component_name = (pattern_name or '') + '.' + name

    assert isinstance(data, dict), data

    if 'location' in data:
        assert role in ('inner', 'outer'), role
        # preparing data for LocationConstraint
        data['role'] = role


    # Note: this removes keys related to constraints from data!
    constraints = extract_pattern_constraints(data, component_name, )
    if 'role' in data:
        del data['role']

    if 'pattern' not in data:
        # got inline pattern definition...

        # pattern_data = dict(data)
        # make a name for anon pattern
        data['name'] = component_name + '[inline]'
        # parse inline pattern
        parsed_pattern = read_pattern(data)
        if not parsed_pattern:
            return None  # Fail too

        # data for component:
        data['_subpattern'] = parsed_pattern
        data['pattern'] = parsed_pattern.name

    if constraints:
        data['constraints'] = constraints
    data['name'] = name

    # remove all not supported keys from data
    extra_keys = set(data.keys()) - set(pc.PatternComponent.__annotations__.keys())
    for k in extra_keys:
        del data[k]

    return pc.PatternComponent(**data)


def extract_pattern_constraints(data: dict, pattern_name: str = None) -> list[pc.SpatialConstraint]:

    constraints = []
    # size
    # location
    for k in ('size', 'location', ):
        if k in data:
            sc_data = data[k]
            # Note: remove used key from data!
            del data[k]
            cls_sc = BoolExprRegistry.get_class_by_kind(k)
            if cls_sc:
                sc: SpatialConstraint = cls_sc.parse(data=sc_data, context=data)
                constraints.append(sc)

    return constraints
