from sympy import Symbol, lambdify

from constraints_2d import BoolExpr, CoordVar, SpatialConstraint, register_SpatialConstraint_default_subclass
from utils.ast_to_sympy import parse_expression


class SympyExpr(BoolExpr):
    """ Wrapper around SymPy expression """

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

    def eval(self, var2value = ()) -> bool:
        """ Evaluate the expr for given values of variables """
        return self.to_callable()(**var2value)
    
    def _subs(self, var2value = ()) -> object:
        """ Replace given values of variables within the expr """
        if not hasattr(self._expr, 'subs'):
            # not a SymPy expression
            return self._expr
        
        return self._expr.subs(var2value, simultaneous=True)  # `simultaneous=True` avoids possible variable clash
    
    def replace_vars(self, var_mapping: dict[str, str] = ()):
        """ Change variables in-place """
        self._expr = self._subs(var_mapping)
        self.expr_string = str(self._expr)  # update textual repr as well
        self.vars = None
        self.lambdified = None

    def __and__(self, y: 'SympyExpr') -> 'SympyExpr':
        """x&y""" 
        return type(self)(expr = self._expr & y._expr)
    def __or__(self, y: 'SympyExpr') -> 'SympyExpr':
        """x|y""" 
        return type(self)(expr = self._expr | y._expr)
    def __xor__(self, y: 'SympyExpr') -> 'SympyExpr':
        """x^y""" 
        return type(self)(expr = self._expr ^ y._expr)
    def __invert__(self) -> 'SympyExpr':
        """~x""" 
        return type(self)(expr = ~self._expr)



class SpatialConstraintSympyBacked(SympyExpr, SpatialConstraint):
    """ Diamond-inherited class to get all features in one """
    pass

def register_sympy_as_expr_backend():
    """register subclass of SpatialConstraint"""
    register_SpatialConstraint_default_subclass(SpatialConstraintSympyBacked)


if __name__ == "__main__":
    register_sympy_as_expr_backend()
