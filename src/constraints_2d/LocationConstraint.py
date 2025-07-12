from dataclasses import dataclass
import re

from constraints_2d.CoordVar import CoordVar
from constraints_2d.SpatialConstraint import SpatialConstraint
from constraints_2d.BoolExpr import BoolExprRegistry
import geom2d as g2


@dataclass(kw_only=True, repr=True)
class LocationConstraint(SpatialConstraint):
    """ Проверка прилегания сторон компонента к границам области родительского паттерна
    (как изнутри, так и снаружи).
    Для внутреннего расположения точка зрения одинаковая — изнутри;
    Для внешнего расположения точка зрения — со стороны родительского элемента (parent) в сторону компонента (this).;

    """

    @classmethod
    def get_kind(cls):
        return "location"

    inside: bool  # Направление рассмотрения
    side_to_gap: dict['g2.Direction', 'g2.open_range']

    def __init__(self,
                 sides_str: str = None,
                 side_to_gap: dict['g2.Direction|str', 'g2.open_range|str|int'] = None,
                 inside=True, check_implicit_sides=True):
        """  """
        if sides_str:
            side_to_gap = parse_sides_to_gaps(sides_str, "0" if inside else '0+')
        assert side_to_gap, side_to_gap

        self.side_to_gap = self._prepare_side_mapping(side_to_gap, check_implicit_sides, inside)
        self.inside = bool(inside)

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
                if isinstance(item, dict):
                    # name to range
                    fixed_data |= item
                if isinstance(item, list):
                    # name to range
                    assert len(item) == 2, item
                    fixed_data |= dict([item])

            return cls(side_to_gap=fixed_data, inside=inside)

        raise TypeError(f"{cls.__name__}.parse({data!r}): `str` or `dict` expected!")

    def eval(self, var2value: dict[str, int] = ()) -> bool:
        """ Evaluate the expr for given values of variables """
        for d, range_ in self.side_to_gap.items():
            look_dir = self._get_component_side(d)
            key = self._get_component_side_key(d)
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

    def _get_component_side(self, d: 'g2.Direction') -> 'g2.Direction':
        """ Returns `this` box's side
        depending on current state of `inside` flag.
        """
        # Use opposite side for outer components.
        return d if self.inside else d.opposite()

    def _get_component_side_key(self, d: 'g2.Direction') -> str:
        """ Returns name of `this` box's side
        depending on current state of `inside` flag.
        """
        # Use opposite side for outer components.
        return self._get_component_side(d).prop_name

    def _get_parent_side_key(self, d: 'g2.Direction') -> str:
        """ Returns '_'-prepended name of side specified by `d` (usually for parent box).
        """
        return self.component_name_aliases['parent'] + d.prop_name

    def referenced_variables(self) -> list[CoordVar]:
        names = []
        for d in self.side_to_gap.keys():
            names.append(self._get_component_side_key(d))
            names.append(self._get_parent_side_key(d))
        return [CoordVar(name) for name in names]

    def replace_vars(self, var_mapping: dict[str, int | str]):
        """ Change variables in-place """
        if any(not isinstance(val, str) for val in var_mapping.values()):
            raise TypeError(f'{type(self)} does not support replacing variables to scalars (got: {var_mapping}).')
        # simply replace keys
        self.side_to_gap = self._prepare_side_mapping({
            var_mapping.get(key.prop_name, key.prop_name): value
            for key, value in self.side_to_gap.items()
        })

    def clone(self) -> 'LocationConstraint':
        return type(self)(side_to_gap=self.side_to_gap)

    @staticmethod
    def _prepare_side_mapping(
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
            value = side_to_gap.get(key) or default_range
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

    def __str__(self) -> str:
        s = 'LocationConstraint(%s)' % repr({
            d.prop_name: range_
            for d, range_ in sorted(self.side_to_gap.items())
        })
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
