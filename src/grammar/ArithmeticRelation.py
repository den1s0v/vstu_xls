# ArithmeticRelation.py


from typing import Tuple, Union, Callable, Optional

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


