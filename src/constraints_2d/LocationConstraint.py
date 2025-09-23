from dataclasses import dataclass
import re

from loguru import logger

from constraints_2d.CoordVar import CoordVar
from constraints_2d.SpatialConstraint import SpatialConstraint
from constraints_2d.BoolExpr import BoolExprRegistry
import geom2d as g2


SIDE_ROLES = ("padding", "margin",)


@dataclass(kw_only=True, repr=True)
class LocationConstraint(SpatialConstraint):
    """ Проверка прилегания сторон компонента к границам области родительского паттерна
    (как изнутри, так и снаружи).
    Для внутреннего расположения точка зрения одинаковая — изнутри;
    Для внешнего расположения точка зрения — со стороны родительского элемента (parent) в сторону компонента (this).
    """

    @classmethod
    def get_kind(cls):
        return "location"

    # Направление рассмотрения
    # inside: bool
    # side_to_gap: dict['g2.Direction', 'g2.open_range']
    side_to_padding: dict['g2.Direction', 'g2.open_range']
    side_to_margin: dict['g2.Direction', 'g2.open_range']
    # Основное направление взгляда для внешних (может быть не определено: None).
    primary_direction: 'g2.Direction | None' = None

    def __init__(self,
                 sides_str: str = None,
                 side_to_gap: dict['g2.Direction|str', 'g2.open_range|str|int'] = None,
                 side_to_padding: dict['g2.Direction', 'g2.open_range'] = None,
                 side_to_margin: dict['g2.Direction', 'g2.open_range'] = None,
                 inside=True,
                 check_implicit_sides=True):
        """  """
        if sides_str:
            side_to_gap = parse_sides_to_gaps(sides_str, "0" if inside else '0+')
        assert side_to_gap, side_to_gap
        if not inside and len(side_to_gap) == 1:
            # Точно знаем, если задана одна сторона взгляда.
            primary_direction = g2.Direction.get(next(iter(side_to_gap)))
            # TODO: В ином случае можно делать предположение о главном направлении,
            # если по одной из осей внешний (!) диапазон сильно больше (или открыт).

        # self.side_to_gap = self._prepare_side_mapping(side_to_gap, check_implicit_sides, inside)
        self.side_to_padding, self.side_to_margin = self._prepare_side_mappings(side_to_gap, check_implicit_sides,
                                                                                inside)

    @classmethod
    def parse(cls, data, context: dict = None):
        """ Parse from string or dict. """
        inside = False
        if 'inside' in context:
            inside = bool(context['inside'])
        elif 'role' in context:
            inside = bool(context['role'].lower() == 'inner')

        if isinstance(data, str):
            return cls(sides_str=data, inside=inside)
        if isinstance(data, dict):
            return cls(side_to_gap=data, inside=inside)
        if isinstance(data, list):
            # transform to dict first
            fixed_data = {}
            for item in data:
                if isinstance(item, str):
                    # no range: treat as strict border
                    fixed_data[item] = '0'
                elif isinstance(item, dict):
                    # name to range
                    fixed_data |= item
                elif isinstance(item, list):
                    # name to range
                    assert len(item) == 2, item
                    fixed_data |= dict([item])

            return cls(side_to_gap=fixed_data, inside=inside)

        raise TypeError(f"{cls.__name__}.parse({data!r}): `str` or `dict` expected!")

    def eval(self, var2value: dict[str, int] = ()) -> bool:
        """ Evaluate the expr for given values of variables """
        # raise NotImplementedError()
        for is_inner, mapping in ((True, self.side_to_padding), (False, self.side_to_margin)):
            for d, range_ in mapping.items():
                look_dir = self._get_component_side(d, is_inner)
                key = self._get_component_side_key(d, is_inner)
                parent_key = self._get_parent_side_key(d)
                if key in var2value and parent_key in var2value:
                    this_coord = var2value[key]
                    parent_coord = var2value[parent_key]
                    diff = (parent_coord - this_coord) * look_dir.coordinate_sign
                    # check range
                    if diff not in range_:
                        return False
                else:
                    raise ValueError(f'Did not pass {key, parent_key} to .eval() of {self!r}, got: {var2value!r}')
        # All checks passed.
        return True

    def _get_component_side(self, d: 'g2.Direction', is_inner=True) -> 'g2.Direction':
        """ Returns `this` box's side
        depending on current state of `inside` flag.
        """
        # Use opposite side for outer components.
        return d if is_inner else d.opposite()

    def _get_component_side_key(self, d: 'g2.Direction', is_inner=True) -> str:
        """ Returns name of `this` box's side
        depending on current state of `inside` flag.
        """
        # Use opposite side for outer components.
        return self._get_component_side(d, is_inner).prop_name

    def _get_parent_side_key(self, d: 'g2.Direction') -> str:
        """ Returns '_'-prepended name of side specified by `d` (usually for parent box).
        """
        return self.component_name_aliases['parent'] + d.prop_name

    def referenced_variables(self) -> list[CoordVar]:
        names = []
        for d in self.side_to_padding.keys():
            names.append(d.prop_name)
            names.append(self._get_parent_side_key(d))
        for d in self.side_to_margin.keys():
            names.append(d.opposite().prop_name)
            names.append(self._get_parent_side_key(d))
        return [CoordVar(name) for name in names]

    def replace_vars(self, var_mapping: dict[str, int | str]):
        """ Change variables in-place """
        raise NotImplementedError()
        # if any(not isinstance(val, str) for val in var_mapping.values()):
        #     raise TypeError(f'{type(self)} does not support replacing variables to scalars (got: {var_mapping}).')
        # # simply replace keys
        # self.side_to_gap = self._prepare_side_mapping_0({
        #     var_mapping.get(key.prop_name, key.prop_name): value
        #     for key, value in self.side_to_gap.items()
        # })

    def clone(self) -> 'LocationConstraint':
        return type(self)(
            side_to_padding=self.side_to_padding,
            side_to_margin=self.side_to_margin,
        )

    @staticmethod
    def _prepare_side_mappings(
            side_to_gap: dict['g2.Direction|str', 'g2.open_range|str|int'],
            check_implicit_sides=True,
            inside=True,
    ) -> tuple[dict['g2.Direction', 'g2.open_range'], dict['g2.Direction', 'g2.open_range']]:
        """ Return: side_to_padding, side_to_margin """

        # pre-process data
        desired_keys = set(side_to_gap.keys())

        default_margin = '*'
        default_padding = '0+'

        # repair & validate data
        paddings = {}
        margins = {}
        for key in desired_keys:
            d, padding_or_margin = location_key_to_side_role(key)

            # 'inner' from key
            if padding_or_margin:
                inner = (padding_or_margin == 'padding')
            else:
                # the default if not set explicitly:
                inner = inside

            value = side_to_gap.get(key, None)
            if value is None:
                # side is not set
                value = default_padding if inner else default_margin
            if not isinstance(value, g2.open_range):
                value = g2.open_range.parse(value)

            # fill resulting mapping
            if inner:
                paddings[d] = value
            else:
                margins[d] = value

        # post-process constraints ...
        if check_implicit_sides and inside:
            # polyfill inside location (paddings) to ensure that component lies inside.
            # '0+', i.e. not intersecting
            non_negative_ray = g2.open_range(0, None)
            for d in g2.Direction.known_instances():
                if d not in paddings:
                    paddings[d] = non_negative_ray

        if check_implicit_sides and not inside and margins:  # outside location (margins) has its own logic.
            # Here, we have input gaps repaired and no extra gaps.

            # 0) Check if any of ranges touch negative area — users tries to do something tricky,
            #  so we should not add anything else.
            negative_ray = g2.open_range(None, -1)
            if paddings or any(gap.intersect(negative_ray) for gap in margins.values()):
                pass
            else:
                # (Here, all gaps are positive.)
                # 1) Check if input requirements do not contradict each other.
                if len(margins) >= 3 or (
                        len(margins) == 2 and
                        # both are horizontal or vertical
                        len(set(d.is_horizontal for d in margins.keys())) == 1
                ):
                    logger.warning('Outer location margins are likely excessive '
                                   f'or contradict each other: {margins!r}.')
                else:
                    # 2) In case of orthogonal constraints we're likely have nothing to add.
                    # pass
                    # 3) In case of single constraint we should add two orthogonal constraints
                    #  to make sure the component is on front of parent.
                    if len(margins) == 1:
                        d = next(iter(margins.keys()))
                        # non_positive_ray = g2.open_range(None, 0)
                        for orthogonal in (d + 90, d - 90):
                            # negative gap implies intersection along other axis.
                            margins[orthogonal] = negative_ray
        # TODO: проверить непротиворечивость paddings и margins (?)
        return paddings, margins

    @staticmethod
    def _prepare_side_mapping_0(
            side_to_gap: dict['g2.Direction|str', 'g2.open_range|str|int'],
            check_implicit_sides=True,
            inside=True,
    ) -> dict['g2.Direction', 'g2.open_range']:

        # pre-process data
        default_range = None
        desired_keys = set(side_to_gap.keys())
        if check_implicit_sides and inside:
            # add all other sides as well
            desired_keys |= set(d.prop_name for d in g2.Direction.known_instances())

            # '0+', i.e. not intersecting
            non_negative_ray = g2.open_range(0, None)
            default_range = non_negative_ray  # if inside else g2.open_range(None, None)

        # repair & validate data
        result = {}
        for key in desired_keys:
            value = side_to_gap.get(key, None)
            if value is None:
                # side is not set
                value = default_range
            if isinstance(key, g2.Direction):
                pass
            elif isinstance(key, str):
                d = g2.Direction.get_by_name(key)
                if not d:
                    raise ValueError(f"LocationConstraint: Cannot recognize direction / side from {key!r}")
                key = d

            if not isinstance(value, g2.open_range):
                value = g2.open_range.parse(value)

            # fill resulting mapping
            result[key] = value

        # post-process constraints
        if check_implicit_sides and not inside:  # outside location has its own logic.
            # Here, we have input gaps repaired and no extra gaps.

            # 0) Check if any of ranges touch negative area — users tries to do something tricky,
            #  so we do not add anything else.
            negative_ray = g2.open_range(None, -1)
            if any(gap.intersect(negative_ray) for gap in result.values()):
                pass
            else:
                # (Here, all gaps are positive.)
                # 1) Check if input requirements do not contradict each other.
                if len(result) >= 3 or (
                        len(result) == 2 and
                        # both are horizontal or vertical
                        len(set(d.is_horizontal for d in result.keys())) == 1
                ):
                    print(f':WARN: outer location constraints are likely excessive or contradict each other: {result!r}.')
                else:
                    # 2) In case of orthogonal constraints we're likely have nothing to add.
                    # pass
                    # 3) In case of single constraint we should add two orthogonal constraints
                    #  to make sure the component is on front of parent.
                    if len(result) == 1:
                        d = next(iter(result.keys()))
                        # non_positive_ray = g2.open_range(None, 0)
                        for orthogonal in (d + 90, d - 90):
                            # negative gap implies intersection along other axis.
                            result[orthogonal] = negative_ray
        return result

    def full_mapping(self) -> dict:
        """ Return serializable union of paddings & margins. """
        return {
            f'{role}-{d.prop_name}': range_
            for role, mapping in (('padding', self.side_to_padding), ('margin', self.side_to_margin))
            for d, range_ in sorted(mapping.items())
        }

    def __str__(self) -> str:
        s = 'LocationConstraint(%s)' % repr(self.full_mapping())
        return s

    __repr__ = __str__

    def __hash__(self):
        return hash(str(self))

    def __lt__(self, other):
        return isinstance(other, type(self)) and str(self) < str(other)


