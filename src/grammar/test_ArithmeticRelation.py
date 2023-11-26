import unittest

from grammar.ArithmeticRelation import ArithmeticRelation, eq, lt, gt, distance, parse_relation_and_limits


class ArithmeticRelationTestCase(unittest.TestCase):
    def test_1(self):
        ar = ArithmeticRelation()
        self.assertEqual(True, False)  # add assertion here

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



if __name__ == '__main__':
    unittest.main()
