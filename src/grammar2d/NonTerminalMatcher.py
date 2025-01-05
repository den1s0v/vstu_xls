from operator import and_
from functools import reduce

from adict import adict

from constraints_2d import SpatialConstraint
from grammar2d import NonTerminal, PatternComponent
from grammar2d.PatternMatcher import PatternMatcher
from grammar2d.Match2d import Match2d, filter_best_matches


class NonTerminalMatcher(PatternMatcher):
    """
        ???
    """
    pattern: NonTerminal

    # _match_tree: list[list[Match2d]] = None

    def find_all(self, precision_ratio_cutoff=0.9) -> list[Match2d]:
        # init empty match to be "forked" later
        m = Match2d(self.pattern, component2match={}, data=adict(constraint=True))
        # self._match_tree = [[m]]
        match_tree = [[m]]

        for component in self.pattern.components:
            new_level = [
                m
                for partial_match in match_tree[-1]
                for m in self._incremental_match_component(partial_match, component)
            ]

            if not new_level and not component.optional:
                raise ValueError(
                    'CANNOT match component {component.name} for element {self.pattern.name}. Consider weaken restrictions on it or making it optional.')

            match_tree.append(new_level)
            # TODO: insert time report.

        # TODO?: conclude the best variant.

        final_matches = filter_best_matches(precision_ratio_cutoff)

        for m in final_matches:
            self.grammar_matcher.register_match(m)

        return final_matches

    def _incremental_match_component(self, partial_match: Match2d, component: PatternComponent,
                                     precision_ratio_cutoff=0.9) -> list[Match2d]:
        """Chain matching with one more component"""
        precision_treshold = component.precision_threshold

        existing_component_positions = {name: m.box for name, m in partial_match.component2match.items()}

        existing_constraint: 'SpatialConstraint' = partial_match.data.constraint
        # add constraints from candidate.
        comp_constraints = component.global_constraints
        if comp_constraints:
            appended_constraint = reduce(and_, [*comp_constraints, existing_constraint])
        else:
            appended_constraint = existing_constraint  ## (see below↓) .clone()  # it should be a new instance

        candidate_matches = self.grammar_matcher.matches_by_element[component.subpattern]
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
                    self.pattern,
                    component2match={
                        **partial_match.component2match,
                        component.name: candidate_m
                    },
                    data=adict(constraint=bound_constraint)
                )
                m.precision = m.calc_precision()

                new_matches.append(m)

        if not new_matches:
            if component.optional:
                # allow further processing this match since we can skip the optional component.
                new_matches.append(partial_match)
            else:
                print('DEBUG: end of branch while matching component {component.name} for element {self.pattern.name}.')

        if len(new_matches) > 1:
            # drop worst matches…
            top_precision = max(m.precision for m in new_matches)
            precision_treshold = top_precision * precision_ratio_cutoff
            # reassign filtered list
            new_matches = [m for m in new_matches if m.precision >= precision_treshold]

        return filter_best_matches(precision_ratio_cutoff)

    ...
