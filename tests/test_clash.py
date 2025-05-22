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
        a = [1, 2, 3]
        b = [2, 3, 4]

        combs = find_combinations_of_compatible_elements((a, b), components_getter=lambda x: x)

        self.assertSetEqual({
            {1, 2, 3, 4},
        }, set(combs))


if __name__ == '__main__':
    unittest.main()
