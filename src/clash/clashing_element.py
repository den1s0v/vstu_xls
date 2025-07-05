# clashing_element.py

from functools import cache
from typing import Hashable, Iterable, override

from adict import adict

from utils import safe_adict

# Функция (obj1, obj2) -> bool
_pair_compatibility_checker: callable = None


def trivial_components_getter(container):
    """ No-op function that just returns its argument. """
    return container


def set_pair_compatibility_checker(func):
    global _pair_compatibility_checker
    assert callable(func)
    _pair_compatibility_checker = func


def retain_longest_only(objects: set | list | Iterable) -> set:
    if len(objects) > 1:
        with_sizes = [(len(obj), obj) for obj in objects]
        with_sizes.sort(reverse=True, key=lambda t: t[0])
        top_len = with_sizes[0][0]
        objects = {t[1] for t in with_sizes if len(t[1]) == top_len}
    return objects


class ObjWithDataWrapper(Hashable):
    """ A generic wrapper for an arbitrary Hashable object,
        optionally associated with some arbitrary data.
    """
    _obj: Hashable
    data: safe_adict
    _hash: int

    def __init__(self, obj: Hashable, data: adict = None):
        self._obj = obj
        self.data = safe_adict(data or {})
        try:
            self._hash = hash(obj)
        except TypeError:
            # Fallback: instance identity
            self._hash = id(self.obj)

    @property
    def obj(self) -> Hashable:
        return self._obj

    def __hash__(self):
        return self._hash

    def __eq__(self, other):
        return self._hash == hash(other)

    def __lt__(self, other):
        if isinstance(other, ObjWithDataWrapper):
            return self._obj < other._obj
        else:
            raise TypeError(
                f"'<' not supported between instances of '{type(self).__name__}' and '{type(other).__name__}'")

    def __repr__(self):
        return f"{type(self).__name__}({self._obj!r})"

    def __str__(self):
        return f"<{self._obj}>"


class ClashingElement(ObjWithDataWrapper):
    """ Internal wrapper around an object involved into clashing sets """

    # clashes_with: frozenset['ClashingElement']
    # cluster: None | int

    @cache
    def clashes_with(self, other: 'ClashingElement') -> bool:
        assert _pair_compatibility_checker
        return not _pair_compatibility_checker(self.obj, other.obj)

    def all_clashing_among(self, others) -> 'ClashingElementSet':
        """ Note: Does not clash to itself """
        if self.data.globally_clashing is not None:
            # Note: see `fill_clashing_elements()`.
            return ClashingElementSet(
                self.data.globally_clashing & set(others)
            )
        # else: fallback
        return ClashingElementSet(other for other in others if (other != self) and self.clashes_with(other))
        # TODO: use `!=`, not `is not` ???

    def all_independent_among(self, others) -> 'ClashingElementSet':
        """ Note: Not independent of itself """
        if self.data.globally_clashing is not None:
            # Note: see `fill_clashing_elements()`.
            return ClashingElementSet(
                set(others) - self.data.globally_clashing
            )
        # else: fallback
        return ClashingElementSet(other for other in others if (other != self) and not self.clashes_with(other))
        # TODO: use `!=`, not `is not` ???

    def clone(self):
        return type(self)(**self.__dict__)


class ClashingContainer(ClashingElement):
    """ A kind of ClashingElement that consists of `ClashingComponent`s and
    the fact of clash is determined by the
    presence of common components. """
    _components: frozenset['ClashingComponent']

    def __init__(self, obj: Hashable, data: adict = None, components: set['ClashingComponent'] = None):
        super().__init__(obj, data)
        self._components = frozenset(components) if components is not None else frozenset()

    @property
    def components(self) -> frozenset['ClashingComponent']:
        return self._components

    def __str__(self):
        return f"{type(self).__name__}({self.obj!r}, components={self.components})"

    # _all_directly_overlapping_cache = None

    def clashes_with(self, other: 'ClashingContainer') -> bool:
        assert isinstance(other, ClashingContainer), type(other)
        return any(component in other.components for component in self.components)

    def clone(self):
        fields = {
            'obj': self.obj,
            'data': self.data,
            # clone components as well
            'components': {cm.clone() for cm in self.components},
        }
        return type(self)(**fields)

    # def on_remove_from_set(self):
    #     # delete from related components
    #     for component in self.components:
    #         component.unbind_from(self)
    #         # component.belongs_to.remove(self)


