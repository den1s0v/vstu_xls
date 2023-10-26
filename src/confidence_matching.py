# confidence_matching.py

"""
При классификации строк может понадобиться
    определять степень уверенности в том,
    насколько данная строка подходит к
    заданному классу,
    то есть определять степень уверенности
    (в точности классификации).

     Для этого каждому классу сопоставляется
     несколько регулярных выражений,
     каждое из которых разработано для своего
     уровня уверенности,
     обычно от большего к меньшему -- от 1 до 0.1
     (уровень уверенности, равный нулю, не имеет смысла).
"""
import re
from dataclasses import dataclass

from adict import adict


def decode_re_spaces(re_spaces: str) -> str:
    r"""
    Перечень замен:
    ' '  -> \\s* -- Один пробел становится "опциональным пробелом",
    "  " -> \\s+ -- Два пробела становятся "минимум одним пробелом",
    "   " -> " " -- Три пробела становятся просто одним пробелом.
    """
    return (re_spaces
            .replace("   ", r'\s')
            .replace("  ", r'\s+')
            .replace(" ", r'\s*'))


class ConfidentPattern():
    """ Паттерн для сопоставления строк со степенью уверенности.
        Синтаксисы паттерна:
         - 're' (regexp)
         - 're-spaces' (regexp in simplified notation @see)
         - 'plain' (plain text)
    """
    pattern: str = None
    confidence: float = 0.5
    pattern_syntax: str = 're'  # plain / re (regexp) / re-spaces
    pattern_flags: int = 0
    pattern_fields: tuple = ()
    content_class: 'ContentClass' = None

    def __init__(self, *args, **kwargs):
        """Valid calls:
        ConfidentPattern(pattern='abc+', confidence=0.9);
        ConfidentPattern('abc+', confidence=0.9);
        ConfidentPattern('abc+', 0.9);
        ConfidentPattern('a b c', 0.9, pattern_syntax='re-spaces');
        ConfidentPattern('a b c', 0.9, 're-spaces');

        # dict-based:
        ConfidentPattern({'pattern': 'abc+', 'confidence': 0.9});
        ConfidentPattern({'pattern': 'abc+', 'confidence': 0.9, 'pattern_syntax': 're-spaces'});
        """
        if len(args) == 1 and isinstance(args[0], dict):
            kwargs = args[0]
            args = ()
        elif len(args) > 0:
            # integrate positional arguments
            for key, val in zip(ConfidentPattern.__annotations__.keys(), args):
                if key not in kwargs:
                    kwargs[key] = val

        # read defaults from annotations
        kw = {k: getattr(ConfidentPattern, k) for k in ConfidentPattern.__annotations__}
        kw.update(kwargs)
        assert kw['pattern'], 'Please specify pattern for ConfidentPattern!'
        # set all attributes
        for k, v in kw.items():
            setattr(self, k, v)

        if self.pattern_syntax != 'plain':
            self._compiled_re = None
        if self.pattern_syntax == 're-spaces':
            self.pattern = decode_re_spaces(self.pattern)

    def match(self, string: str):
        if self.pattern_syntax == 'plain':
            return string == self.pattern

        if not self._compiled_re:
            self._compiled_re = re.compile(self.pattern, self.pattern_flags)

        m = self._compiled_re.match(string)
        if m:
            return Match(m, self)
        return None


@dataclass
class Match:
    match: re.Match
    pattern: ConfidentPattern


class ContentClass:
    """ Класс (разновидность) контента,
        характеризующийся собственным набором паттернов """

    def __init__(self, name='a', patterns=None):
        self.name = name
        self.patterns = self.prepare_patterns(patterns)

    @classmethod
    def prepare_patterns(cls, patterns):
        assert patterns, 'at least one pattern is required'
        if isinstance(patterns, ConfidentPattern):
            return [patterns]
        if isinstance(patterns, str):
            return [ConfidentPattern(patterns)]

        ps = [
            p if isinstance(patterns, ConfidentPattern) else ConfidentPattern(p)
            for p in patterns
        ]
        ps.sort(key=lambda p: p.confidence, reverse=True)
        return ps
