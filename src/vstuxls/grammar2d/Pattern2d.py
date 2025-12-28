from copy import deepcopy
from dataclasses import dataclass
from enum import Enum

import vstuxls.grammar2d.Grammar as ns
import vstuxls.grammar2d.Match2d as m2
import vstuxls.grammar2d.PatternComponent as pc
import vstuxls.grammar2d.PatternMatcher as pm
from vstuxls.constraints_2d import BoolExprRegistry, SizeConstraint, SpatialConstraint
from vstuxls.geom2d import Box, Point, open_range
from vstuxls.utils import WithCache, WithSafeCreate, safe_adict, sorted_list


class OverlapResolutionMode(Enum):
    """Режимы разрешения накладок между матчами."""
    NONE = "none"  # не убирать никакие накладки
    FULL = "full"  # убирать полное наложение (по умолчанию)
    PARTIAL = "partial"  # убирать частичное наложение в пользу более точного


class OverlapMetricEnum(Enum):
    """Метрики, по которым можно сравнивать матчи."""
    AREA = "area"
    WIDTH = "width"
    HEIGHT = "height"
    PRECISION = "precision"


class OverlapOrderEnum(Enum):
    """Направление сравнения: max/min."""
    MAX = "max"
    MIN = "min"


@dataclass
class OverlapCriterion:
    """Один критерий сравнения: метрика + направление (max/min)."""
    metric: OverlapMetricEnum
    order: OverlapOrderEnum


@dataclass
class OverlapConfig:
    """Полная конфигурация разрешения накладок для паттерна."""
    mode: OverlapResolutionMode
    criteria: list[OverlapCriterion]

    @classmethod
    def default(cls) -> "OverlapConfig":
        """Значения по умолчанию: no overlap filtering (NONE mode)."""
        return cls(
            mode=OverlapResolutionMode.NONE,
            criteria=[
                OverlapCriterion(OverlapMetricEnum.AREA, OverlapOrderEnum.MAX),
                OverlapCriterion(OverlapMetricEnum.PRECISION, OverlapOrderEnum.MAX),
            ],
        )

    @classmethod
    def from_yaml(cls, overlap_data: dict, pattern_name: str | None = None) -> "OverlapConfig":
        """Создаёт OverlapConfig из YAML-секции overlap."""
        overlap_data = overlap_data or {}

        mode_str = overlap_data.get("mode", "full")
        try:
            mode = OverlapResolutionMode(mode_str)
        except ValueError:
            print(
                f"SYNTAX WARN: grammar pattern `{pattern_name}` has invalid overlap.mode: "
                f"{mode_str!r}, using 'full'"
            )
            mode = OverlapResolutionMode.FULL

        raw_resolution = overlap_data.get("resolution", ["area-max", "precision-max"])
        if not isinstance(raw_resolution, list):
            print(
                f"SYNTAX WARN: grammar pattern `{pattern_name}` has invalid overlap.resolution "
                f"(expected list, got {type(raw_resolution).__name__}), using default"
            )
            raw_resolution = ["area-max", "precision-max"]

        criteria: list[OverlapCriterion] = []
        invalid_items: list[str] = []

        for item in raw_resolution:
            if not isinstance(item, str):
                invalid_items.append(f"{item!r} (not a string)")
                continue

            parts = item.split("-")
            if len(parts) != 2:
                invalid_items.append(f"{item!r} (expected format 'metric-order', e.g. 'area-max')")
                continue

            metric_str, order_str = parts[0].lower(), parts[1].lower()
            try:
                metric = OverlapMetricEnum(metric_str)
            except ValueError:
                invalid_items.append(
                    f"{item!r} (invalid metric '{metric_str}', "
                    f"expected one of: {', '.join(e.value for e in OverlapMetricEnum)})"
                )
                continue

            try:
                order = OverlapOrderEnum(order_str)
            except ValueError:
                invalid_items.append(
                    f"{item!r} (invalid order '{order_str}', "
                    f"expected one of: {', '.join(e.value for e in OverlapOrderEnum)})"
                )
                continue

            criteria.append(OverlapCriterion(metric=metric, order=order))

        if invalid_items:
            print(
                f"SYNTAX WARN: grammar pattern `{pattern_name}` has invalid overlap.resolution items:\n"
                + "\n".join(f"  - {item}" for item in invalid_items)
            )

        if not criteria:
            # Если ничего не удалось распарсить – используем значения по умолчанию
            if raw_resolution:  # Предупреждаем только если был непустой список
                print(
                    f"SYNTAX WARN: grammar pattern `{pattern_name}` has no valid overlap.resolution items, "
                    f"using default: {[f'{c.metric.value}-{c.order.value}' for c in cls.default().criteria]}"
                )
            return cls.default()

        return cls(mode=mode, criteria=criteria)


