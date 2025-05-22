# clashing_element.py

from functools import cache
from typing import Any, Hashable, Iterable, override
# from collections import Or

from dataclasses import Field, dataclass, asdict
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
    data: adict = Field(default_factory=adict)

    def __hash__(self):
        try:
            return hash(self.obj)
        except:
            # Fallback: instance identity
            return id(self.obj)



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
    

@dataclass()
class ClashingContainer(ClashingElement):
    components: set['ClashingComponent']
    # _all_directly_overlapping_cache = None
    
    def clashes_with(self, other: 'ClashingContainer') -> bool:
        assert isinstance(other, ClashingContainer), type(other)
        return bool(self.components & other.components)
    
    def is_free(self):
        return all(
            self in i.belonds_to and len(i.belonds_to) == 1
            for i in self.components)

    @cache
    def all_directly_overlapping(self, ) -> set['ClashingContainer']:
        return {other
                for component in self.components
                for other in component.belonds_to
                if other is not self
                }

    def all_clashing_among(self, others) -> set['ClashingContainer']:
        # optimized version
        return set(others) & self.all_directly_overlapping()

    def all_independent_among(self, others) -> set['ClashingContainer']:
        # optimized version
        return set(others) - self.all_directly_overlapping()

    def clone(self):
        fields = asdict(self)
        # clone components as well
        fields['components'] = {cm.clone() for cm in self.components}
        return type(self)(**fields)

    def on_remove_from_set(self):
        # delete from related components
        for component in self.components:
            component.belonds_to.remove(self)


@dataclass()
class ClashingComponent(ObjWithDataWrapper):
    belonds_to: set['ClashingContainer']
    
    def clone(self):
        fields = asdict(self)
        # re-create set
        fields['belonds_to'] = set(self.belonds_to)
        return type(self)(**fields)
    
    
    

# @dataclass()
class ClashingElementSet(set['ClashingElement']):
    # elements: set['ClashingElement']

    @override
    def remove(self, *elements: 'ClashingElement'):
        for element in elements:
            # trigger changes
            element.on_remove_from_set()
            # remove as usual
            super().remove(element)

    def with_removed(self, *elements: 'ClashingElement'):
        s = self.clone()
        s.remove(*elements)
        return s

    def free_subset(self):
        """ Make a subset that it contains only elements not clashing with any other (in this) """
        s = type(self)()
        for el in self:
            if not el.all_clashing_among(*self):
                s.add(el.clone())
                
        return s

    @classmethod
    def make(cls,
             elements: Iterable,
             # pair_compatibity_checker=None,
             components_getter=None) -> 'ClashingElementSet':

        # Вспомогательное для объединения и наполнения компонентов
        hash2component: dict[int, ClashingComponent] = {}

        def get_component(component_obj, container: ClashingContainer) -> ClashingComponent:
            """ Get or create component """
            h = hash(component_obj)
            comp = hash2component.get(h)
            if not comp:
                hash2component[h] = comp = ClashingComponent(component_obj)
            comp.belonds_to.add(container)
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

    def get_bare_objs(self) -> set:
        # Extract objects back
        return {clash_elem.obj for clash_elem in self}
