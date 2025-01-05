import unittest

from tests_bootstrapper import init_testing_environment

init_testing_environment()

from grammar.ArithmeticRelation import ArithmeticRelation, eq, lt, gt, distance
from grammar.ArithmeticRelation import parse_relation_and_limits
from grammar.ArithmeticRelation import parse_range, parse_size_range


class ArithmeticRelationTestCase(unittest.TestCase):
    def test_1(self):
        ar = ArithmeticRelation()
        # self.assertEqual(True, False)  # add assertion here

    def test_range(self):
        # self.assertIn(-99, range(None, None, None))
        # self.assertIn(+99, range(None, None, None))
        ...


class ExprTestCase(unittest.TestCase):
    def test_simple(self):
        expr = '<='
        self.assertEqual((lt, (0, None)), parse_relation_and_limits(expr))

        expr = '>>'
        self.assertEqual((gt, (1, None)), parse_relation_and_limits(expr))

        expr = '=='
        self.assertEqual((eq, (1, 1)), parse_relation_and_limits(expr))

        expr = '<>'
        self.assertEqual((lt, (None, None)), parse_relation_and_limits(expr))

    def test_complex(self):
        expr = '<123<'
        self.assertEqual((lt, (123, 123)), parse_relation_and_limits(expr))

        expr = '<1..23<'
        self.assertEqual((lt, (1, 23)), parse_relation_and_limits(expr))

        expr = '>-90,23>'
        self.assertEqual((gt, (-90, 23)), parse_relation_and_limits(expr))

        expr = '<90->'
        self.assertEqual((distance, (0, 90)), parse_relation_and_limits(expr))

        expr = '<6+>'
        self.assertEqual((distance, (6, None)), parse_relation_and_limits(expr))


class RangeTestCase(unittest.TestCase):

    def test_range(self):
        self.assertNotIn(-1, range(0, 5))
        self.assertIn(0, range(0, 5))
        self.assertIn(4, range(0, 5))
        self.assertNotIn(5, range(0, 5))

        inf = 999999  # See default value for `inf_value` arg of `parse_range()`

        expr = '1'
        self.assertEqual(range(1, 1 + 1), parse_range(expr))

        expr = '1'
        self.assertEqual(range(1, 1 + 0), parse_range(expr, incr_upper_bound=False))

        expr = '9'
        self.assertEqual(range(9, 9 + 1), parse_range(expr))

        expr = '194'
        self.assertEqual(range(194, 194 + 1), parse_range(expr))

        expr = '0+'
        self.assertEqual(range(0, inf), parse_range(expr))

        expr = '0+'
        self.assertEqual(range(0, inf), parse_range(expr, incr_upper_bound=False))

        expr = '0-'
        self.assertEqual(range(-inf, 0 + 1), parse_range(expr))

        expr = '0-'
        self.assertEqual(range(-inf, 0 + 0), parse_range(expr, incr_upper_bound=False))

        expr = '3'
        self.assertEqual(range(3, 3 + 1), parse_range(expr))

        expr = '+3'
        self.assertEqual(range(3, 3 + 1), parse_range(expr))

        expr = '3+'
        self.assertEqual(range(3, inf), parse_range(expr))

        expr = '+3+'
        self.assertEqual(range(3, inf), parse_range(expr))

        expr = '3-'
        self.assertEqual(range(-inf, 3 + 1), parse_range(expr))

        expr = ' * '
        self.assertEqual(range(-inf, inf), parse_range(expr))

        expr = '3..5'
        self.assertEqual(range(3, 5 + 1), parse_range(expr))

        expr = '3, 5'
        self.assertEqual(range(3, 5 + 1), parse_range(expr))

        expr = '-3'
        self.assertEqual(range(-3, -3 + 1), parse_range(expr))

        expr = '-3+'
        self.assertEqual(range(-3, inf), parse_range(expr))

        expr = '-3-'
        self.assertEqual(range(-inf, -3 + 1), parse_range(expr))

        expr = '-5..-3'
        self.assertEqual(range(-5, -3 + 1), parse_range(expr))

        expr = '-5 ... -3'
        self.assertEqual(range(-5, -3 + 1), parse_range(expr))

        expr = '-5, -3'
        self.assertEqual(range(-5, -3 + 1), parse_range(expr))

        expr = '-5, -3'
        self.assertEqual(range(-5, -3 + 0), parse_range(expr, incr_upper_bound=False))

        expr = '-5, *'
        self.assertEqual(range(-5, inf), parse_range(expr))

        expr = '-5 .. *'
        self.assertEqual(range(-5, inf), parse_range(expr))

        expr = '* .. 5'
        self.assertEqual(range(-inf, 5 + 1), parse_range(expr))

        expr = '* .. *'
        self.assertEqual(range(-inf, inf), parse_range(expr))

    def test_size_range(self):
        inf = 999999

        expr = '1x0'
        self.assertEqual((
            range(1, 1 + 1),
            range(0, 0 + 1)),
            parse_size_range(expr))

        expr = '0x974'
        self.assertEqual((
            range(0, 0 + 1),
            range(974, 974 + 1)),
            parse_size_range(expr))

        expr = '8+ x 1'
        self.assertEqual((
            range(8, inf),
            range(1, 1 + 1)),
            parse_size_range(expr))

        expr = '4+ x 1..2'
        self.assertEqual((
            range(4, inf),
            range(1, 2 + 1)),
            parse_size_range(expr))

        expr = '5- x 59+'
        self.assertEqual((
            range(-inf, 5 + 1),
            range(59, inf)),
            parse_size_range(expr))

        expr = '1 x 1'
        self.assertEqual((
            range(1, 1 + 1),
            range(1, 1 + 1)),
            parse_size_range(expr))

        expr = '5+ x 4'
        self.assertEqual((
            range(5, inf),
            range(4, 4 + 1)),
            parse_size_range(expr))

        expr = '1..4 x 2+'
        self.assertEqual((
            range(1, 4 + 1),
            range(2, inf)),
            parse_size_range(expr))

    @unittest.expectedFailure
    def test_size_range_empty_error1(self):
        """ Reversed range """
        expr = '-5, -8'
        parse_range(expr)

    @unittest.expectedFailure
    def test_size_range_empty_error2(self):
        """ Too low inf_value """
        expr = '-5000-'
        parse_range(expr, inf_value=999)

