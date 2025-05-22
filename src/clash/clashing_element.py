# clashing_element.py

from functools import cache
from typing import Any, Hashable, Iterable, override
# from collections import Or

from dataclasses import field, dataclass, asdict
from adict import adict

# Функция (obj1, obj2) -> bool
_pair_compatibility_checker: callable = None


def set_pair_compatibility_checker(func):
    global _pair_compatibility_checker
    assert callable(func)
    _pair_compatibility_checker = func


@dataclass()
class ObjWithDataWrapper(Hashable):
    """ A generic wrapper for an arbitrary object, 
        optionally associated with some arbitrary data
    """
    obj: Hashable
    data: adict = field(default_factory=adict)

    def __hash__(self):
        try:
            return hash(self.obj)
        except TypeError:
            # Fallback: instance identity
            return id(self.obj)
        raise f"Unexpected TypeError: unhashable type: '{type(obj).__name__}'"

    def __eq__(self, other):
        return hash(self) == hash(other)

    def __repr__(self):
        return f"{type(self).__name__}({self.obj!r})"


class ClashingElement(ObjWithDataWrapper):
    # clashes_with: set['ClashingElement']
    # cluster: None | int

    def clashes_with(self, other: 'ClashingElement') -> bool:
        assert _pair_compatibility_checker
        return not _pair_compatibility_checker(self.obj, other.obj)

    def all_clashing_among(self, others) -> set['ClashingElement']:
        """ Note: Does not clash to itself """
        return {other for other in others if (other is not self) and self.clashes_with(other)}

    def all_independent_among(self, others) -> set['ClashingElement']:
        """ Note: Not independent from itself """
        return {other for other in others if (other is not self) and not self.clashes_with(other)}

    def clone(self):
        return type(self)(**asdict(self))

    def on_remove_from_set(self):
        # nothing to do
        pass

    def __hash__(self):
        return super().__hash__()


@dataclass()
class ClashingContainer(ClashingElement):
    components: set['ClashingComponent'] = field(default_factory=set)

    # _all_directly_overlapping_cache = None

    def clashes_with(self, other: 'ClashingContainer') -> bool:
        assert isinstance(other, ClashingContainer), type(other)
        return bool(self.components & other.components)

    def is_free(self):
        return all(
            self in i.belongs_to and len(i.belongs_to) == 1
            for i in self.components)

    @cache
    def all_directly_overlapping(self, ) -> set['ClashingContainer']:
        return {other
                for component in self.components
                for other in component.belongs_to
                if other is not self
                }

    def all_clashing_among(self, others) -> set['ClashingContainer']:
        # optimized version
        return set(others) & self.all_directly_overlapping()

    def all_independent_among(self, others) -> set['ClashingContainer']:
        # optimized version
        return set(others) - self.all_directly_overlapping()

    def clone(self):
        fields = {
            'obj': self.obj,
            'data': self.data,
            # clone components as well
            'components': {cm.clone() for cm in self.components},
        }
        return type(self)(**fields)

    def on_remove_from_set(self):
        # delete from related components
        for component in self.components:
            component.unbind_from(self)
            # component.belongs_to.remove(self)

    def __hash__(self):
        return super().__hash__()

    def __eq__(self, other):
        return super().__eq__(other)

    def __repr__(self):
        return super().__repr__()


@dataclass()
class ClashingComponent(ObjWithDataWrapper):
    belongs_to: set['ClashingContainer'] = field(default_factory=set)

    def clone(self):
        fields = {
            'obj': self.obj,
            'data': self.data,
            # re-create set
            'belongs_to': set(self.belongs_to),
        }
        return type(self)(**fields)

    def unbind_from(self, element: ClashingContainer):
        if element in self.belongs_to:
            self.belongs_to.remove(element)

    def __hash__(self):
        return super().__hash__()

    def __eq__(self, other):
        return super().__eq__(other)

    def __repr__(self):
        return super().__repr__()


# @dataclass()
class ClashingElementSet(set['ClashingElement']):
    # elements: set['ClashingElement']

    @override
    def remove(self, *elements: 'ClashingElement'):
        for element in elements:
            if element not in self:
                continue
            # remove as usual
            super().remove(element)
            # trigger changes
            element.on_remove_from_set()

    def with_removed(self, *elements: 'ClashingElement'):
        s = self.clone()
        s.remove(*elements)
        return s

    def free_subset(self):
        """ Make a subset that it contains only elements not clashing with any other (in this) """
        s = type(self)()
        for el in self:
            if not el.all_clashing_among(self):
                s.add(el.clone())

        return s

    @classmethod
    def make(cls,
             elements: Iterable,
             # pair_compatibility_checker=None,
             components_getter=None) -> 'ClashingElementSet':

        # Вспомогательное для объединения и наполнения компонентов
        hash2component: dict[int, ClashingComponent] = {}

        def get_component(component_obj, container: ClashingContainer) -> ClashingComponent:
            """ Get or create component """
            h = hash(component_obj)
            comp = hash2component.get(h)
            if not comp:
                hash2component[h] = comp = ClashingComponent(component_obj)
            comp.belongs_to.add(container)
            return comp

        # Подготовить объекты, упаковав их в наши обёртки
        clashing_elements = []

        for element in elements:
            if components_getter:
                el = ClashingContainer(obj=element)
                el.components = {
                    get_component(component, el)
                    for component in components_getter(element)
                }
            else:
                el = ClashingElement(obj=element)

            clashing_elements.append(el)

        return cls(clashing_elements)

    def clone(self) -> 'ClashingElementSet':
        """Deep clone"""
        return type(self)(el.clone() for el in self)

    def get_bare_objs(self) -> list:
        # Extract objects back
        return [clash_elem.obj for clash_elem in self]