class ClashingComponent(ObjWithDataWrapper):
    """ A part of one or more `ClashingContainer`s. """

    def __init__(self, obj: Hashable, data: adict = None):
        super().__init__(obj, data)

    def __str__(self):
        return f"{type(self).__name__}({self.obj!r})"

    def clone(self):
        fields = {
            'obj': self.obj,
            'data': self.data,
        }
        return type(self)(**fields)

    # def unbind_from(self, element: ClashingContainer):
    #     if element in self.belongs_to:
    #         self.belongs_to.remove(element)


class ClashingElementSet(set['ClashingElement'], Hashable):

    # def __init__(self, *args, **kw):
    #     super().__init__(*args, **kw)
    #     ...

    @override
    def remove(self, *elements: 'ClashingElement'):
        for element in elements:
            if element not in self:
                continue
            # remove as usual
            super().remove(element)

    def with_removed(self, *elements: 'ClashingElement') -> 'ClashingElementSet':
        s = self.clone()
        s.remove(*elements)
        return s

    @cache
    def free_subset(self) -> 'ClashingElementSet':
        """ Make a subset that it contains only elements not clashing with any other (in this) """
        s = type(self)()
        for el in self:
            if not el.all_clashing_among(self):
                s.add(el.clone())

        return s

    def get_all_clashing(self) -> 'ClashingElementSet':
        """ Make a subset that it contains only elements not clashing with any other (in this) """
        s = type(self)()
        for el in self:
            for sub_el in el.data.globally_clashing:
                s.add(sub_el.clone())

        return s

    @classmethod
    def make(cls,
             elements: Iterable,
             # pair_compatibility_checker=None,
             components_getter=None) -> 'ClashingElementSet':

        # Вспомогательное для объединения и наполнения компонентов
        hash2component: dict[int, ClashingComponent] = {}

        def get_component(component_obj) -> ClashingComponent:
            """ Get or create component """
            h = hash(component_obj)
            comp = hash2component.get(h)
            if not comp:
                hash2component[h] = comp = ClashingComponent(component_obj)
            return comp

        # Подготовить объекты, упаковав их в наши обёртки
        clashing_elements = []

        for element in elements:
            if components_getter:
                el = ClashingContainer(obj=element, components={
                    get_component(component)  #, el)
                    for component in components_getter(element)
                })
            else:
                el = ClashingElement(obj=element)

            clashing_elements.append(el)

        return cls(clashing_elements)

    def clone(self) -> 'ClashingElementSet':
        """Deep clone"""
        return type(self)(el.clone() for el in self)

    def get_bare_objs(self) -> list:
        # Extract objects back, sort for stability
        arr = [clash_elem.obj for clash_elem in self]
        arr.sort()
        return arr

    def __hash__(self):
        # return hash(tuple(sorted(self)))
        return hash(frozenset(self))


