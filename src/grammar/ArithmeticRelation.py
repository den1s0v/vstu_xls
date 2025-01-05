# ArithmeticRelation.py


from typing import Tuple, Literal, Union, Callable, Optional

from operator import sub, eq
import re

# def eq(x: int, y: int):
#     return 0 if x == y else 1  # flips normal 'eq' semantics (?!!)


lt = sub


# def lt(x: int, y: int):
#     return x - y

def gt(x: int, y: int):
    return y - x


def distance(x: int, y: int):
    return abs(y - x)


class ArithmeticRelation:
    """
        A == B eq (default)
        A < B  lt
        A > B  gt
        A <> B distance
    """

    def __init__(self,
                 op: Union[str, Callable] = lt,
                 limits: Tuple[Optional[int], Optional[int]] = (0, 0),
                 a=None, b=None):
        assert hasattr(op, '__call__'), 'callable expected'
        self.op = op
        assert len(limits) == 2
        self.limits = limits
        self.a = a
        self.b = b

    def test(self, x: int, y: int):
        diff = self.op(x, y)
        low, top = self.limits
        return (low is None or low <= diff) and \
               (low is None or diff <= top)


def parse_relation_and_limits(s: str) -> Tuple[Callable, Tuple[Optional[int], Optional[int]]]:
    s = s.strip()
    if s in ('<', '<='):
        return lt, (0, None)
    if s == '<<':
        return lt, (1, None)
    if s in ('=', '=='):
        return eq, (1, 1)
    if s in ('>', '>='):
        return gt, (0, None)
    if s == '>>':
        return gt, (1, None)
    # no limits:
    if s == '<>':
        return lt, (None, None)  # distance?

    op = None
    range_str = None
    # 3
    # 3+
    # 3-
    # 3..5
    # 3, 5
    # -3
    # -3+
    # -3-
    # -5..-3
    # -5, -3
    range_pattern = r'(-?\d+(?:\.\.-?\d+|,\s*-?\d+|[+-])?)'
    if m := re.match(f'<{range_pattern}<$', s):
        op = lt
        range_str = m[1]
    if m := re.match(f'>{range_pattern}>$', s):
        op = gt
        range_str = m[1]
    if m := re.match(f'<{range_pattern}>$', s):
        op = distance
        range_str = m[1]

    if not range_str:
        raise ValueError(f'Relation format not recognized: `{s}`')

    # parse range_str into two borders
    if '..' in range_str:
        low, top = (int(x) for x in range_str.split('..'))
    elif ',' in range_str:
        low, top = (int(x.strip()) for x in range_str.split(','))
    elif range_str.endswith('+'):
        x = int(range_str.rstrip('+'))
        low, top = (x, None)
    elif range_str.endswith('-'):
        x = int(range_str.rstrip('-'))
        low, top = (0, x)
    else:
        x = int(range_str)
        low, top = (x, x)

    return op, (low, top)

    # # the default
    # return lt, (0, 0)


def parse_range(s: str, incr_upper_bound=True, inf_value=999999) -> range:
    """ Parse an integer range in form of the following (by default including upper bound)
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
    Note: `range` cannot express true infinite bounds, so use practically reliable positive `inf_value`.
    """
    s = s.strip()

    if s == '*':
        return range(-inf_value, +inf_value)

    number_pattern = r'([+-]?\d+)'
    single_range_pattern = f'{number_pattern}([+-]?)'
    L, R = None, None

    if m := re.fullmatch(single_range_pattern, s):
        value_str = m[1]
        value = int(value_str)
        post_sign_str = m[2]
        match post_sign_str:
            case '':
                L, R = value, value + incr_upper_bound
            case '-':
                L, R = -inf_value, value + incr_upper_bound
            case '+':
                L, R = value, inf_value

    if not m:
        number_pattern = r'([+-]?\d+|\*)'  # '*' added.
        middle_chars = r'\.{2,3}|,'
        double_range_pattern = rf'{number_pattern}\s*(?:{middle_chars})\s*{number_pattern}'

        if m := re.fullmatch(double_range_pattern, s):
            value_1_str = m[1]
            L = int(value_1_str) if value_1_str != '*' else -inf_value
            value_2_str = m[2]
            R = int(value_2_str) + incr_upper_bound if value_2_str != '*' else inf_value

    if m:
        if L > R - incr_upper_bound:
            raise ValueError(f"invalid empty range in parse_range({repr(s)}) -> ({L}, {R})")
        return range(L, R)

    raise ValueError("cannot parse_range(%s)" % repr(s))


def parse_size_range(s: str, incr_upper_bound=True, inf_value=999999) -> tuple[range, range]:
    """ Parse a ranged size as a couple of integer ranges in form of the following (by default including upper bound)
    | `8+ x 1`
    | `4+ x 1..2`
    | `5+ x 59+`
    | `1 x 1`
    | `5+ x 4`
    | `1..4 x 2+`
    |
    Note: `range` cannot express true infinite bounds, so use practically reliable positive `inf_value`.
    """
    s = s.strip()
    range_pattern = r'(.+)'
    middle_chars = r'[xх]'  # latin 'x' & cyrillic 'х'
    size_range_pattern = rf'{range_pattern}\s*{middle_chars}\s*{range_pattern}'

    if m := re.fullmatch(size_range_pattern, s, re.IGNORECASE):
        range_1_str = m[1]
        range_2_str = m[2]

        r1 = parse_range(range_1_str, incr_upper_bound, inf_value)
        r2 = parse_range(range_2_str, incr_upper_bound, inf_value)

        return r1, r2

    raise ValueError("cannot parse_size_range(%s)" % repr(s))
