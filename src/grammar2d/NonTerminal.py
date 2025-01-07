from dataclasses import dataclass

from grammar2d.Pattern2d import Pattern2d, PatternRegistry
from grammar2d.PatternComponent import PatternComponent


@dataclass(kw_only=True)
class NonTerminal(Pattern2d):
    """Структура или Коллекция"""
    components: list[PatternComponent]

    @classmethod
    def get_kind(cls):
        return "area"  # ???

    # dependencies: list[GrammarElement] = None
    def dependencies(self, recursive=False) -> list[Pattern2d]:
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
    def component_by_name(self) -> dict[str, PatternComponent] | None:
        if not self._cache.component_by_name:
            self._cache.component_by_name = {
                comp.name: comp
                for comp in self.components
            }
        return self._cache.component_by_name

    def max_score(self) -> float:
        """ precision = score / max_score """
        return sum(comp.weight for comp in self.components if comp.weight > 0)

    ...

    def get_matcher(self, grammar_macher):
        from grammar2d.NonTerminalMatcher import NonTerminalMatcher
        return NonTerminalMatcher(self, grammar_macher)


PatternRegistry.register(NonTerminal)
