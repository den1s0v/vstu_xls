from collections import defaultdict
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path

import yaml
from loguru import logger

import vstuxls.grammar2d.PatternComponent as pc
from vstuxls.grammar2d.Pattern2d import Pattern2d, read_pattern
from vstuxls.grammar2d.Terminal import Terminal
from vstuxls.string_matching import CellType, read_cell_types
from vstuxls.utils import WithCache, find_file_under_path

TARGET_MODES = ('root', 'all')


@dataclass
class Grammar(WithCache):
    """Грамматика описывает весь документ, начиная от корня"""

    cell_types: dict[str, CellType]
    # can be initialized with list but normally is dict
    patterns: dict[str, Pattern2d] | list[Pattern2d]
    root_name: str | None = None

    # root: оптимизировать процесс для корневого, all: искать все подряд
    target_mode: str = 'root'  # или 'all'

    _root: Pattern2d  | None = None

    def __post_init__(self):
        if self.target_mode not in TARGET_MODES:
            raise ValueError(f'Grammar\'s `target_mode` must be one of `{TARGET_MODES
            }`, but got: `{self.target_mode}`.')

        # init patterns
        pattern_list = self.patterns if isinstance(self.patterns, list) else self.patterns.values()
        self.patterns = {}  # dict
        for pt in pattern_list:
            self._register_pattern(pt)

    def _register_pattern(self, pattern: Pattern2d):
        assert pattern.name, f"Cannot register pattern without name: {pattern}"
        self.patterns[pattern.name] = pattern
        pattern.set_grammar(self)

        # check root
        if pattern.root:
            if self.root_name:
                assert self.root_name == pattern.name, \
                    f"Grammar pattern `{pattern.name}` is declared as root, but grammar itself declares `{self.root_name}` as root."
            else:
                self.root_name = pattern.name
            self._root = pattern
        elif self.root_name == pattern.name:
            pattern.root = True  # update pattern
            self._root = pattern

        # recurse into pattern's components to register their components as well.
        if hasattr(pattern, 'components'):
            component: pc.PatternComponent
            # for all declared patterns, if not registered before.
            for component in pattern.components:
                if (p := component._subpattern) and p.name not in self.patterns:
                    self._register_pattern(p)

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

    def __str__(self):
        return f'Grammar[{len(self.cell_types)} cell types, {len(self.patterns)} patterns]'

    __repr__ = __str__

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

    # @property
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
                        "Grammar defined improperly: some patterns cannot be matched due to circular dependencies:\n - "
                        f"{'\n - '.join(sorted(map(str,
                            unmatched_patterns)))}. \n"
                        "Elements could be matched correctly: \n - "
                        f"{'\n - '.join(sorted(map(str, matched_patterns)))}.")

                waves.append(current_wave)
                unmatched_patterns -= current_wave
                matched_patterns |= current_wave

            assert waves, 'Cannot infer any matching stages for the grammar!'

            if self.target_mode == 'root':
                # check root
                if (n := len(waves[-1])) > 1:
                    logger.warning(f'WARNING: grammar defines several ({n}) top-level patterns!')
                    if not self.root_name:
                        raise ValueError(
                            f'Grammar root is not specified and cannot be inferred automatically. Suggested options: {waves[-1]}.')
                elif not self.root_name:
                    top_elem = waves[-1][0]
                    self.root_name = top_elem.name
                    self._root = top_elem
                    logger.info(f'INFO: Grammar root inferred automatically: {self.root_name}')
                elif self.root not in waves[-1]:
                    logger.warning('WARNING: `root` of grammar is not the top-level pattern!')

                # Optimize waves (drop unnecessary patterns)
                ... # TODO

            self._cache.dependency_waves = waves

        return self._cache.dependency_waves

    # can_be_extended_by: dict[Pattern2d, list[Pattern2d]] = None

    @property
    def extension_map(self) -> dict[Pattern2d, list[Pattern2d]]:
        """ Base Pattern to all its redefinitions (get dict `can_be_extended_by)`"""
        if not self._cache.can_be_extended_by:
            # build map
            can_be_extended_by = defaultdict(list)

            for pattern in self.patterns.values():
                for base in pattern.extends_patterns(recursive=True):
                    # reverse extension
                    bases = can_be_extended_by[base]
                    if pattern not in bases:
                        bases.append(pattern)
                        # can_be_extended_by[base] = bases

            self._cache.can_be_extended_by = dict(can_be_extended_by)  # convert to ordinary dict
        return self._cache.can_be_extended_by

    def can_extend(self, base_pattern: str | Pattern2d, extension_pattern: str | Pattern2d) -> bool:
        """ Check if a base pattern be extended by another pattern considered as a "child". """
        children = self.extension_map.get(self[base_pattern], None)
        return children and extension_pattern in children


def read_grammar_data(
        config_file: 'str | Path' = '../cnf/grammar_root.yml',
        data: dict = None,
        require_cell_types: bool = True,
  ) -> tuple[dict[str, CellType], list[Pattern2d]]:
    if not data:
        assert config_file
        with open(config_file, encoding='utf-8') as f:
            data = yaml.safe_load(f)

    assert isinstance(data, dict), data

    cell_types = read_cell_types(data=data, raise_on_error=require_cell_types)

    parsed_patterns = []

    if 'patterns' in data:
        # get & parse patterns.
        patterns_dict = data['patterns']
        assert isinstance(patterns_dict, dict), patterns_dict

        for name, fields in patterns_dict.items():
            fields['name'] = name
            p = read_pattern(fields)
            if p:
                parsed_patterns.append(p)

    if 'include_grammars' in data:
        # Add cell_types & patterns from referenced grammar (with overwrite for cell_types)
        for sub_path in data['include_grammars']:
            # TODO add guard: ignore grammars already loaded to avoid potential duplication & uncontrolled recursion.
            sub_cell_types, sub_parsed_patterns = read_grammar_data(config_file=find_file_under_path(sub_path), require_cell_types=False)
            cell_types |= sub_cell_types or {}
            parsed_patterns += sub_parsed_patterns or ()

    if not parsed_patterns:
        raise ValueError(
            f'Format error: `patterns` dict and/or `include_grammars` list are expected in given file: `{config_file}`.')

    return cell_types, parsed_patterns


def read_grammar(
        config_file: str | Path = Path(str(files('vstuxls').joinpath('cnf', 'grammar_root.yml'))),
        data: dict | None = None,
        require_cell_types: bool = True,
  ) -> Grammar | None:

    cell_types, parsed_patterns = read_grammar_data(config_file, data=data, require_cell_types=require_cell_types)

    return Grammar(cell_types, parsed_patterns)
