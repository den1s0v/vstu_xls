import re
from functools import lru_cache

import geom2d.open_range as ns


@lru_cache()
def parse_range(s: str) -> 'ns.open_range':
    """ Parse an integer range in form of the following (including upper bound)
    | `3`
    | `3+`
    | `3-`
    | `3..5`
    | `3, 5`
    | `-3`
    | `-3+`
    | `-3-`
    | `*` (any value)
    | `*,*` (any value)
    | `-5..-3`
    | `-5, -3`
    | `-5, *`
    | `-5 .. *`
    | `* .. 5`
    | `* .. *`
    |
    """
    s = s.strip()

    if s == '*':
        return ns.open_range(None, None)

    number_pattern = r'([+-]?\d+)'
    single_range_pattern = f'{number_pattern}([+-]?)'
    L, R = None, None

    if m := re.fullmatch(single_range_pattern, s):
        value_str = m[1]
        value = int(value_str)
        post_sign_str = m[2]
        match post_sign_str:
            case '':
                L, R = value, value
            case '-':
                L, R = None, value
            case '+':
                L, R = value, None

    if not m:
        number_pattern = r'([+-]?\d+|\*)'  # '*' added.
        middle_chars = r'\.{2,3}|,'
        double_range_pattern = rf'{number_pattern}\s*(?:{middle_chars})\s*{number_pattern}'

        if m := re.fullmatch(double_range_pattern, s):
            value_1_str = m[1]
            L = int(value_1_str) if value_1_str != '*' else None
            value_2_str = m[2]
            R = int(value_2_str) if value_2_str != '*' else None

    if m:
        return ns.open_range(L, R)

    raise ValueError("cannot parse_range(%s)" % repr(s))


def parse_size_range(s: str) -> tuple['ns.open_range', 'ns.open_range']:
    """ Parse a ranged size as a couple of integer ranges in form of the following (by default including upper bound)
    | `8+ x 1`
    | `4+ x 1..2`
    | `5+ x 59+`
    | `1 x 1`
    | `5+ x 4`
    | `1..4 x 2+`
    |
    """

    s = s.strip()
    range_pattern = r'(.+)'
    middle_chars = r'[xх]'  # latin 'x' & cyrillic 'х'
    size_range_pattern = rf'{range_pattern}\s*{middle_chars}\s*{range_pattern}'

    if m := re.fullmatch(size_range_pattern, s, re.IGNORECASE):

        r1 = parse_range(m[1])
        r2 = parse_range(m[2])

        return r1, r2

    raise ValueError("cannot parse_size_range(%s)" % repr(s))
