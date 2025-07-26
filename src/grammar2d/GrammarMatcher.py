from collections import defaultdict
from dataclasses import dataclass

from loguru import logger

from geom2d import Point, Box
from grammar2d import Grammar, Pattern2d
from grammar2d.Match2d import Match2d
from grid import GridView, CellView, Grid
from string_matching import CellClassifier


@dataclass
class GrammarMatcher:
    grammar: Grammar

    # projection of processed grid
    _grid_view: GridView = None

    # matches starting at left top corner
    _matches_by_position: dict[Point, list[Match2d]] = None

    # matches related to pattern
    _matches_by_element: dict[Pattern2d, list[Match2d]] = None

    # scalar info about cells
    type_to_cells: dict[str, list[CellView]] = None

    def get_pattern_matches(self, pattern: Pattern2d, region: Box = None) -> list[Match2d]:
        """ Get all currently known matches of given pattern.
        If region specified, return only matches that are within the region. """
        occurrences = self.matches_by_element[pattern] or []

        if region:
            # filter by region
            occurrences = list(filter(
                lambda m: m.box in region,
                occurrences))
        return occurrences

    def run_match(self, grid: Grid) -> list[Match2d]:
        self.matches_by_element.clear()
        self._grid_view = grid.get_view()
        self._recognise_all_cells_content()
        self._roll_matching_waves()

        root = self.grammar.root
        # assert root in self._matches_by_element, set(self._matches_by_element.keys())
        root_matches = self._matches_by_element.get(root) or []
        return root_matches

    @property
    def matches_by_position(self) -> dict[Point, list[Match2d]]:
        if not self._matches_by_position:
            self._matches_by_position = defaultdict(list)
        return self._matches_by_position

    @property
    def matches_by_element(self) -> dict[Pattern2d, list[Match2d]]:
        if not self._matches_by_element:
            self._matches_by_element = defaultdict(list)
        return self._matches_by_element

    def register_match(self, match: Match2d, as_pattern: 'str|Pattern2d' = None, _seen_patterns: set = None):
        self.matches_by_position[match.box.position].append(match)
        self.matches_by_element[match.pattern].append(match)

        # add patterns extended by this too!
        # for base_pattern in self.grammar.extension_map.get(match.pattern) or ():
        for base_pattern in match.pattern.extends_patterns(recursive=True):
            self.matches_by_element[base_pattern].append(match)
            # ## print(f' + Registered match for {base_pattern} extended by {match.pattern}')

    def _recognise_all_cells_content(self, max_hypotheses_per_cell=5):

        ccl = CellClassifier(self.grammar.get_effective_cell_types().values())
        self.type_to_cells = defaultdict(list)

        for cw in self._grid_view.iterate_cells():
            match_list = ccl.match(cw.cell.content, max_hypotheses_per_cell)
            if match_list:
                for m in match_list:
                    # save to local cache
                    ct_name = m.pattern.content_class.name
                    self.type_to_cells[ct_name].append(cw)

            # save to cell_view's data
            data = cw.data  # reference to updatable dict
            # if 'cell_matches' not in data:
            #     data['cell_matches'] = dict()
            data['cell_matches'] = {
                m.pattern.content_class.name: m
                for m in match_list
            }

    def _roll_matching_waves(self, verbose=True):
        """ Find matches of all grammar elements per all matching waves defined by grammar,
            from terminals to the root. """
        for wave in self.grammar.dependency_waves():
            if verbose:
                logger.debug('WAVE:')
                logger.debug([p.name for p in wave])
            if self.grammar.root in wave:
                self._find_matches_of_pattern(self.grammar.root)
            else:
                for ptt in wave:
                    if ptt.independently_matchable():
                        self._find_matches_of_pattern(ptt)
            ...

    def _find_matches_of_pattern(self, pattern: Pattern2d):
        """Try finding matches of element on all grid space"""
        matcher = pattern.get_matcher(self)
        matches = matcher.find_all(match_limit=pattern.count_in_document.stop)

        # Check the quantity of matches
        if len(matches) not in pattern.count_in_document:
            logger.warning(f'Found {len(matches)} match(es) of pattern `{pattern.name
                }` but expected {pattern.count_in_document}.')

            if pattern.count_in_document.stop is not None and len(matches) > pattern.count_in_document.stop:
                limit = pattern.count_in_document.stop
                # Drop unexpected matches.
                matches = matches[:limit]
                logger.warning(f' ... limited result to {limit} match(es) of this pattern.')

        for m in matches or ():
            # register Match globally
            self.register_match(m)

        ###
        logger.debug('')
        logger.debug(f':: {len(matches)} matches of pattern `{pattern.name}` ↓')
        logger.debug([
            (m.get_content(), m.box)
            for m in matches
        ])
        # ...
