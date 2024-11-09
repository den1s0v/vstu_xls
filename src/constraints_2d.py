# constraints_2d.py

from geom2d import Box


# Helpers for redefining a class >>
SpatialConstraint_factory_class = None  # global var, can be modified from other module via function below.

def register_SpatialConstraint_default_subclass(cls):
    """Register default SpatialConstraint implementation"""
    global SpatialConstraint_factory_class
    assert issubclass(cls, SpatialConstraint), f"{cls} does not derive from SpatialConstraint."
    SpatialConstraint_factory_class = cls
    # print(' - registered class:', cls)
    # print(' - mro:', cls.mro())

def get_SpatialConstraint_default_subclass() -> type:
    cls = SpatialConstraint_factory_class or SpatialConstraint
    return cls

# << Helpers.


class CoordVar:
    """ Имя переменной в форме `[[<component>]_]<attr>` ,
    где <attr> относится к одному из параметров прямоугольника на плоскости
    """

    __slots__ = ('component', 'attr')

    component: str  # prefix, can be empty
    attr: str  # x, left, y, top, right, bottom

    valid_attrs = (
        'x', 'left', 'L',
        'y', 'top', 'T',
        'right', 'R',
        'bottom', 'B',
        'width', 'w', 'W',
        'height', 'h', 'H',
        # 'start', 'S',
        # 'end', 'E',
        # 'size', 'length', 'D',  # 'D': L & S were taken :)
    )

    box_attrs = {
        'L': 'left',
        'T': 'top',
        'R': 'right',
        'B': 'bottom',
        'W': 'w',
        'H': 'h',
        'width': 'w',
        'height': 'h',
        # 'S': 'start',
        # 'E': 'end',
        # 'D': 'length',
    }

    def __init__(self, var_name: str):
        self.component, attr_name = self.split_component_attr(var_name)
        self.attr = self.validate_attr(attr_name)

    @property
    def var_name(self) -> str:
        if self.component and self.component != '_':
            sep = '_'
        else:
            sep = ''
        return f"{self.component}{sep}{self.attr}"
    
    def __str__(self): return self.var_name

    def attr_for_box(self) -> str:
        return self.box_attrs.get(self.attr, self.attr)

    @classmethod
    def validate_attr(cls, attr_name: str) -> str:
        assert attr_name in (cls.valid_attrs), f"Unknown attribute name: '{attr_name}' (expected one of: {cls.valid_attrs})."
        return attr_name

    @classmethod
    def split_component_attr(cls, var_name: str) -> tuple[str, str]:
        """ Examples:
            `'var_name_x'` => (`'var_name'`, `'x'`);
            `'_x'` => (`'_'`, `'x'`);
            `'x'` => (`''`, `'x'`).
        """
        parts = var_name.rsplit('_', maxsplit=1)
        attr_name = parts[-1]
        if len(parts) == 1:
            component = ''
        else:
            component = parts[0] or '_'
        return component, attr_name

    def clone(self) -> 'CoordVar':
        return type(self)(self.var_name)


class BoolExpr:
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

    def replace_vars(self, var_mapping: dict[str, str]):
        """ Change variables in-place """
        raise NotImplementedError(type(self))

    def __str__(self) -> str:
        return self.expr_string or str(self._expr)

    def clone(self) -> 'BoolExpr':
        return type(self)(self.expr_string, self._expr)

    def __and__(self, y: 'BoolExpr') -> 'BoolExpr':
        """x&y"""
        raise NotImplementedError(type(self))
    def __or__(self, y: 'BoolExpr') -> 'BoolExpr':
        """x|y"""
        raise NotImplementedError(type(self))
    def __xor__(self, y: 'BoolExpr') -> 'BoolExpr':
        """x^y"""
        raise NotImplementedError(type(self))
    def __invert__(self) -> 'BoolExpr':
        """~x"""
        raise NotImplementedError(type(self))


