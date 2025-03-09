from dataclasses import dataclass

from constraints_2d import SpatialConstraint
from constraints_2d import BoolExprRegistry
import grammar2d.Grammar as ns
import grammar2d.PatternComponent as pc
import grammar2d.PatternMatcher as pm
from geom2d import open_range, Box
from utils import WithCache, WithSafeCreate


@dataclass(kw_only=True, )
class Pattern2d(WithCache, WithSafeCreate):
    """Паттерн — элемент 2D-грамматики:
    Базовый класс для терминала и нетерминалов грамматики """
    name: str  # имя узла грамматики (определяет тип содержимого)
    root: bool = False  # whether this element is the grammar's root.
    precision_threshold = 0.3  # [0, 1] порог допустимой точности, ниже которого элемент считается не найденным.

    description: str = None  # текстовое описание
    style: dict = None  # оформление области; пока только `borders`
    count: open_range = None  # open_range(0, None)  # кратность элемента в документе (1 = уникален)

    # Линейная иерархия переопределения базовых узлов. Перечисленные здесь элементы могут заменяться на текущий элемент.
    extends: list[str] = ()
    _extends_patterns: list['Pattern2d'] = None

    constraints: list[SpatialConstraint] = ()

    _grammar: 'ns.Grammar' = None

    name_for_constraints = 'element'

    def __post_init__(self):
        # convert attributes to usable types
        if not isinstance(self.count, open_range):
            self.count = open_range.parse(str(self.count)) if self.count else open_range(0, None)

    def __hash__(self) -> int:
        return hash(self.name)

    def __str__(self) -> str:
        return "%s(name='%s')" % (type(self).__name__, self.name)

    def __repr__(self) -> str:
        return "%s(name='%s')" % (type(self).__name__, self.name)

    def __dict__(self) -> dict:
        return dict(name=self.name)

    def __eq__(self, other):
        return self.name == other.name

    def __lt__(self, other):
        return self.name < other.name

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

    def check_constraints_for_bbox(self, box: Box) -> bool:
        """ Check if bounding box satisfies this pattern's constraints. """
        component2box = {'element': box}
        for ct in self.global_constraints:
            if not ct.eval_with_components(component2box):
                return False
        return True

    def dependencies(self, recursive=False) -> list['Pattern2d']:
        """ Pattern2d must be known before this one can be matched. """
        raise NotImplementedError(type(self))

    def extends_patterns(self, recursive=False) -> list['Pattern2d']:
        """ Instances of Pattern2d redefined by this one. """
        if self._extends_patterns is None:
            self._extends_patterns = [
                self._grammar.patterns[base_name]
                for base_name in self.extends
            ]
        if not recursive:
            return self._extends_patterns
        else:
            seen_bases = {}  # using as ordered set, with meaningless values
            for base in self._extends_patterns:
                if base in seen_bases:
                    continue
                seen_bases[base] = base  # add
                sub_bases = base.extends_patterns(recursive)
                if self in sub_bases:
                    print(f"SYNTAX WARN: grammar pattern `{self.name}` extends pattern(s) `{seen_bases
                    }` some of which, in turn, indirectly extend this one.")
                seen_bases |= dict.fromkeys(sub_bases)

            return list(seen_bases)

    def set_grammar(self, grammar: 'ns.Grammar'):
        self._grammar = grammar

    # @property
    # def is_root(self) -> bool:
    #     return self.parent is None

    def max_score(self) -> float:
        """ Ex. precision = score / max_score """
        raise NotImplementedError(type(self))

    def score_of_match(self, match: 'grammar2d.Match2d') -> float:
        """ Calc score for given match """
        raise NotImplementedError(type(self))

    def can_be_extended_by(self, child_element: 'Pattern2d') -> bool:
        return self._grammar.can_extend(self, child_element)

    def get_matcher(self, grammar_matcher) -> 'pm.PatternMatcher':
        raise NotImplementedError()


class PatternRegistry:
    registry = {}

    @classmethod
    def register(cls, pattern_cls):
        """Регистрация подкласса в реестре по его kind.
        Может использовано как аннотация."""
        kind = pattern_cls.get_kind()
        cls.registry[kind] = pattern_cls
        return pattern_cls

    @classmethod
    def get_pattern_class_by_kind(cls, kind: str) -> 'type[Pattern2d]|None':
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
        return pattern_cls.safe_create(**data)
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

    # read constraints for component
    constraints = extract_pattern_constraints(data, component_name, )
    if 'role' in data:
        del data['role']

    # collect info about keys could not be read...
    keys_ignored = set(data.keys())

    if 'pattern' not in data:
        # got inline pattern definition...

        # pattern_data = dict(data)
        # make a name for anon pattern
        data['name'] = component_name + '[inline]'
        # parse inline pattern
        parsed_pattern = read_pattern(data)
        if not parsed_pattern:
            return None  # Fail too

        keys_ignored &= set(parsed_pattern._kwargs_ignored)

        # data for component:
        data['_subpattern'] = parsed_pattern
        data['pattern'] = parsed_pattern.name

    # Add role for component
    data['inner'] = (role == 'inner')

    if constraints:
        data['constraints'] = constraints
    data['name'] = name

    component = pc.PatternComponent.safe_create(**data)
    keys_ignored &= set(component._kwargs_ignored)

    if (keys_ignored):
        print(f"SYNTAX WARN: grammar pattern `{pattern_name}` has component `{name \
            }` that defines unrecognized keys: {keys_ignored}.")

    return component


def extract_pattern_constraints(data: dict, pattern_name: str = None) -> list[pc.SpatialConstraint]:
    constraints = []
    # size
    # location
    for k in ('size', 'location',):
        if k in data:
            sc_data = data[k]
            # Note: remove used key from data!
            del data[k]
            cls_sc = BoolExprRegistry.get_class_by_kind(k)
            if cls_sc:
                sc: SpatialConstraint = cls_sc.parse(data=sc_data, context=data)
                constraints.append(sc)

    return constraints
