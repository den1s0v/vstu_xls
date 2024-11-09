# grammar2d.py

from collections import defaultdict
from dataclasses import dataclass
from functools import reduce
from operator import and_
from typing import Optional, Union

from confidence_matching import CellType
from constraints_2d import SpatialConstraint
from utils import WithCache


GRAMMAR: 'Grammar' = None

@dataclass
class PatternComponent(WithCache):
    """ Обёртка над элементом грамматики, которая позволяет задать его отношение к родительскому элементу (родитель — это контейнер для компонента).
        Точность определения этого компонента вносит вклад в точность определения родительского элемента (объём вклада также зависит от `weight`).
        Компонент может быть опциональным и отсутствовать на практике, — в этом случае он не вносит вклад в точность определения родительского элемента.
    """
    name: str  # имя компонента по отношению к родителю.

    element_name: str  # имя дочернего элемента, включаемого в родительский как компонент.

    _element: 'GrammarElement' = None  # дочерний элемент грамматики
    @property
    def element(self) -> 'GrammarElement':
        """дочерний элемент грамматики"""
        if not self._element:
            self._element = GRAMMAR[self.element_name]  # TODO: assign GRAMMAR befor usage.
        return self._element


    constraints: list[SpatialConstraint]  # "Локальные" ограничения, накладываемые на расположение этого компонента по отношению к родителю. Используются координаты текущего дочернего элемента и родительского элемента. Также могут использоваться координаты других компонентов родителя, которые были определены по списку компонентов выше этого компонента. "Локальные" означает, то для записи координат может быть использована сокращёная форма: 'x' — свой 'x', '_x' — 'x' родителя, и т.п.

    weight: float = 1  # (-∞, ∞) вес компонента для регулирования вклада в точность опредления родителя. >0: наличие желательно, 0: безразлично (компонент может быть опущен без потери точности), <0: наличие нежелательно.

    optional = False  # Если True, компонент считается опциональным и может отсутствовать. Если False, то его наличие обязательно требуется для существования родительского элемента.

    precision_treshold = 0.3  # [0, 1] порог допустимой точности, ниже которого компонент считается не найденным.

    # @property
    # def max_score(self) -> float:
    #     return self.weight * max(0, self.importance)

    def dependencies(self, recursive=False) -> list['GrammarElement']:
        if not recursive:
            return self.element

        return [self.element, *self.element.dependencies(recursive=True)]

    # constraints_with_full_names: list[SpatialConstraint] = None
    
    @property
    def global_constraints(self) -> list[SpatialConstraint]:
        """ "Глобальные" ограничения — запись координат преобразована из сокращённой формы в полную:
        'x' или 'this_x' → '<self.name>_x';
        '_x' или 'parent_x' → 'element_x' (координата родителя),
        и т.п. """
        if not self._cache.constraints_with_full_names:
            self._cache.constraints_with_full_names = [
                ex.clone().replace_components({
                    'this': self.name,
                    'parent': 'element',
                })
                for ex in self.constraints
            ]
        return self._cache.constraints_with_full_names
        
    def constraints_conjunction(self) -> SpatialConstraint:
        if self._cache.constraints_conjunction is None:
            self._cache.constraints_conjunction = reduce(and_, self.global_constraints)
        return self._cache.constraints_conjunction
        
    def checks_components(self) -> set[str]:
        """ Find which components are checked within constraints.
        This method usually returns 'element' as parent, and `self.name` as well. """
        if self._cache.components_in_constraints is None:
            self._cache.components_in_constraints = frozenset(self.constraints_conjunction().referenced_components())
        return self._cache.components_in_constraints
        
    def checks_other_components(self) -> set[str]:
        """ Find which other components are checked within constraints.
        This method omits 'element' as parent, and self. """
        return self.checks_components() - {'element', self.name}
        





@dataclass
class GrammarElement:
    """Элемент грамматики: """

    name: str  # имя узла грамматики (определяет тип содержимого)
    root: bool = False  # whether this element is the grammars's root.
    precision_treshold = 0.3  # [0, 1] порог допустимой точности, ниже которого элемент считается не найденным.

    def __hash__(self) -> int:
        return hash(self.name)

    # parent: Optional['GrammarElement'] = None # родительский узел грамматики
    # components: dict[str, 'PatternComponent']

    extends: list[str | 'GrammarElement'] = ()  # Линейная иерархия переопределения базовых узлов. Перечисленные здесь элементы могут заменяться на текущий элемент.

    def dependencies(self, recursive=False) -> list['GrammarElement']:
        """ GrammarElement must be known before this one can be matched. """
        raise NotImplementedError(type(self))

    # @property
    # def is_root(self) -> bool:
    #     return self.parent is None

    def max_score(self) -> float:
        raise NotImplementedError(type(self))

    def can_be_extended_by(self, child_element: 'GrammarElement') -> bool:
        return GRAMMAR.can_extend(self, child_element)



@dataclass
class Terminal(GrammarElement):
    """просто ячейка"""
    cell_type_name: str
    _cell_type: CellType = None

    @property
    def cell_type(self) -> CellType:
        if not self._cell_type:
            self._cell_type = GRAMMAR.cell_types[self.cell_type_name]
        return self._cell_type

    def dependencies(self, recursive=False) -> list['GrammarElement']:
        return ()

    def max_score(self) -> float:
        return 1
    
    def get_matcher(self, grammar_macher):
        from grammar2d_matching import TerminalMatcher
        return TerminalMatcher(self, grammar_macher)