BoolExprRegistry.register(LocationConstraint)


def parse_sides_to_gaps(s: str, range_value="0") -> dict[str, str]:
    """Treats `s` as list of direction names (comma- or/and space-separated).
    Returns a dict with all values set to `range_value` (e.g. zero gaps). """
    parts = re.split(r'\s*[,\s]\s*', s)
    return dict.fromkeys(parts, range_value)


def location_key_to_side_role(key: str) -> tuple['g2.Direction', str | None]:
    """
    Parse location side key that contains a Direction's propname and may include "padding" or "margin" as explicit role
    of the
    constraint.
    :param key: str of form "padding-right", "left margin", "top", "margin_bottom
    :return: 2-tuple of Direction and role ("padding" or "margin" or None if not specified)
    :raises ValueError if any component was not recognized.
    """
    # cut the role out
    for sep in ('-', ' ', '_'):
        if sep in key:
            w1, _, w2 = key.partition(sep)
            if w1 in SIDE_ROLES:
                role = w1
                key = w2
            elif w2 in SIDE_ROLES:
                role = w2
                key = w1
            else:
                raise ValueError(f"LocationConstraint: Cannot find 'padding' or 'margin' in {key!r}")
            break
    else:
        # no separator used
        role = None

    d = g2.Direction.get(key)
    if not d:
        raise ValueError(f"LocationConstraint: Cannot recognize direction / side from {key!r}")
    return d, role
