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

    box_attrs = {  # keys returned by Box.as_dict()
        'x': 'left',
        'y': 'top',
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