class NonTerminal(GrammarElement, WithCache):
    """Структура или Коллекция"""
    components: list[PatternComponent]

    # dependencies: list[GrammarElement] = None
    def dependencies(self, recursive=False) -> list[GrammarElement]:
        if not self._cache.dependencies:
            dependency_set = set()
            for comp in self.components:
                dependency_set |= comp.dependencies(recursive)
            # check circular dependencies
            assert self not in dependency_set, 'Grammar element `{self.name}` has circular dependency on itself (via component `{comp.name}`) !'
            self._cache.dependencies = list(sorted(dependency_set))
        return self._cache.dependencies

    # component_by_name: dict[str, GrammarElement] = None
    @property
    def component_by_name(self, name: str) -> GrammarElement | None:
        if not self._cache.component_by_name:
            self._cache.component_by_name = {
                comp.name: comp
                for comp in self.components
            }
        return self._cache.component_by_name.get(name)

    def max_score(self) -> float:
        """ precision = score / max_score """
        return sum(comp.weight for comp in self.components if comp.weight > 0)
    ...
    
    def get_matcher(self, grammar_macher):
        from grammar2d_matching import NonTerminalMatcher
        return NonTerminalMatcher(self, grammar_macher)



@dataclass
class Grammar(WithCache):
    """Грамматика описывает весь документ, начиная от корня"""
    
    cell_types: dict[str, CellType]
    elements: dict[str, GrammarElement]
    root_name: str = None
    
    def register_element(self, elem: GrammarElement):
        assert elem.name, f"Cannot register element without name: {elem}"
        self.elements[elem.name] = elem

        # check root
        if elem.root:
            if self.root_name:
                assert self.root_name == elem.name, f"Grammar element `{elem.name}` is declared as root, but grammar itself declares `{self.root_name}` as root."
            else:
                self.root_name = elem.name
            self._root = elem
        elif self.root_name == elem.name:
            elem.root = True  # update element
            self._root = elem


    _root: GrammarElement = None
    @property
    def root(self) -> GrammarElement:
        """корень грамматики"""
        if not self._root:
            assert self.root_name, '`root` of grammar not specified!'
            self._root = self.elements[self.root_name]
        return self._root

    def __getitem__(self, name_or_el: str | GrammarElement):
        """Short syntax to access element of the grammar"""
        if isinstance(name_or_el, GrammarElement):
            assert name_or_el.name in self.elements, name_or_el
            elem = name_or_el
        else:
            elem = self.elements[name_or_el]
        return elem
    
    def get_effective_cell_types(self) -> dict[str, CellType]:
        """ Get cell types only used for matching, i.e. omit unused ones. """
        effective_cell_types = {}
        for elem in self.elements.values():
            if isinstance(elem, Terminal):
                requested_cell_type = elem.cell_type
                assert requested_cell_type in self.cell_types, f"Used undeclared cell type {requested_cell_type} for element {elem.name}."
                effective_cell_types[requested_cell_type] = self.cell_types[requested_cell_type]
        return effective_cell_types

    # dependency_waves: list[set[GrammarElement]] = None

    @property
    def dependency_waves(self) -> list[set[GrammarElement]]:
        """get list of sets `_dependency_waves`"""
        if not self._cache.dependency_waves:
            assert self.elements, 'Cannot process empty grammar!'
            
            # build dependency "tree" by tracing stages of matching process.
            waves = []
            unmatched_elements = set(self.elements.values())
            matched_elements = set()

            while unmatched_elements:
                current_wave: set[GrammarElement] = set()
                for elem in list(unmatched_elements):  # iterate over a copy
                    elem_deps = set(elem.dependencies(recursive=False))
                    if not(elem_deps - matched_elements):
                        # this one can be matched now.
                        current_wave.add(elem)
                
                if not current_wave:
                    raise ValueError(f"Grammar defined improperly: some elements cannot be matched due to circular dependencies ({unmatched_elements}). Elements could be matched correctly: {matched_elements}.")

                waves.append(current_wave)
                unmatched_elements -= current_wave
                matched_elements |= current_wave
            
            assert waves, 'Cannot infer any matching stages for the grammar!'
            
            # check root
            if (n := len(waves[-1])) > 1:
                print(f'WARNING: grammar defines several ({n}) top-level elements!')
                if not self.root_name:
                    raise ValueError(f'Grammar root is not specified and cannot be inferred automatically. Suggested options: {waves[-1]}.')
            elif not self.root_name:
                top_elem = waves[-1][0]
                self.root_name = top_elem.name
                self._root = top_elem
                print('INFO: Grammar root inferred automatically:', self.root_name)
            elif self.root not in waves[-1]:
                print('WARNING: `root` of grammar is not the top-level element!')
            
            self._cache.dependency_waves = waves
            
        return self._cache.dependency_waves

    # can_be_extended_by: dict[GrammarElement, list[GrammarElement]] = None

    @property
    def extension_map(self) -> dict[GrammarElement, list[GrammarElement]]:
        """get dict `can_be_extended_by`"""
        if not self._cache.can_be_extended_by:
            # build map
            can_be_extended_by = defaultdict(list)

            for elem in self.elements.values():
                for base in elem.extends:
                    # direct extension
                    bases = can_be_extended_by[self[base]]
                    if elem not in bases:
                        bases.append(elem)

                    # indirect extension
                    for superbase in base.extends:
                        superbases = can_be_extended_by[self[superbase]]
                        if elem not in superbases:
                            superbases.append(elem)
                        # add superbase to elem's bases for ршрук completeness
                        if superbase not in elem.extends:
                            elem.extends.append(superbase)


                    # Note: infinite propagation is not implemented, only 2 levels. Please declare all bases in Element's specification, do not rely on automatic inference.

            self._cache.can_be_extended_by = dict(can_be_extended_by)  # convert to ordinary dict
        return self._cache.can_be_extended_by

    def can_extend(self, base_element: str | GrammarElement, extension_element: str | GrammarElement) -> bool:
        children = self.extension_map.get(self[base_element], None)
        return children and extension_element in children




