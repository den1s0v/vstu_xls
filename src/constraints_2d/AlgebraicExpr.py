from constraints_2d.ArbitraryBoolExprBase import ArbitraryBoolExprBase
from constraints_2d.SpatialConstraint import SpatialConstraint

# Helpers for redefining a class >>
AlgebraicExpr_factory_class = None  # global var, can be modified from other module via function below.


def register_AlgebraicExpr_default_subclass(cls):
    """Register default AlgebraicExpr implementation"""
    global AlgebraicExpr_factory_class
    assert issubclass(cls, AlgebraicExpr), f"{cls} does not derive from AlgebraicExpr."
    AlgebraicExpr_factory_class = cls
    # print(' - registered class:', cls)
    # print(' - mro:', cls.mro())


def get_AlgebraicExpr_default_subclass() -> type['AlgebraicExpr']:
    cls = AlgebraicExpr_factory_class or AlgebraicExpr
    return cls


# << Helpers.


class AlgebraicExpr(ArbitraryBoolExprBase, SpatialConstraint):
    """ Система неравенств с переменными, содержащими координаты прямоугольников-компонентов. """

    @classmethod
    def get_kind(cls):
        return "inequality"

    # expr: BoolExpr

    # component_name_aliases = {
    #     'this': '',
    #     'parent': '_',
    # }

    def __new__(cls, *args, **kw):
        """Modified class constructor.
        Expected args: expr_string: str = None, expr: object = None.
        In fact, it returns an instance of class currently registered as default `AlgebraicExpr` implementation """
        obj = object.__new__(get_AlgebraicExpr_default_subclass())
        obj.__init__(*args, **kw)
        return obj