class Arrangement(ClashingElementSet):
    """ A set of mutually compatible elements.
     Primary addition method `try_add` may refuse if the new element is incompatible with the existing.
     """
    incompatible: ClashingElementSet

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.incompatible = self.find_all_incompatible()

    def try_add(self, new_elem: ClashingElement) -> bool:
        """Returns True if given element was added successfully or already present (i.e. not refused to add)."""
        if new_elem in self.incompatible:
            # We do not expect the new one.
            return False
        external_incompatible = new_elem.data.globally_clashing or set()
        if external_incompatible & self:
            # We have some elements incompatible with the new one.
            return False

        # Register it
        self.add(new_elem)
        self.incompatible |= external_incompatible

        return True

    def try_add_all(self, new_elements: Iterable[ClashingElement]) -> tuple[bool, set]:
        """Returns True if all given elements were added successfully"""
        ok = True
        not_added = set()
        for new_elem in new_elements:
            success = self.try_add(new_elem)
            ok = ok and success
            if not success:
                not_added.add(new_elem)
        return ok, not_added

    def find_all_incompatible(self) -> ClashingElementSet:
        """ Return from universe the elements that do clash with this set. """
        all_incompatible = ClashingElementSet()
        for el in self:
            incompatible = el.data.globally_clashing or set()
            all_incompatible |= incompatible
        return all_incompatible

    def select_candidates_from(self, universe: ClashingElementSet | set) -> ClashingElementSet:
        """ Retain only elements that are compatible with this set. """

        selected_candidates = ClashingElementSet(universe - self - self.incompatible)

        return selected_candidates

    def get_outer_neighbours(self) -> ClashingElementSet:
        """ Get elements of universe that are not in this set
        and are "neighbours"
        (i.e. close to elements of this set in the sense that they have common clashing
        elements). """

        neighbours = ClashingElementSet({
            neighbour
            for el in self
            for neighbour in el.data.neighbours
        })

        return self.select_candidates_from(neighbours)

    def select_neighbours_from(self, universe: ClashingElementSet | set) -> ClashingElementSet:
        """ Retain only elements that are compatible with this set
        and are "neighbours"
        (i.e. close to elements of this set in the sense that they have common clashing elements). """

        selected_candidates = ClashingElementSet(self.get_outer_neighbours() & self.select_candidates_from(universe))

        return selected_candidates

    def closest_neighbours_from(self, universe: ClashingElementSet | set) -> ClashingElementSet:
        """ Retain only elements that are all compatible with this set
        and are "neighbours" & having the largest number on common clashes.
         """

        all_globally_clashing_with_this_set = {
            clashing_element
            for elem in self
            for clashing_element in (elem.data.globally_clashing or ())
        }

        rating_candidate_list: list[tuple[int, ClashingElement]] = []  # (count of common clashes, candidate)

        for ext_elem in universe:
            ext_clashing_elements = ext_elem.data.globally_clashing or set()
            common = all_globally_clashing_with_this_set & ext_clashing_elements
            if common:
                rating_candidate_list.append((
                    len(common), ext_elem
                ))

        rating_candidate_list.sort(key=lambda t: t[0], reverse=True)

        addable_arrangement = Arrangement()

        # Adding starting from the closest, keeping the most close elements
        addable_arrangement.try_add_all(t[1] for t in rating_candidate_list)

        return self.select_candidates_from(addable_arrangement)

    def closest_neighbour_sets_from(self, universe: ClashingElementSet | set) -> set[ClashingElementSet]:
        """ Retain only elements that are all compatible with this set
        and are "neighbours" & having the largest number on common clashes.
         """

        all_globally_clashing_with_this_set = {
            clashing_element
            for elem in self
            for clashing_element in (elem.data.globally_clashing or ())
        }

        rating_candidate_list: list[tuple[int, ClashingElement]] = []  # (count of common clashes, candidate)

        for ext_elem in universe:
            ext_clashing_elements = ext_elem.data.globally_clashing or set()
            common = all_globally_clashing_with_this_set & ext_clashing_elements
            if common:
                rating = len(common)
                rating_candidate_list.append((
                    rating, ext_elem
                ))
                # # save rating in metadata
                # ext_elem.data._rating = rating

        rating_candidate_list.sort(key=lambda t: t[0], reverse=True)

        addable_arrangement = Arrangement()

        # Adding starting from the closest, keeping the most close elements
        candidate_list = [t[1] for t in rating_candidate_list]
        _, extra_1 = addable_arrangement.try_add_all(candidate_list)
        size_1 = len(addable_arrangement)
        
        neighbour_sets = {
            self.select_candidates_from(addable_arrangement),
        }
        
        if extra_1:
            # Возможны альтернативные варианты
            top_rating_sum = sum(t[0] for t in rating_candidate_list if t[1] not in extra_1)
            # try to find another combinations starting from not used (extra) elements
            for extra_elem in extra_1:
                arrangement_2 = Arrangement()
                _, extra_2 = arrangement_2.try_add_all([extra_elem] + candidate_list)
                size_2 = len(arrangement_2)
                rating_sum_2 = sum(t[0] for t in rating_candidate_list if t[1] not in extra_2)
                if size_2 > size_1 or rating_sum_2 >= top_rating_sum:
                    # Found another good arrangement: at least the same rating or higher coverage
                    # Note: changing to `size_2 >= size_1` makes it slower by 7 times. This does not make it smarter.
                    neighbour_sets.add(
                        self.select_candidates_from(arrangement_2)
                    )

        # Это ускоряет в 2-3 раза.
        # Отфильтровать: взять только самые длинные.
        if len(neighbour_sets) > 1:
            neighbour_sets = retain_longest_only(neighbour_sets)

        return neighbour_sets

    def clone(self) -> 'Arrangement':
        """Deep clone"""
        obj: Arrangement = super().clone()
        obj.incompatible = self.incompatible.clone()
        return obj