class SpatialConstraint(BoolExpr):
    """ Система неравенств с переменными, содержащими координаты прямоугольников-компонентов. """
    # expr: BoolExpr

    component_name_aliases = {
        'this': '',
        'parent': '_',
    }

    def __new__(self, *args, **kw):
        """Modified class constructor.
        In fact, it returns an instance of class currently registered as default `SpatialConstraint` implementation """
        obj = object.__new__(get_SpatialConstraint_default_subclass())
        obj.__init__(*args, **kw)
        return obj

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

    def referenced_components(self) -> set[str]:
        components = {var.component for var in self.referenced_variables()}
        return components

    def eval_with_components(self, component2box: dict[str, Box]) -> bool:
        var_name2value = self._map_vars_to_component_coordinates(component2box)
        return self.eval(var_name2value)

    def inline_component_positions(self, component2box: dict[str, Box]):
        var_name2value = self._map_vars_to_component_coordinates(component2box)
        self.replace_vars(var_name2value)
        return self

    def replace_components(self, mapping: dict[str, str]):
        """ Rename variables — change leading parts of variables so these denote different components. In-place. """
        vars_mapping = self._vars_mapping_for_replacing_components(mapping)
        self.replace_vars(vars_mapping)
        return self


    def _fit_component_mapping(self, mapping: set[str]):
        """ Update mapping to utilize component_name_aliases to exisiting components if required """
        this_components = self.referenced_components()
        components_requested = set(mapping.keys())
        unmatched_components = components_requested - this_components

        if unmatched_components:
            known_aliases = set(self.component_name_aliases.keys())
            unknown_components = unmatched_components - known_aliases
            assert not unknown_components, f"Cannot map components {unknown_components} on expression `{self}`."

            for name in unmatched_components & known_aliases:
                alias = self.component_name_aliases[name]
                # replace key in given mapping
                mapping[alias] = mapping[name]
                del mapping[name]

        return mapping


    def _vars_mapping_for_replacing_components(self, component_mapping: dict[str, str]):
        component_mapping = self._fit_component_mapping(component_mapping)
        var_names_mapping = {}
        for v in self.referenced_variables():
            if v.component in component_mapping:
                target_component = component_mapping[v.component]
                new_var = v.clone()
                new_var.component = target_component  # change `component` in the copy
                var_names_mapping[v.var_name] = new_var.var_name
        return var_names_mapping


    def _map_vars_to_component_coordinates(self, component2box: dict[str, Box]) -> dict[str, int]:
        component2box = self._fit_component_mapping(component2box)
        var_name2value = {}
        for v in self.referenced_variables():
            if v.component in component2box:
                box = component2box[v.component]
                try:
                    value = getattr(box, v.attr_for_box())
                except AttributeError:
                    raise AttributeError(v, v.attr, f'Cannot read {v.attr} from Box instance.')
                var_name2value[v.var_name] = value
        return var_name2value













# \\\\\\\\\\\\\\\\\\

# relations_2d.py

""" Пространственные взаимоотношения двумерных прямоугольных структур. """


"""

Экземпляр взаимоотношения связывает описание элементов для спецификации 2D-грамматики.



○ Relation2d  # Взаимоотношение элементов
  |
  ○ Item  # Элемент, компонент.
  |
  ○ Aggregation  # Включающее отношение. Агрегация содержит элементы, находящиеся в общих рамках.
  | |
  | ○ Structure  # содержит именованные элементы (которые не пересекаются)
  | |
  | ○ Collection  #  содержит однотипные элементы (которые не пересекаются)
  |  |
  |  ○ Array  # ← элементы коллекции пространственно упорядочены
  |    |
  |    ○ LineArray  # Ряд — горизонтальный либо вертикальный
  |    ○ FillArray  # связная область "заливки" элементами / AdjacentCellsArea
  |
  |
  ○ Ousting  # Взаимное вытеснение (всех элементов)
  ○ Opposition  # Сопоставление на удалении (друг напротив друга)
  ○ Intersection  # Комбинация пересечением

"""

