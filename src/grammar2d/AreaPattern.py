from dataclasses import dataclass, field
from typing import override

from geom2d import open_range
import grammar2d.Match2d as m2
from grammar2d.NonTerminal import NonTerminal
from grammar2d.Pattern2d import Pattern2d, PatternRegistry
from grammar2d.PatternComponent import PatternComponent


@dataclass(kw_only=True, repr=True)
class AreaPattern(NonTerminal):
    """Структура из элементов разного типа

    """
    components: list[PatternComponent]

    @classmethod
    @override
    def get_kind(cls):
        return "area"  # ???

    # dependencies: list[Pattern2d] = None
    @override
    def dependencies(self, recursive=False) -> list[Pattern2d]:
        if not self._cache.dependencies:
            dependency_set = set()
            for comp in self.components:
                dependency_set |= comp.dependencies(recursive)
            # check circular dependencies
            assert self not in dependency_set, \
                'Grammar pattern `{self.name}` has circular dependency on itself (via component `{comp.name}`) !'
            self._cache.dependencies = list(sorted(dependency_set))
        return self._cache.dependencies

    # component_by_name: dict[str, PatternComponent] = None
    @property
    def component_by_name(self) -> dict[str, PatternComponent] | None:
        if not self._cache.component_by_name:
            self._cache.component_by_name = {
                comp.name: comp
                for comp in self.components
            }
        return self._cache.component_by_name

    @override
    def max_score(self) -> float:
        """ precision = score / max_score """
        return sum(comp.weight for comp in self.components if comp.weight > 0)

    def score_of_match(self, match: m2.Match2d) -> float:
        """ Calc score for given match:
            weighted sum of all given components
            (?) if any is absent but required?
        """
        return sum(
                comp_m.precision * self.component_by_name[name].weight
                for name, comp_m in match.component2match.items()
        )

    ...

    # def get_matcher(self, grammar_macher):
    #     from grammar2d.AreaPatternMatcher import AreaPatternMatcher
    #     return AreaPatternMatcher(self, grammar_macher)


PatternRegistry.register(AreaPattern)
