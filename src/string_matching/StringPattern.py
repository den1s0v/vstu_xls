import re
from typing import Union

import string_matching.CellType as ns
from string_matching.StringMatch import StringMatch
from string_matching.StringTransformer import StringTransformer


# A comma or a mandatory space with optional spaces around.
RE_COMMON_SEPARATOR = re.compile(r'\s*[,\s]\s*')


VALID_pattern_syntax = {'re', 're-spaces', 'plain'}
VALID_preprocess = {'fix_sparse_words', 'remove_all_spaces', 'remove_spaces_around_hypen'}


class StringPattern:
    """ Паттерн для сопоставления строк со степенью уверенности.

    `pattern`: pattern to match

    `confidence`: confidence level in range [0..1] associated with the pattern.

    `pattern_syntax` — синтаксисы паттерна:
     - 're' (regexp, python's `re` lib), the default.
     - 're-spaces' (regexp in simplified notation @see (…?)).
     - 'plain' (exact plain text; pattern_flags are ignored).

    `pattern_flags`: optional string of space-separated regexp flags defined in `re` lib (I M S X - IGNORECASE MULTILINE DOTALL VERBOSE)

    `captures` используется,
    если паттерн содержит группы захвата (запоминающие скобки),
    чтобы указать имена групп захвата (в порядке их появления).
    Если же regex использует именованные группы захвата ( `…(?P<your_name>...)…` ) и определяет все указанные имена,
    то их взаимный порядок в паттерне может не соблюдаться.

    `content_class`: `CellType` instance.

    `preprocess`: optional names of transformations to apply first.
     Available so far: 'fix_sparse_words', 'remove_all_spaces', 'remove_spaces_around_hypen'.
    """
    pattern: str = None
    confidence: float = 0.5
    pattern_syntax: str = 're'  # one of: 'plain' / 're' (regexp) / 're-spaces'
    pattern_flags: int | str = 0
    captures: tuple = ()
    content_class: 'ns.CellType|str' = '<Unspecified content_class>'
    preprocess: list[str] = None

    def __init__(self, *args, **kwargs):
        """Valid calls:
        StringPattern(pattern='abc+', confidence=0.9);
        StringPattern('abc+', confidence=0.9);
        StringPattern('abc+', 0.9, pattern_flags=);
        StringPattern('a b c', 0.9, pattern_syntax='re-spaces');
        StringPattern('a b c', 0.9, 're-spaces');

        # dict-based:
        StringPattern({'pattern': 'abc+', 'confidence': 0.9});
        StringPattern({'pattern': 'abc+', 'confidence': 0.9, 'pattern_syntax': 're-spaces'});
        """
        if len(args) == 1 and isinstance(args[0], dict):
            # dict passed
            kwargs = args[0]
        elif len(args) == 1 and isinstance(args[0], StringPattern):
            # copying
            kwargs = vars(args[0])
        elif len(args) > 0:
            # integrate positional arguments
            for key, val in zip(StringPattern.__annotations__.keys(), args):
                if key not in kwargs:
                    kwargs[key] = val

        # read defaults from annotations
        kw = {k: getattr(StringPattern, k) for k in StringPattern.__annotations__}
        kw.update(kwargs)
        assert kw['pattern'], 'Please specify pattern for StringPattern!'
        assert kw['content_class'], 'Please specify content_class for StringPattern!'
        # set all attributes
        for k, v in kw.items():
            setattr(self, k, v)

        if self.preprocess is not None and isinstance(self.preprocess, str):
            self.preprocess = RE_COMMON_SEPARATOR.split(self.preprocess)

        # check input values to match enums
        assert (self.pattern_syntax in VALID_pattern_syntax), f"StringPattern.pattern_syntax must be one of {VALID_pattern_syntax}, got: `{self.pattern_syntax}`."

        assert not (set(self.preprocess or ()) - VALID_preprocess), f"StringPattern.preprocess must contain one or more of {VALID_preprocess}, got: `{self.preprocess}`."

        assert (0 <= self.confidence <= 1), f"StringPattern.confidence must be within [0..1], got: `{self.confidence}`."

        if self.pattern_syntax == 're-spaces':
            # convert regex in 're-spaces' to ordinary 're'
            self.pattern = StringTransformer.apply('decode_re_spaces', self.pattern)

        if isinstance(self.pattern_flags, str):
            # parse regex flags
            self.pattern_flags = re_flags_to_int(self.pattern_flags)

        if self.pattern_syntax != 'plain':
            self._compiled_re = re.compile(self.pattern, self.pattern_flags)

    def match(self, string: str) -> Union['StringMatch', None]:
        string = self.preprocess_string(string)

        if self.pattern_syntax == 'plain':
            if string == self.pattern:
                re_match_imitation = [string]  # list has `0` index
                return StringMatch(re_match_imitation, self, string)

        else:
            m = self._compiled_re.match(string)
            if m:
                return StringMatch(m, self, string)
        return None

    def preprocess_string(self, string: str) -> str:
        transformations = []

        # use custom transformations if set
        if self.preprocess:
            transformations.extend(self.preprocess)

        # add default preprocess steps:
        transformations += [
            # cut whitespaces outside
            str.strip,
            # cut extra whitespaces inside
            'shrink_extra_inner_spaces',
        ]

        for tr in transformations:
            string = StringTransformer.apply(tr, string)

        return string

    def logical_index_to_re_group_index(self, re_match: re.Match | list[str], index_or_name: int | str):
        """
        :param re_match: re.Match object to find index for
        :param index_or_name: high-level index (e.g. name from `captures`)
        :return: index suitable for `re_match[…]`, or `None` if it does not exist.
        """
        if index_or_name == 0:
            # do not convert reference to "whole string"
            return index_or_name

        try:
            if self.captures and isinstance(re_match, re.Match) and set(re_match.groupdict().keys()) == set(self.captures):
                # string expected, as regex is fully defined: all named groups set.
                if isinstance(index_or_name, int):
                    return self.captures[index_or_name - 1]
                elif index_or_name in self.captures:
                    return index_or_name  # string as is.
            else:
                # int (number of positional group) expected, as regex does not define (all) named groups.
                if isinstance(index_or_name, str):
                    return self.captures.index(index_or_name) + 1
                return index_or_name  # int as is.
        except (ValueError, IndexError):
            return None

    def calc_precision_of_match(self, match: StringMatch) -> float:
        """ Precision of `match` in range [0..1], by default defined as `pattern.confidence * match.coverage_ratio`. """
        return self.confidence * match.coverage_ratio


def re_flags_to_int(re_flags: str = '') -> int:
    """Get int union of flags for re.* constants:
     I M S X - IGNORECASE MULTILINE DOTALL VERBOSE"""
    bit_flags = 0
    # default: search names within `re` module
    for name in re_flags.split():
        bad_flag = False
        try:
            flag = getattr(re, name)

            if isinstance(flag, re.RegexFlag):
                bit_flags |= flag
            else:
                bad_flag = True
        except AttributeError:
            bad_flag = True

        if bad_flag:
            # TODO: use logging
            print(f'WARN: unknown regex flag `{name}` (in pattern_flags: {re_flags}).')

    # TODO: remove old ugly implementation below.
    re_flags = re_flags.upper()
    if 'I' in re_flags:
        bit_flags |= re.I
    if 'M' in re_flags:
        bit_flags |= re.M
    if 'S' in re_flags:
        bit_flags |= re.S
    if 'X' in re_flags:
        bit_flags |= re.X
    return bit_flags

