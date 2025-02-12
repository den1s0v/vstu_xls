from dataclasses import dataclass
from typing import override

from grammar2d.Pattern2d import Pattern2d, PatternRegistry
from grammar2d.PatternComponent import PatternComponent


# @dataclass(kw_only=True)
@PatternRegistry.register
class NonTerminal(Pattern2d):
    """Структура или Коллекция"""

    @classmethod
    @override
    def get_kind(cls):
        return "general"  # ???


    ...

    def get_matcher(self, grammar_macher):
        raise NotImplementedError(type(self))

