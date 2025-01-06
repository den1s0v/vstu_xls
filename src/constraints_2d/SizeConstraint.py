from constraints_2d.CoordVar import CoordVar
from constraints_2d.SpatialConstraint import SpatialConstraint
from constraints_2d.BoolExpr import BoolExprRegistry
from geom2d import parse_size_range


class SizeConstraint(SpatialConstraint):
    """ Проверка размера элемента. """

    @classmethod
    def get_kind(cls):
        return "size"

    _predicates: dict[str, callable]

    def __init__(self, size_range_tuple: tuple | list = None, size_range_str: str = None):
        """ Pass either: `size_range_str='4+ x 1..2'` or `size_range_tuple=(range(4, 999), range(1, 3))` """
        if size_range_str:
            size_range_tuple = parse_size_range(size_range_str)
        assert size_range_tuple, size_range_tuple
        assert len(size_range_tuple) == 2, size_range_tuple

        functions = (range_.__contains__ for range_ in size_range_tuple)
        self._predicates = dict(zip('wh', functions))

    def eval(self, var2value: dict[str, int] = ()) -> bool:
        """ Evaluate the expr for given values of variables """
        return all(
            self._eval_predicate(key, value)
            for key, value in var2value.items()
            if key in self._predicates  # ← guard off extra args
        )

    def referenced_variables(self) -> list[CoordVar]:
        return [CoordVar(ch) for ch in self._predicates.keys()]

    def replace_vars(self, var_mapping: dict[str, int | str]):
        """ Change variables in-place """
        if any(not isinstance(val, str) for val in var_mapping.values()):
            raise TypeError(f'{type(self)} does not support replacing variables to scalars (got: {var_mapping}).')
        # simply replace keys
        self._predicates = {
            var_mapping.get(key, key): value
            for key, value in self._predicates.items()
        }

    def _eval_predicate(self, key: str, value: int) -> bool:
        """ Evaluate one of predicates with given value of dimension """
        assert key in self._predicates, (key, [*self._predicates.keys()])

        f = self._predicates[key]
        return f(value)


BoolExprRegistry.register(SizeConstraint)
