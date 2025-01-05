from constraints_2d.BoolExpr import BoolExpr
from constraints_2d.CoordVar import CoordVar


class ArbitraryBoolExprBase(BoolExpr):
    """ Abstract wrapper around an instance of symbolic-math expression """
    __slots__ = ('expr_string', '_expr')

    expr_string: str
    _expr: object

    def __init__(self, expr_string: str = None, expr: object = None):
        self.expr_string = expr_string
        self._expr = expr
        assert self.decidable(), self

    def referenced_variables(self) -> list[CoordVar]:
        raise NotImplementedError(type(self))

    def decidable(self) -> bool:
        raise NotImplementedError(type(self))

    def eval(self, var2value: dict[str, int] = ()) -> bool:
        """ Evaluate the expr for given values of variables """
        raise NotImplementedError(type(self))

    def replace_vars(self, var_mapping: dict[str, int | str]):
        """ Change variables in-place """
        raise NotImplementedError(type(self))

    def assignable_vars(self) -> set[str]:
        """ Find which variables can take values via Equality
            Ex. in `a == b + 1` both `a` and `b` can be "assigned" if the other is materialized.
        """
        raise NotImplementedError(type(self))

    def assigned_vars(self) -> dict[str, int]:
        """ Find which variables have taken values via Equality
            Ex. for `a == 5 and 1 = b` returns: `{'a': 5, 'b': 1}`.
        """
        raise NotImplementedError(type(self))

    def __str__(self) -> str:
        return self.expr_string or str(self._expr)

    def clone(self) -> 'ArbitraryBoolExprBase':
        return type(self)(self.expr_string, self._expr)

    def __and__(self, y: 'ArbitraryBoolExprBase') -> 'ArbitraryBoolExprBase':
        """x&y"""
        raise NotImplementedError(type(self))

    def __or__(self, y: 'ArbitraryBoolExprBase') -> 'ArbitraryBoolExprBase':
        """x|y"""
        raise NotImplementedError(type(self))

    def __xor__(self, y: 'ArbitraryBoolExprBase') -> 'ArbitraryBoolExprBase':
        """x^y"""
        raise NotImplementedError(type(self))

    def __invert__(self) -> 'ArbitraryBoolExprBase':
        """~x"""
        raise NotImplementedError(type(self))
