from dataclasses import dataclass
from typing import override

from grammar2d.Pattern2d import Pattern2d, PatternRegistry
from grammar2d.PatternComponent import PatternComponent


# @dataclass(kw_only=True)
@PatternRegistry.register
class NonTerminal(Pattern2d):
    """Структура или Коллекция.

    Этот тип паттерна не может быть обнаружен в данных непосредственно,
    но может быть использован в грамматике с `kind=general`,
    чтобы служить обобщением для других паттернов, которые указывают этот в своём списке `extends`.
    Таким образом реализуется принцип полиморфизма и аналог множественного наследования.
    """

    @classmethod
    @override
    def get_kind(cls):
        """ ...Thoughts to give it a more sensible name:
          - generalization;
          - base;
          - abstract;
          - extension_point;
          - ...?
         """
        return "general"  # ???

    # def dependencies(self, recursive=False) -> list[Pattern2d]:
    #     return super().dependencies(recursive)

    # def max_score(self) -> float:
    #     """ precision = score / max_score """
    #     raise NotImplementedError(type(self))

    ...

    def get_matcher(self, grammar_matcher):
        # raise NotImplementedError(type(self))
        from grammar2d.NonTerminalMatcher import NonTerminalMatcher
        return NonTerminalMatcher(self, grammar_matcher)
