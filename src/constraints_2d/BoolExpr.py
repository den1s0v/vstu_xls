from constraints_2d.CoordVar import CoordVar


class BoolExpr:
    """ Абстракция логического выражения """

    def eval(self, var2value: dict[str, int] = ()) -> bool:
        """ Evaluate the expr for given values of variables """
        raise NotImplementedError(type(self))

    def referenced_variables(self) -> list[CoordVar]:
        raise NotImplementedError(type(self))

    @classmethod
    def get_kind(cls):
        return "Base BoolExpr"


class BoolExprRegistry:
    registry = {}

    @classmethod
    def register(cls, boolexpr_cls):
        # Регистрация подкласса в реестре по его kind
        kind = boolexpr_cls.get_kind()
        cls.registry[kind] = boolexpr_cls

    @classmethod
    def get_class_by_kind(cls, kind: str) -> 'type|None':
        boolexpr_cls = cls.registry.get(kind)
        if not boolexpr_cls:
            print('WARN: no BoolExpr having kind = `%s`' % kind)
        return boolexpr_cls

