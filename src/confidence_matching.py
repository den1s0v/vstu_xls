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
from typing import List, Dict

import yaml

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


def re_flags_to_int(re_flags: str = '') -> int:
    """Get int union of flags for re.* constants:
     I M S X - IGNORECASE MULTILINE DOTALL VERBOSE"""
    int_flags = 0
    re_flags = re_flags.upper()
    if 'I' in re_flags:
        int_flags |= re.I
    if 'M' in re_flags:
        int_flags |= re.M
    if 'S' in re_flags:
        int_flags |= re.S
    if 'X' in re_flags:
        int_flags |= re.X
    return int_flags


class ConfidentPattern():
    """ Паттерн для сопоставления строк со степенью уверенности.
        Синтаксисы паттерна (pattern_syntax):
         - 're' (regexp)
         - 're-spaces' (regexp in simplified notation @see)
         - 'plain' (plain text)

        `pattern_fields` используется,
        если паттерн содержит группы захвата (запоминающие скобки),
        чтобы указать имена групп захвата (в порядке их появления).
    """
    pattern: str = None
    confidence: float = 0.5
    pattern_syntax: str = 're'  # plain / re (regexp) / re-spaces
    pattern_flags: int | str = 0
    pattern_fields: tuple = ()
    content_class: 'CellType' = None

    def __init__(self, *args, **kwargs):
        """Valid calls:
        ConfidentPattern(pattern='abc+', confidence=0.9);
        ConfidentPattern('abc+', confidence=0.9);
        ConfidentPattern('abc+', 0.9, pattern_flags=);
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

        if self.pattern_syntax == 're-spaces':
            self.pattern = decode_re_spaces(self.pattern)

        if isinstance(self.pattern_flags, str):
            self.pattern_flags = re_flags_to_int(self.pattern_flags)

        if self.pattern_syntax != 'plain':
            self._compiled_re = re.compile(self.pattern, self.pattern_flags)

    def match(self, string: str):
        if self.pattern_syntax == 'plain':
            return string == self.pattern

        m = self._compiled_re.match(string)
        if m:
            return Match(m, self)
        return None


@dataclass
class Match:
    re_match: re.Match
    pattern: ConfidentPattern


class CellType:
    """ Класс (разновидность) контента ячейки,
        характеризующийся собственным набором паттернов """

    def __init__(self, name='a', patterns=None):
        self.name = name
        self.patterns = self.prepare_patterns(patterns, self)

    @classmethod
    def prepare_patterns(cls, patterns, content_class):
        assert patterns, 'at least one pattern is required'
        if isinstance(patterns, ConfidentPattern):
            return [patterns]
        if isinstance(patterns, str):
            return [ConfidentPattern(patterns)]

        ps = [
            p if isinstance(patterns, ConfidentPattern) else ConfidentPattern(p, content_class=content_class)
            for p in patterns
        ]
        ps.sort(key=lambda p: p.confidence, reverse=True)
        return ps


def read_cell_types(config_file: str = '../cnf/cell_types.yml') -> Dict[str, CellType]:
    with open(config_file) as f:
        data = yaml.safe_load(f)

    cell_types = {}
    for kt in data['cell_types']:
        for k, t in kt.items():
            cell_types[k] = CellType(**t)

    return cell_types
