# grammar2d_matching.py


from collections import defaultdict
from dataclasses import dataclass
from functools import reduce
from operator import and_

from adict import adict
from constraints_2d import SpatialConstraint

from geom2d import Box, Point, VariBox
from grammar2d import Grammar, GrammarElement, NonTerminal, PatternComponent, Terminal
from grid import CellView, Grid, GridView




@dataclass()
class Match2d:
    element: GrammarElement 
    components: dict[str, 'Match2d'] = None
    precision = None
    box: Box = None
    data: dict = None
    
    def calc_precision(self) -> float:
        if self.precision is None:
            self.precision = sum(
                comp_m.precision * self.element.component_by_name[name].weight 
                for name, comp_m in self.components.items()
            ) / self.element.max_score()
        return self.precision

    def clone(self):
        """Make a shallow copy"""
        return Match2d(
            self.element,
            dict(self.components),
            self.precision,
            self.box,
            dict(self.data),
        )
        
    
    def filter_best_matches(matches: list['Match2d'], precision_ratio_cutoff = 0.9) -> list['Match2d']:
        """Leave best matches only (default precision_ratio_cutoff == 0.9, i.e. matches having precision within top 10% from the best of the list)"""
        if len(matches) > 1:
            # drop worst matches…
            top_precision = max(m.precision for m in matches)
            precision_treshold = top_precision * precision_ratio_cutoff
            # reassign filtered list
            matches = [m for m in matches if m.precision >= precision_treshold]
            
        return matches
        
    

@dataclass
class ElementMacher:
    element: GrammarElement
    grammar_macher: 'GrammarMacher'
    
    def match(self) -> list[Match2d]:
        pass
        # raise TypeError(f"Unknown element type: {type(self.element)}")
    

class TerminalMatcher(ElementMacher):
    element: Terminal
    def match(self) -> list[Match2d]:
        type_name = self.element.cell_type.name
        type_name = self.element.cell_type.name
        matches = []
        if type_name in self.grammar_macher._type_to_cells:
            for cw in self.grammar_macher._type_to_cells[type_name]:
                precision = cw.data['cell_matches'][type_name].confidence
                if precision < self.element.precision_treshold:
                    continue
                
                m = Match2d(self.element, precision=precision, box=cw, data=cw.data['cell_matches'][type_name])
                self.grammar_macher.register_match(m)
                matches.append(m)
                
        return matches


class NonTerminalMatcher(ElementMacher):
    element: NonTerminal
    
    # _match_tree: list[list[Match2d]] = None
    
    def match(self, precision_ratio_cutoff = 0.9) -> list[Match2d]:
        # init empty match to be "forked" later
        m = Match2d(self.element, components = {}, data = adict(constraint = True))
        # self._match_tree = [[m]]
        match_tree = [[m]]
        
        for component in self.element.components:
            new_level = [
                m
                for partial_match in match_tree[-1]
                for m in self._incremental_match_component(partial_match, component)
            ]

            if not new_level and not component.optional:
                raise ValueError('CANNOT match component {component.name} for element {self.element.name}. Consider weaken restrictions on it or making it optional.')

            match_tree.append(new_level)
            # TODO: insert time report.

        # TODO?: conclude the best variant.
        
        final_matches = Match2d.filter_best_matches(match_tree[-1], precision_ratio_cutoff)
        
        for m in final_matches:
            self.grammar_macher.register_match(m)

        return final_matches
        
                
    def _incremental_match_component(self, partial_match: Match2d, component: PatternComponent, precision_ratio_cutoff = 0.9) -> list[Match2d]:
        """Chain matching with one more component"""
        precision_treshold = component.precision_treshold

        existing_component_positions = {name: m.box for name, m in partial_match.components.items()}
        
        existing_constraint: 'SpatialConstraint' = partial_match.data.constraint
        # add constraints from candidate.
        comp_constraints = component.get_constraints_as_for_parent()
        if comp_constraints:
            appended_constraint = reduce(and_, [*comp_constraints, existing_constraint])
        else:
            appended_constraint = existing_constraint ## (see below↓) .clone()  # it should be a new instance

        candidate_matches = self.grammar_macher.matches_by_element[component.element]
        new_matches = []
        for candidate_m in candidate_matches:
            if candidate_m.precision < precision_treshold:
                continue
            
            # evaluate combined inequality.
            appended_component_positions = {**existing_component_positions, component.name: candidate_m.box}
            
            if appended_constraint.eval_with_components(appended_component_positions) != False:
                # this combination makes sense so far.
            
                bound_constraint = appended_constraint.clone().inline_component_positions(appended_component_positions)
                
                m = Match2d(
                    self.element, 
                    components = {
                        **partial_match.components, 
                        component.name: candidate_m
                    }, 
                    data = adict(constraint = bound_constraint)
                )
                m.precision = m.calc_precision()
                
                new_matches.append(m)

            
        if not new_matches: 
            if component.optional:
                # allow further processing this match since we can skip the optional component.
                new_matches.append(partial_match)
            else:
                print('DEBUG: end of branch while matching component {component.name} for element {self.element.name}.')
                
        if len(new_matches) > 1:
            # drop worst matches…
            top_precision = max(m.precision for m in new_matches)
            precision_treshold = top_precision * precision_ratio_cutoff
            # reassign filtered list
            new_matches = [m for m in new_matches if m.precision >= precision_treshold]
            
        return Match2d.filter_best_matches(new_matches, precision_ratio_cutoff)
    ...


@dataclass
class GrammarMacher:
    
    grammar: Grammar
    
    _grid_view: GridView = None
    _matches_by_position: dict[Point, list[Match2d]] = None
    _matches_by_element: dict[GrammarElement, list[Match2d]] = None
    _type_to_cells: dict[str, list[CellView]] = None
    
    def run_match(self, grid: Grid) -> Match2d:
        self._grid_view = grid.getView()
        self._recognise_all_cells_content()

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
    
    def _recognise_all_cells_content(self):
        self._type_to_cells = defaultdict(list)
        for cw in self._grid_view.iterate_cells():
            for cell_type in self.grammar.get_effective_cell_types().values():
                m = cell_type.match(cw.cell.content)
                if m:
                    # save to local cache
                    self._type_to_cells[cell_type.name].append(cw)
                    # save to cell_view's data
                    data = cw.data  # reference to updatable dict
                    if 'cell_matches' not in data:
                        data['cell_matches'] = dict()
                    data['cell_matches'][cell_type.name] = m
    
    
    def _roll_matching_waves(self):
        """ Find matches of all grammar elements per all matching waves defined by grammar, from terminals to the root. """
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

