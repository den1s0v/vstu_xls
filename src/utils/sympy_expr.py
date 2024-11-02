from sympy import Symbol

from constraints_2d import BoolExpr, CoordVar, SpatialConstraint, register_SpatialConstraint_default_subclass
from utils.ast_to_sympy import parse_expression


class SympyExpr(BoolExpr):
    """ Wrapper around SymPy expression """

    def __init__(self, expr_string: str = None, expr: object = None):
        sympy_expr = (expr or parse_expression(expr_string)).simplify()
        super().__init__(expr_string, sympy_expr)

    def referenced_variables(self) -> list[CoordVar]:
        if not hasattr(self._expr, 'atoms'):
            # not a SymPy expression, thus no vars in it.
            return ()
            
        # extract vars
        return [CoordVar(v.name) for v in self._expr.atoms(Symbol)]

    def decidable(self) -> bool:
        return self._expr != False

    def eval(self, var2value = ()) -> bool:
        """ Evaluate the expr for given values of variables """
        if not hasattr(self._expr, 'subs'):
            # not a SymPy expression
            return self._expr
        
        return self._expr.subs(var2value, simultaneous=True)  # `simultaneous=True` avoids possible variable clash
    
    def replace_vars(self, var_mapping: dict[str, str] = ()):
        """ Change variables in-place """
        self._expr = self.eval(var_mapping)
        self.expr_string = str(self._expr)  # update textual repr as well

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
