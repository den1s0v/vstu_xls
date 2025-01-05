from sympy import Eq, Symbol, lambdify, Expr as SympyOp

from constraints_2d.ArbitraryBoolExprBase import ArbitraryBoolExprBase
from constraints_2d.BoolExpr import BoolExpr
from constraints_2d.CoordVar import CoordVar
from constraints_2d.AlgebraicExpr import AlgebraicExpr, register_AlgebraicExpr_default_subclass
from constraints_2d.utils.ast_to_sympy import parse_expression


class SympyExpr(AlgebraicExpr):
    """ Adapter to SymPy expression """

    _expr: SympyOp

    def __init__(self, expr_string: str = None, expr: object = None):
        sympy_expr = (expr or parse_expression(expr_string)).simplify()
        expr_string = (expr_string or str(sympy_expr))
        super().__init__(expr_string, sympy_expr)
        self.lambdified = None
        self.vars = None

    def referenced_variables(self) -> list[CoordVar]:
        if self.vars is None:
            if not hasattr(self._expr, 'atoms'):
                # not a SymPy expression, thus no vars in it.
                self.vars = ()

            # extract vars
            self.vars = [CoordVar(v.name) for v in self._expr.atoms(Symbol)]
        return self.vars

    def decidable(self) -> bool:
        return self._expr != False

    def to_callable(self) -> callable:
        expr_vars = self.referenced_variables()
        if not expr_vars:
            # not a SymPy expression
            return lambda: self._expr

        if not self.lambdified:
            self.lambdified = lambdify(expr_vars, self._expr, docstring_limit=0)
        return self.lambdified

    def eval(self, var2value: dict[str, int] = ()) -> bool:
        """ Evaluate the expr for given values of variables """
        # Check if vars provided are sufficient to fully evaluate the expr.
        missing_vars = {str(v) for v in self.referenced_variables()} - set(var2value)
        if missing_vars:
            raise ValueError(f"Cannot evaluate {self}: missing vars {missing_vars}")
        return self.to_callable()(**var2value)

    def _subs(self, var2value=()) -> SympyOp:
        """ Replace given values of variables within the expr """
        if not hasattr(self._expr, 'subs'):
            # not a SymPy expression
            return self._expr

        return self._expr.subs(var2value, simultaneous=True)  # `simultaneous=True` avoids possible variable clash

    def replace_vars(self, var_mapping: dict[str, int | str] = ()):
        """ Change variables in-place """
        self._expr = self._subs(var_mapping)
        if var_mapping and any(isinstance(val, (int, float)) for val in var_mapping.values()):
            # numbers inserted, should try to simplify
            self._expr = self._expr.simplify()
        self.expr_string = str(self._expr)  # update textual repr as well
        self.vars = None
        self.lambdified = None

    def assignable_vars(self) -> set[str]:
        """ Find which variables can take values via Equality 
            Ex. in `a == b + 1` both `a` and `b` can be "assigned" if the other is materialized.
        """
        return extract_vars_with_equality(self._expr)

    def assigned_vars(self) -> dict[str, int]:
        """ Find which variables have taken values via Equality 
            Ex. for `a == 5 and 1 == b` returns: `{'a': 5, 'b': 1}`.
        """
        return extract_var_values_from_sympy_expr(self._expr)

    def __and__(self, y: 'SympyExpr') -> 'SympyExpr':
        """x&y"""
        return type(self)(expr=self._expr & y._expr)

    def __or__(self, y: 'SympyExpr') -> 'SympyExpr':
        """x|y"""
        return type(self)(expr=self._expr | y._expr)

    def __xor__(self, y: 'SympyExpr') -> 'SympyExpr':
        """x^y"""
        return type(self)(expr=self._expr ^ y._expr)

    def __invert__(self) -> 'SympyExpr':
        """~x"""
        return type(self)(expr=~self._expr)


def register_sympy_as_expr_backend():
    """register subclass of AlgebraicExpr"""
    register_AlgebraicExpr_default_subclass(SympyExpr)


def extract_vars_with_equality(expr) -> set[str]:
    """ Find which variables are "assigned" to values via Eq 
            Ex. for `a == 5 and 1 = b` returns: `{'a': 5, 'b': 1}`. """
    var_set = set()
    if hasattr(expr, 'atoms'):
        for eq in expr.atoms(Eq):
            for sym in eq.atoms(Symbol):
                var_set.add(sym.name)
    return var_set


def extract_var_values_from_sympy_expr(expr) -> dict[str, int]:
    """ Find which variables are "assigned" to values via Eq 
            Ex. for `a == 5 and 1 == b` returns: `{'a': 5, 'b': 1}`. """
    var2val = {}
    if hasattr(expr, 'atoms'):
        for eq in expr.atoms(Eq):
            var = None
            val = None
            for arg in eq.args:
                if arg.is_symbol:
                    var = arg.name
                elif arg.is_number:
                    val = int(arg)  # Note domain assumption: any value is int.

            if var is not None and val is not None:
                var2val[var] = val
    return var2val


if __name__ == "__main__":
    register_sympy_as_expr_backend()