@dataclass(kw_only=True)
class Pattern2d(WithCache, WithSafeCreate):
    """Паттерн — элемент 2D-грамматики:
    Базовый класс для терминала и нетерминалов грамматики """
    name: str  # имя узла грамматики (определяет тип содержимого)
    root: bool = False  # whether this element is the grammar's root.
    precision_threshold = 0.3  # [0, 1] порог допустимой точности, ниже которого элемент считается не найденным.
    confidence: float = 1.0  # confidence level in range [0..1] associated with the pattern.

    description: str = None  # текстовое описание
    style: dict = None  # оформление области; пока никак не используется.
    count_in_document: open_range = None  # open_range(0, None)  # кратность элемента в документе (1 = уникален)

    # Линейная иерархия переопределения базовых узлов. Перечисленные здесь элементы могут заменяться на текущий элемент.
    extends: list[str] = ()
    _directly_extends_patterns: list['Pattern2d'] = None
    _all_direct_extensions: list['Pattern2d'] = None

    static_data: dict = None  # static data for the pattern, not used for matching. Will be included in any match of this pattern.

    constraints: list[SpatialConstraint] = ()

    overlap_config: OverlapConfig | None = None  # конфигурация разрешения накладок

    _grammar: 'ns.Grammar' = None
    _size_constraint: SizeConstraint = ...

    name_for_constraints = 'element'

    def __post_init__(self):
        # convert attributes to usable types
        if not isinstance(self.count_in_document, open_range):
            self.count_in_document = open_range.parse(
                str(self.count_in_document)) if self.count_in_document else open_range(0, None)
        if self.extends and not isinstance(self.extends, list):
            self.extends = [str(self.extends)]

        # Устанавливаем значения по умолчанию для overlap_config, если не задано
        if self.overlap_config is None:
            self.overlap_config = OverlapConfig.default()

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

    def get_overlap_mode_enum(self) -> OverlapResolutionMode:
        """Возвращает режим разрешения накладок."""
        if self.overlap_config:
            return self.overlap_config.mode
        return OverlapResolutionMode.FULL

    def get_overlap_criteria(self) -> list[OverlapCriterion]:
        """Возвращает критерии разрешения конфликтов."""
        if self.overlap_config:
            return list(self.overlap_config.criteria)
        return OverlapConfig.default().criteria

    @classmethod
    def get_kind(cls):
        return "Base 2D pattern"

    @classmethod
    def independently_matchable(cls):
        """ Returns True by default; False only for specific patterns that cannot be matched independently,
        rather in a context of another pattern. """
        return True

    def recalc_box_for_match(self, match: 'm2.Match2d') -> Box:
        """ Calc bounding box simply as union of all components
        """
        if not match.component2match:
            return match.box

        union = Box.union(*(
            m.box
            for m in match.component2match.values()
        ))
        return union

    def get_points_occupied_by_match(self, match: 'm2.Match2d') -> list[Point]:
        """ Default: opaque.
        Реализация по умолчанию: Просто берём внутреннюю прямоугольную область.
        """
        return sorted_list(match.box.iterate_points())

    def get_text_of_match(self, match: 'm2.Match2d') -> list[str]:
        """ Просто всё содержимое всех ячеек.
        """
        return [s
                for m in match.component2match.values()
                for s in m.get_content()]

    def prepare_match(self, match: 'm2.Match2d') -> None:
        """Хук для инициализации данных совпадения."""
        self._ensure_match_data(match)
        self._attach_static_data(match)

    def _attach_static_data(self, match: 'm2.Match2d') -> None:
        data = self._ensure_match_data(match)

        static_data = self._static_data_for_match(match)
        if static_data:
            data.update(static_data)

    def _ensure_match_data(self, match: 'm2.Match2d') -> safe_adict:
        if match.data is None or not isinstance(match.data, safe_adict):
            match.data = safe_adict(match.data or {})
        return match.data

    def set_match_metadata(self, match: 'm2.Match2d', **metadata) -> None:
        """Служебные данные, используемые при экспорте содержимого."""
        if not metadata:
            return
        data = self._ensure_match_data(match)
        data.update(metadata)

    def _static_data_for_match(self, match: 'm2.Match2d') -> dict | None:
        if not self.static_data:
            return None
        try:
            return deepcopy(self.static_data)
        except Exception:
            return dict(self.static_data)

    def _exportable_match_metadata(self, match: 'm2.Match2d') -> dict:
        data = getattr(match, 'data', None)
        if not data:
            return {}

        return {
            key: deepcopy(value)
            for key, value in data.items()
            if isinstance(key, str) and key.startswith('@')
        }

    def _merge_static_data_into_content(self, match: 'm2.Match2d', content):
        static_data = self._static_data_for_match(match)
        metadata = self._exportable_match_metadata(match)

        if isinstance(content, dict):
            merged = {}
            if static_data:
                merged.update(static_data)
            if metadata:
                merged.update(metadata)
            merged.update(content)  # match content takes precedence.
            return merged

        if content is None:
            if static_data or metadata:
                merged = {}
                if static_data:
                    merged.update(static_data)
                if metadata:
                    merged.update(metadata)
                return merged
            return None

        merged = {}
        if static_data:
            merged.update(static_data)
        if metadata:
            merged.update(metadata)

        if not merged:
            return content

        merged.setdefault('@content', content)
        return merged

    def _build_content_of_match(self, match: 'm2.Match2d', include_position=False) -> dict:
        """Игнорирует поля, начинающиеся с "_". Этот префикс может быть использован 
        специально, чтобы скрывать избыточные данные из результата."""
        return ({
            '@box': match.box,
        } if include_position else {}) | {
            name: m.get_content()
            for name, m in match.component2match.items()
            if not name.startswith('_')
        }

    def get_content_of_match(self, match: 'm2.Match2d', include_position=False):
        """Компактные данные для экспорта в JSON."""
        content = self._build_content_of_match(match, include_position)
        return self._merge_static_data_into_content(match, content)

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
        """ `Pattern2d`s must be known before this one can be matched.
            A common assumption for a pattern is to
             let all extensions match before this one can be used.
        """
        # make a set & convert to list
        return sorted({
            dep
            for extending in self.get_extending_patterns(recursive)
            for dep in extending.dependencies(recursive)
        })

    def extends_patterns(self, recursive=False) -> list['Pattern2d']:
        """ Instances of Pattern2d redefined by this one. """
        if self._directly_extends_patterns is None:
            self._directly_extends_patterns = [
                self._grammar.patterns[base_name]
                for base_name in self.extends
            ]
        if not recursive:
            return self._directly_extends_patterns
        else:
            seen_bases = {}  # using dict as ordered set, ignoring values.
            for base in self._directly_extends_patterns:
                if base in seen_bases:
                    continue
                seen_bases[base] = base  # add
                sub_bases = base.extends_patterns(recursive)
                if self in sub_bases:
                    print(f"SYNTAX WARN: grammar pattern `{self.name}` extends pattern(s) `{seen_bases
                    }` some of which, in turn, indirectly extend this one.")
                seen_bases |= dict.fromkeys(sub_bases)

            return list(seen_bases)

    def get_extending_patterns(self, recursive=False) -> list['Pattern2d']:
        """ Instances of Pattern2d that redefine this one. """
        if self._all_direct_extensions is None:
            self._all_direct_extensions = [
                p
                for p in self._grammar.patterns.values()
                if self.name in p.extends
            ]
        if not recursive:
            return self._all_direct_extensions
        else:
            seen_extensions = {}  # using dict as ordered set, ignoring values.
            for extension in self._all_direct_extensions:
                if extension in seen_extensions:
                    continue
                seen_extensions[extension] = extension  # add
                sub_extensions = extension.get_extending_patterns(recursive)
                if self in sub_extensions:
                    print(f"SYNTAX WARN: grammar pattern `{self.name}` is extended by pattern(s) `{seen_extensions
                    }` some of which, in turn, are indirectly extended by this one.")
                seen_extensions |= dict.fromkeys(sub_extensions)

            return list(seen_extensions)

    def set_grammar(self, grammar: 'ns.Grammar'):
        self._grammar = grammar

    # @property
    # def is_root(self) -> bool:
    #     return self.parent is None

    def max_score(self) -> float:
        """ Ex. precision = score / max_score """
        raise NotImplementedError(type(self))

    def score_of_match(self, match: 'm2.Match2d') -> float:
        """ Calc score for given match """
        raise NotImplementedError(type(self))

    def can_be_extended_by(self, child_element: 'Pattern2d') -> bool:
        return self._grammar.can_extend(self, child_element)

    def get_matcher(self, grammar_matcher) -> 'pm.PatternMatcher':
        raise NotImplementedError()

    def get_size_constraint(self) -> SizeConstraint | None:
        if self._size_constraint is ...:
            self._size_constraint = \
                (list(filter(lambda x: isinstance(x, SizeConstraint), self.global_constraints))
                 or
                 (None,))[0]
        return self._size_constraint


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
        raise ValueError('Format error: `kind` key is expected for any pattern of a grammar.')

    pattern_cls = PatternRegistry.get_pattern_class_by_kind(kind)

    # Silently ignore unknown kinds. TODO
    if not pattern_cls:
        return None

    pattern_name = data.get('name')
    components = read_pattern_components(data, pattern_name)
    constraints = extract_pattern_constraints(data, pattern_name)

    # Парсим секцию overlap в типизированный OverlapConfig
    overlap_config: OverlapConfig | None = None
    if 'overlap' in data:
        overlap_data = data['overlap']
        del data['overlap']
        if isinstance(overlap_data, dict):
            overlap_config = OverlapConfig.from_yaml(overlap_data, pattern_name)
        else:
            print(
                f"SYNTAX WARN: grammar pattern `{pattern_name}` has invalid overlap section "
                f"(expected dict, got {type(overlap_data).__name__}), using default overlap config"
            )

    if components:
        data['components'] = components
    if constraints:
        data['constraints'] = constraints
    if overlap_config:
        data['overlap_config'] = overlap_config

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
    data.pop('role', None)

    # collect info about keys could not be read...
    keys_ignored = set(data.keys())

    if 'pattern' not in data:
        # got inline pattern definition...
        if 'pattern_definition' not in data:
            raise ValueError(f"grammar pattern `{pattern_name}` has component `{name
                }` that defines no 'pattern' nor 'pattern_definition'.")

        pattern_data = dict(data['pattern_definition'])
        # make a name for anon pattern
        pattern_data['name'] = component_name + '[inline]'
        # parse inline pattern
        parsed_pattern = read_pattern(pattern_data)
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

    if keys_ignored:
        print(f"SYNTAX WARN: grammar pattern `{pattern_name}` has component `{name \
            }` that defines unrecognized keys: {keys_ignored}.")

    return component


def extract_pattern_constraints(data: dict, pattern_name: str = None) -> list[pc.SpatialConstraint]:
    """ Finds keys 'size', 'location' (so far) and parses them as `SpatialConstraint`s.
     By the way, deletes corresponding keys from `data`!
     """
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
