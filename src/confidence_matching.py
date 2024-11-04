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
import math
import re
from dataclasses import dataclass
from typing import List, Dict, Optional, Union

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


_RE_SEVERAL_SPACES = re.compile(r'\s{2,}')
_RE_SPACES = re.compile(r'\s+')
_RE_GAPS = re.compile(r'\b\s+\b')
_RE_HYPEN_SPACED = re.compile(r'\s*-\s*')
_RE_LIST_OF_FREE_FORM_SEP = re.compile(r'\s*[,\s]\s*')


def shrink_extra_inner_spaces(string: str):
    """ Replace each sequence of several whitespaces with one space. """
    return _RE_SEVERAL_SPACES.sub(" ", string)


def fix_sparse_words(string: str, _mul_of_longest_as_sep=2, _min_spaces=5):
    """ Try fix:
     'М А Т Е М А Т И К А' -> 'МАТЕМАТИКА'
     'И Н.   Я З Ы К' -> 'ИН. ЯЗЫК' (note: keep space between words)
     """
    # if string.count(' ') < _min_spaces:
    # if len(gap_ms := _RE_GAPS.findall(string)) < _min_spaces:
    spaces_count = string.count(" ")
    if spaces_count == 0 or spaces_count * 2 < len(string) - 1:
        # not enough spaces to apply this transformation
        return string
    gaps = {len(s) for s in _RE_GAPS.findall(string)}

    if not gaps:
        return string

    gaps = sorted(gaps)
    # min_gap, max_gap = min(gaps), max(gaps)
    min_gap = min(gaps)

    # TODO: min_gap = 0, если слова без разрывов (???)

    # separator_min_len = max(min_gap + 1, math.ceil(max_gap - (_frac_of_longest_as_sep or 0.5) * (max_gap - min_gap)))
    separator_min_len = math.ceil(_mul_of_longest_as_sep * min_gap)

    words = string.split(" " * separator_min_len)
    # remove spaces from each word
    words = [_RE_SPACES.sub('', w) for w in words]
    # filter empty words (if any), before joining words back
    return " ".join(w for w in words if w)


class ConfidentPattern:
    """ Паттерн для сопоставления строк со степенью уверенности.
        Синтаксисы паттерна (`pattern_syntax`):
         - 're' (regexp)
         - 're-spaces' (regexp in simplified notation @see)
         - 'plain' (plain text)

        `pattern_fields` используется,
        если паттерн содержит группы захвата (запоминающие скобки),
        чтобы указать имена групп захвата (в порядке их появления).

        `preprocess`: 'fix_sparse_words', 'remove_all_spaces', 'remove_spaces_around_hypen' or nothing

        `update_content`: 'clear', 'replace_with_preprocessed' or nothing
    """
    pattern: str = None
    confidence: float = 0.5
    pattern_syntax: str = 're'  # plain / re (regexp) / re-spaces
    pattern_flags: int | str = 0
    pattern_fields: tuple = ()
    content_class: 'CellType' = None
    preprocess: list[str] = None

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
        assert kw['content_class'], 'Please specify content_class for ConfidentPattern!'
        # set all attributes
        for k, v in kw.items():
            setattr(self, k, v)

        if self.pattern_syntax == 're-spaces':
            self.pattern = decode_re_spaces(self.pattern)

        if isinstance(self.pattern_flags, str):
            self.pattern_flags = re_flags_to_int(self.pattern_flags)

        if self.pattern_syntax != 'plain':
            self._compiled_re = re.compile(self.pattern, self.pattern_flags)

        if self.preprocess is not None and isinstance(self.preprocess, str):
            self.preprocess = _RE_LIST_OF_FREE_FORM_SEP.split(self.preprocess)

    def match(self, string: str) -> Union['Match', None]:
        if self.pattern_syntax == 'plain':
            if string == self.pattern:
                return Match(re.Match(string), self, string)

        else:
            string = self.preprocess_token(string)
            m = self._compiled_re.match(string)
            if m:
                return Match(m, self, string)
        return None

    def preprocess_token(self, string: str) -> str:
        # use custom transformations if set
        if self.preprocess:
            for tr in self.preprocess:
                if tr == 'fix_sparse_words':
                    string = fix_sparse_words(string)
                elif tr == 'remove_all_spaces':
                    string = string.replace(" ", '')
                elif tr == 'remove_spaces_around_hypen':
                    string = _RE_HYPEN_SPACED.sub("-", string)

        # Default preprocess steps:
        # cut whitespaces outside
        string = string.strip()
        # cut extra whitespaces inside
        string = shrink_extra_inner_spaces(string)

        return string


@dataclass
class Match:
    re_match: re.Match
    pattern: ConfidentPattern
    cell_text: str

    @property
    def confidence(self):
        return self.pattern.confidence


class CellType:
    """ Класс (разновидность) контента ячейки,
        характеризующийся собственным набором паттернов """
    name: str
    description: str
    patterns: List[ConfidentPattern]
    update_content: list[str] = ()

    def __init__(self, name='a', description='no info', patterns=None, update_content=None):
        self.name = name
        self.description = description
        self.patterns = self.prepare_patterns(patterns, self)

        if update_content is not None and isinstance(update_content, str):
            self.update_content = _RE_LIST_OF_FREE_FORM_SEP.split(update_content)

    @classmethod
    def prepare_patterns(cls, patterns, content_class, transformations=None):
        assert patterns, 'at least one pattern is required'
        if isinstance(patterns, ConfidentPattern):
            return [patterns]
        if isinstance(patterns, str):
            return [ConfidentPattern(patterns)]

        ps = [
            p if isinstance(patterns, ConfidentPattern) else ConfidentPattern(**p, content_class=content_class)
            for p in patterns
        ]
        ps.sort(key=lambda p: p.confidence, reverse=True)
        return ps

    def match(self, cell_text: str) -> Optional[Match]:
        """Return match according to pattern with highest confidence."""
        for p in self.patterns:
            if m := p.match(cell_text):
                return m
        return None



def read_cell_types(config_file: str = '../cnf/cell_types.yml') -> Dict[str, CellType]:
    with open(config_file, encoding='utf-8') as f:
        data = yaml.safe_load(f)

    cell_types = {}
    for kt in data['cell_types']:
        for k, t in kt.items():
            cell_types[k] = CellType(name=k, **t)

    return cell_types


class CellClassifier:
    """ Классификатор для контента ячейки,
        находит для данной строки наиболее подходящие типы
        из известных CellType """
    cell_types: List[CellType]

    def __init__(self, cell_types=None):
        if not cell_types:
            cell_types = list(read_cell_types().values())
        self.cell_types = cell_types

    def match(self, cell_text: str) -> List[Match]:
        matches = []
        for ct in self.cell_types:
            if m := ct.match(cell_text):
                matches.append(m)

        matches.sort(key=lambda m: m.confidence, reverse=True)
        return matches

