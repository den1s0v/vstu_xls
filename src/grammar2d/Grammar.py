from collections import defaultdict
from dataclasses import dataclass

import yaml

from grammar2d.Pattern2d import Pattern2d, read_pattern
from grammar2d.NonTerminal import NonTerminal
from grammar2d.Terminal import Terminal
from string_matching import CellType, read_cell_types
from utils import WithCache


# @dataclass
class Grammar(WithCache):
    """Грамматика описывает весь документ, начиная от корня"""

    cell_types: dict[str, CellType]
    patterns: dict[str, Pattern2d]
    root_name: str = None

    def __init__(self, cell_types: dict[str, CellType], patterns: list[Pattern2d]):
        self.cell_types = cell_types

        self.patterns = {}
        for pt in patterns:
            self.register_pattern(pt)

    def register_pattern(self, pattern: Pattern2d):
        assert pattern.name, f"Cannot register pattern without name: {pattern}"
        self.patterns[pattern.name] = pattern

        # check root
        if pattern.root:
            if self.root_name:
                assert self.root_name == pattern.name,\
                    f"Grammar pattern `{pattern.name}` is declared as root, but grammar itself declares `{self.root_name}` as root."
            else:
                self.root_name = pattern.name
            self._root = pattern
        elif self.root_name == pattern.name:
            pattern.root = True  # update pattern
            self._root = pattern

    _root: Pattern2d = None

    @property
    def root(self) -> Pattern2d:
        """корень грамматики"""
        if not self._root:
            assert self.root_name, '`root` of grammar not specified!'
            self._root = self.patterns[self.root_name]
        return self._root

    def __getitem__(self, name_or_el: str | Pattern2d):
        """Short syntax to access pattern of the grammar"""
        if isinstance(name_or_el, Pattern2d):
            assert name_or_el.name in self.patterns, name_or_el
            pattern = name_or_el
        else:
            pattern = self.patterns[name_or_el]
        return pattern

    def get_effective_cell_types(self) -> dict[str, CellType]:
        """ Get cell types only used for matching, i.e. omit unused ones. """
        effective_cell_types = {}
        for pattern in self.patterns.values():
            if isinstance(pattern, Terminal):
                requested_cell_type = pattern.cell_type.name
                assert requested_cell_type in self.cell_types, \
                    f"Used undeclared cell type {requested_cell_type} for pattern {pattern.name}."
                effective_cell_types[requested_cell_type] = self.cell_types[requested_cell_type]
        return effective_cell_types

    # dependency_waves: list[set[Pattern2d]] = None

    @property
    def dependency_waves(self) -> list[set[Pattern2d]]:
        """get list of sets `_dependency_waves`"""
        if not self._cache.dependency_waves:
            assert self.patterns, 'Cannot process empty grammar!'

            # build dependency "tree" by tracing stages of matching process.
            waves = []
            unmatched_patterns = set(self.patterns.values())
            matched_patterns = set()

            while unmatched_patterns:
                current_wave: set[Pattern2d] = set()
                for pattern in list(unmatched_patterns):  # iterate over a copy
                    elem_deps = set(pattern.dependencies(recursive=False))
                    if not (elem_deps - matched_patterns):
                        # this one can be matched now.
                        current_wave.add(pattern)

                if not current_wave:
                    raise ValueError(
                        f"Grammar defined improperly: some patterns cannot be matched due to circular dependencies ({unmatched_patterns}). Elements could be matched correctly: {matched_patterns}.")

                waves.append(current_wave)
                unmatched_patterns -= current_wave
                matched_patterns |= current_wave

            assert waves, 'Cannot infer any matching stages for the grammar!'

            # check root
            if (n := len(waves[-1])) > 1:
                print(f'WARNING: grammar defines several ({n}) top-level patterns!')
                if not self.root_name:
                    raise ValueError(
                        f'Grammar root is not specified and cannot be inferred automatically. Suggested options: {waves[-1]}.')
            elif not self.root_name:
                top_elem = waves[-1][0]
                self.root_name = top_elem.name
                self._root = top_elem
                print('INFO: Grammar root inferred automatically:', self.root_name)
            elif self.root not in waves[-1]:
                print('WARNING: `root` of grammar is not the top-level pattern!')

            self._cache.dependency_waves = waves

        return self._cache.dependency_waves

    # can_be_extended_by: dict[Pattern2d, list[Pattern2d]] = None

    @property
    def extension_map(self) -> dict[Pattern2d, list[Pattern2d]]:
        """get dict `can_be_extended_by`"""
        if not self._cache.can_be_extended_by:
            # build map
            can_be_extended_by = defaultdict(list)

            for pattern in self.patterns.values():
                for base in pattern.extends:
                    # direct extension
                    bases = can_be_extended_by[self[base]]
                    if pattern not in bases:
                        bases.append(pattern)

                    # indirect extension
                    for superbase in base.extends:
                        superbases = can_be_extended_by[self[superbase]]
                        if pattern not in superbases:
                            superbases.append(pattern)
                        # add superbase to pattern's bases for ршрук completeness
                        if superbase not in pattern.extends:
                            pattern.extends.append(superbase)

                    # Note: infinite propagation is not implemented, only 2 levels. Please declare all bases in Element's specification, do not rely on automatic inference.

            self._cache.can_be_extended_by = dict(can_be_extended_by)  # convert to ordinary dict
        return self._cache.can_be_extended_by

    def can_extend(self, base_pattern: str | Pattern2d, extension_pattern: str | Pattern2d) -> bool:
        children = self.extension_map.get(self[base_pattern], None)
        return children and extension_pattern in children
