from collections import defaultdict
from dataclasses import dataclass

from grammar2d.GrammarElement import GrammarElement
from grammar2d.NonTerminal import NonTerminal
from grammar2d.Terminal import Terminal
from string_matching import CellType
from utils import WithCache


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
                    if not (elem_deps - matched_elements):
                        # this one can be matched now.
                        current_wave.add(elem)

                if not current_wave:
                    raise ValueError(
                        f"Grammar defined improperly: some elements cannot be matched due to circular dependencies ({unmatched_elements}). Elements could be matched correctly: {matched_elements}.")

                waves.append(current_wave)
                unmatched_elements -= current_wave
                matched_elements |= current_wave

            assert waves, 'Cannot infer any matching stages for the grammar!'

            # check root
            if (n := len(waves[-1])) > 1:
                print(f'WARNING: grammar defines several ({n}) top-level elements!')
                if not self.root_name:
                    raise ValueError(
                        f'Grammar root is not specified and cannot be inferred automatically. Suggested options: {waves[-1]}.')
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
