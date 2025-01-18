from dataclasses import dataclass

from grammar2d.Pattern2d import Pattern2d
from grammar2d.PatternComponent import PatternComponent


class NonTerminal(Pattern2d):
    """Структура или Коллекция"""

    @classmethod
    def get_kind(cls):


    ...

    def get_matcher(self, grammar_macher):
        raise NotImplementedError(type(self))

