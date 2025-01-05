from collections import defaultdict
from dataclasses import dataclass

from geom2d import Point
from grammar2d import Grammar, GrammarElement
from grammar2d.Match2d import Match2d
from grid import GridView, CellView, Grid
from string_matching import CellClassifier
from utils import global_var


@dataclass
class GrammarMatcher:
    grammar: Grammar

    _grid_view: GridView = None
    _matches_by_position: dict[Point, list[Match2d]] = None
    _matches_by_element: dict[GrammarElement, list[Match2d]] = None
    type_to_cells: dict[str, list[CellView]] = None

    def run_match(self, grid: Grid) -> Match2d:
        self._grid_view = grid.get_view()
        self._recognise_all_cells_content()

        with global_var(GRAMMAR=self):
            ...

    @property
    def matches_by_position(self) -> dict[Point, list[Match2d]]:
        if not self._matches_by_position:
            self._matches_by_position = defaultdict(list)
        return self._matches_by_position

    @property
    def matches_by_element(self) -> dict[GrammarElement, list[Match2d]]:
        if not self._matches_by_element:
            self._matches_by_element = defaultdict(list)
        return self._matches_by_element

    def register_match(self, match: Match2d):
        self.matches_by_position[match.box.position].append(match)
        self.matches_by_element[match.element].append(match)

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

    def _roll_matching_waves(self):
        """ Find matches of all grammar elements per all matching waves defined by grammar,
            from terminals to the root. """
        for wave in self.grammar.dependency_waves():
            if self.grammar.root in wave:
                _res_ = self._find_matches_of_element(self.grammar.root)
            else:
                for elem in wave:
                    self._find_matches_of_element(elem)
            ...

    def _find_matches_of_element(self, element: GrammarElement):
        """Try finding matches of element on all grid space"""
        ...
        # for wave in self.grammar.dependency_waves():
        # if
