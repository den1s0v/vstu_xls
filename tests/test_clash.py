import unittest

from tests_bootstrapper import init_testing_environment

init_testing_environment()

from clash import *


class ClashTestCase(unittest.TestCase):
    def test_set_type(self):
        a = ClashingElementSet.make([])
        b = ClashingElementSet.make([])

        self.assertIsInstance(a, ClashingElementSet)
        self.assertIsInstance(b, ClashingElementSet)

        u = a | b
        self.assertEqual(set, type(u))

        self.assertIsInstance(ClashingElementSet(u), ClashingElementSet)

    def test_clash_1(self):
        objs = [
            [1, 2],
            [2, 3],
            [3, 4],
        ]
        combs = find_combinations_of_compatible_elements(objs, components_getter=trivial_components_getter)

        self.assertEqual([
            [[1, 2], [3, 4]],
            [[2, 3]],
        ], combs)

    def test_clash_2(self):
        objs = [
            [1, 2],
            [2, 3],
            [3, 4],
            [4, 5],
            [5, 1],
        ]
        combs = find_combinations_of_compatible_elements(objs, components_getter=lambda x: x)

        self.assertEqual([
            [[1, 2], [3, 4]],
            [[1, 2], [4, 5]],
            [[2, 3], [4, 5]],
            [[2, 3], [5, 1]],
        ], combs)


if __name__ == '__main__':
    unittest.main()
