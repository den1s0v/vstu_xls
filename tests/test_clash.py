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

    def test_sets(self):
        """ Testing internal operations """
        objs = [
            '9',
            '0',
            'a1',
            'b2',
            'c3',
            '1234',
        ]
        clashing_set = ClashingElementSet.make(
            objs,
            trivial_components_getter,
        )

        expected_free = {
            'a1': ['0', '9', 'b2', 'c3', ],
            'b2': ['0', '9', 'a1', 'c3', ],
            'c3': ['0', '9', 'a1', 'b2', ],
            '1234': ['0', '9', ],
            '0': ['1234', '9', 'a1', 'b2', 'c3', ],
            '9': ['0', '1234', 'a1', 'b2', 'c3', ],
        }

        for clashing_set_1 in (clashing_set, clashing_set.clone()):
            for el_0 in clashing_set_1:
                for el in (el_0, el_0.clone(), el_0.clone().clone()):
                    el_raw: str = el.obj

                    self.assertIn(el, clashing_set, el)
                    self.assertIn(el.clone(), clashing_set, el)

                    clash = el.all_clashing_among(clashing_set).get_bare_objs()
                    free = el.all_independent_among(clashing_set).get_bare_objs()

                    self.assertEqual(expected_free[el_raw], free, ('free →', el))

                    expected_clash = sorted_list(set(objs) - set(expected_free[el_raw]) - {el_raw})
                    self.assertEqual(expected_clash, clash, ('clash →', el))

        base = clashing_set
        reducible = clashing_set.clone()

        for el in base:
            self.assertIn(el, base, el)
            self.assertIn(el, reducible, el)
            reducible.remove(el)
            self.assertIn(el, base, el)
            self.assertNotIn(el, reducible, el)
        self.assertFalse(bool(reducible))

        reducible = clashing_set | set()

        for el in base:
            self.assertIn(el, base, el)
            self.assertIn(el, reducible, el)
            reducible.remove(el)
            self.assertIn(el, base, el)
            self.assertNotIn(el, reducible, el)
        self.assertFalse(bool(reducible))

        reducible = clashing_set - set()

        for el in base:
            self.assertIn(el, base, el)
            self.assertIn(el, reducible, el)
            reducible.remove(el)
            self.assertIn(el, base, el)
            self.assertNotIn(el, reducible, el)
        self.assertFalse(bool(reducible))

    def test_clash_01(self):
        objs = [
            'a1',
            'b2',
            'c3',
            '1234',
        ]
        combs = find_combinations_of_compatible_elements(objs, components_getter=trivial_components_getter)

        self.assertEqual([
            ['1234'],
            ['a1', 'b2', 'c3'],
        ], combs)

    def test_clash_02_one_free(self):
        objs = [
            '0',
            'a1',
            'b2',
            'c3',
            '1234',
        ]
        combs = find_combinations_of_compatible_elements(objs, components_getter=trivial_components_getter)

        self.assertEqual([
            ['0', '1234'],
            ['0', 'a1', 'b2', 'c3'],
        ], combs)

    def test_clash_021_two_free(self):
        objs = [
            '9',
            '0',
            'a1',
            'b2',
            'c3',
            '1234',
        ]
        combs = find_combinations_of_compatible_elements(objs, components_getter=trivial_components_getter)

        self.assertEqual([
            ['0', '1234', '9', ],
            ['0', '9', 'a1', 'b2', 'c3', ],
        ], combs)

    def test_clash_03_all_touch(self):
        objs = [
            'x0',
            'x1',
            'x2',
            'x3',
            'x4',
        ]
        combs = find_combinations_of_compatible_elements(objs, components_getter=trivial_components_getter)

        self.assertEqual([
            ['x0'],
            ['x1'],
            ['x2'],
            ['x3'],
            ['x4'],
        ], combs)

    def test_clash_04_all_free(self):
        objs = [
            '0',
            '1',
            '2',
            '3',
            '4',
        ]
        combs = find_combinations_of_compatible_elements(objs, components_getter=trivial_components_getter)

        self.assertEqual([
            ['0', '1', '2', '3', '4', ]
        ], combs)

    def test_clash_05_one_conflict(self):
        objs = [
            '0',
            '1',
            '2x',
            '3',
            '4x',
        ]
        combs = find_combinations_of_compatible_elements(objs, components_getter=trivial_components_getter)

        self.assertEqual([
            ['0', '1', '2x', '3', ],
            ['0', '1', '3', '4x', ],
        ], combs)

    def test_clash_05_two_groups(self):
        objs = [
            '0x',
            '0y',
            '0z',
            'x',
            'y',
            'z',
        ]
        combs = find_combinations_of_compatible_elements(objs, components_getter=trivial_components_getter)

        self.assertEqual([
            ['0x', 'y', 'z', ],
            ['0y', 'x', 'z', ],
            ['0z', 'x', 'y', ],
            ['x', 'y', 'z', ],
        ], combs)

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

    def test_clash_1_strings(self):
        objs = [
            ['1', '2'],
            ['2', '3'],
            ['3', '4'],
        ]
        combs = find_combinations_of_compatible_elements(objs, components_getter=trivial_components_getter)

        self.assertEqual([
            [['1', '2'], ['3', '4']],
            [['2', '3']],
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
            [[3, 4], [5, 1]],
        ], combs)

    def test_clash_3_two_clusters(self):
        r"""
        Visually (a link means a conflict, a pair-wise clash):

		   2         (1a)         8
			\       /    \       /
		3 — (x234+15)    (y876*ab) — 7
			/       \    /       \
		   4         (5b)         6

	    Conflict resolving is be done by removing "middle" elements.
        """
        objs = [
            '1a',
            '2',
            '3',
            '4',
            '5b',
            'x234+15',
            '6',
            '7',
            '8',
            'y876*ab',
        ]
        combs = find_combinations_of_compatible_elements(objs, components_getter=trivial_components_getter)

        self.assertEqual([
            ['1a', '2', '3', '4', '5b', '6', '7', '8', ],
            ['2', '3', '4', 'y876*ab', ],
            ['6', '7', '8', 'x234+15', ],
            ['x234+15', 'y876*ab', ],
        ], combs)

    def test_clash_4_grid_5x5_matches_2x2_8(self):
        r"""
        Data, visually:

        12345
        67890
        ABCDE
        FGHIJ
        KLNMO

        """

        # базовые квадраты 4x4 из четырёх 2x2:

        # grid 00 (плотная упаковка квадратов 2x2 c позиции (0,0))
        Q1 = [
    		'1267',
            '3489',
            'ABFG',
            'CDHI',
            ]

        # grid 11 (плотная упаковка квадратов 2x2 c позиции (1,1))
        Q2 = [
            '78BC',
            '90DE',
            'GHLN',
            'IJMO',
            ]

        objs = [
            *Q1, *Q2
        ]

        combs = find_combinations_of_compatible_elements(objs, components_getter=trivial_components_getter)

        self.assertEqual(sorted_list([
            # базовые квадраты
            sorted_list(Q1),
            sorted_list(Q2),
            # дальные стороны разных квадратов
            sorted_list([ *Q1[0:2], *Q2[2:4] ]),
            sorted_list([ Q1[0], Q1[2], Q2[1], Q2[3] ]),
            # уголок из 3-х и отстоящий угол от другого квадрата
            sorted_list([ *Q1[0:3], Q2[3] ]),
            sorted_list([ Q1[0], *Q2[1:4] ]),
        ]), combs)

    def test_clash_5_grid_5x5_matches_2x2_8(self):
        r"""
        Data, visually:

        12345
        67890
        ABCDE
        FGHIJ
        KLNMO

        Q:
        13
        24

        """

        # базовые квадраты 4x4 из четырёх 2x2:

        # grid 00 (плотная упаковка квадратов 2x2 c позиции (0,0))
        Q1 = [
    		'1267',
            '3489',
            'ABFG',
            'CDHI',
            ]

        # grid 01 (плотная упаковка квадратов 2x2 c позиции (0,1))
        Q2 = [
    		'67AB',
            '89CD',
            'FGKL',
            'HINM',
            ]

        # grid 10 (плотная упаковка квадратов 2x2 c позиции (1,0))
        Q3 = [
            '2378',
            '4590',
            'BCGH',
            'DEIJ',
            ]

        # grid 11 (плотная упаковка квадратов 2x2 c позиции (1,1))
        Q4 = [
            '78BC',
            '90DE',
            'GHLN',
            'IJMO',
            ]

        objs = [
            *Q1, *Q2, *Q3, *Q4,
        ]

        combs = find_combinations_of_compatible_elements(objs, components_getter=trivial_components_getter)

        # self.assertEqual(sorted_list([
        some_expected_combs = [
            # базовые квадраты
            sorted_list(Q1),
            sorted_list(Q2),
            sorted_list(Q3),
            sorted_list(Q4),

            # дальные стороны разных квадратов
            sorted_list([ *Q1[0:2], *Q2[2:4] ]),
            sorted_list([ *Q1[0:2], *Q3[2:4] ]),
            sorted_list([ *Q1[0:2], *Q4[2:4] ]),
            sorted_list([ Q1[0], Q1[2], Q2[1], Q2[3] ]),
            sorted_list([ Q1[0], Q1[2], Q3[1], Q3[3] ]),
            sorted_list([ Q1[0], Q1[2], Q4[1], Q4[3] ]),

            sorted_list([ *Q2[0:2], *Q4[2:4] ]),
            sorted_list([ Q2[0], Q2[2], Q4[1], Q4[3] ]),
            sorted_list([ Q2[0], Q2[2], Q4[1], Q4[3] ]),

            sorted_list([ *Q3[0:2], *Q2[2:4] ]),
            sorted_list([ *Q3[0:2], *Q4[2:4] ]),
            sorted_list([ Q3[0], Q3[2], Q4[1], Q4[3] ]),

            # уголок из 3-х и отстоящий угол от другого квадрата
            sorted_list([ *Q1[0:3], Q2[3] ]),
            sorted_list([ *Q1[0:3], Q3[3] ]),
            sorted_list([ *Q1[0:3], Q4[3] ]),

            sorted_list([ Q2[0], *Q2[2:4], Q1[1] ]),
            sorted_list([ Q2[0], *Q2[2:4], Q3[1] ]),
            sorted_list([ Q2[0], *Q2[2:4], Q4[1] ]),

            sorted_list([ *Q3[0:2], Q3[3], Q1[2] ]),
            sorted_list([ *Q3[0:2], Q3[3], Q2[2] ]),
            sorted_list([ *Q3[0:2], Q3[3], Q4[2] ]),

            sorted_list([ Q1[0], *Q4[1:4] ]),
            sorted_list([ Q2[0], *Q4[1:4] ]),
            sorted_list([ Q3[0], *Q4[1:4] ]),
        ]

        for objs in some_expected_combs:
	        self.assertIn(objs, combs)

    def __test_clash_6_grid_8x7_matches_2x2_shift(self):
        r"""
        Data, visually:

        12345678
        AB9CDEFG
        HIJKLNMO
        PQRSTUVW
        ab9cdefg
        hijklnmo
        pqrstuvw

        """
        objs = [
            # grid 00 (плотная упаковка квадратов 2x2 c позиции (0,0))
            '12AB',
            '349C',
            '56DE',
            '78FG',
            'HIPQ',
            'JKRS',
            'LNTU',
            'MOVW',
            'abhi',
            '9cjk',
            'deln',
            'fgmo',

            # grid 10 (плотная упаковка квадратов 2x2 c позиции (1,0))
            '23B9',
            '45CD',
            '67EF',
            'IJQR',
            'KLST',
            'NMUV',
            'b9ij',
            'cdkl',
            'efnm',

            # grid 01 (плотная упаковка квадратов 2x2 c позиции (0,1))
            'ABHI',
            '9CJK',
            'DELN',
            'FGMO',
            'PQab',
            'RS9c',
            'TUde',
            'VWfg',
            'hipq',
            'jkrs',
            'lntu',
            'movw',

            # grid 11 (плотная упаковка квадратов 2x2 c позиции (1,1))
            'B9IJ',
            'CDKL',
            'EFNM',
            'QRb9',
            'STcd',
            'UVef',
            'ijqr',
            'klst',
            'nmuv',
        ]
        combs = find_combinations_of_compatible_elements(objs, components_getter=trivial_components_getter)

        self.assertEqual([
            sorted_list(['12AB', '349C', '56DE', '78FG', 'HIPQ', 'JKRS', 'LNTU', 'MOVW', 'abhi', '9cjk', 'deln', 'fgmo',]),
            sorted_list(['23B9', '45CD', '67EF', 'IJQR', 'KLST', 'NMUV', 'b9ij', 'cdkl', 'efnm', ]),
            sorted_list(['ABHI', '9CJK', 'DELN', 'FGMO', 'PQab', 'RS9c', 'TUde', 'VWfg', 'hipq', 'jkrs', 'lntu', 'movw',]),
            sorted_list(['B9IJ', 'CDKL', 'EFNM', 'QRb9', 'STcd', 'UVef', 'ijqr', 'klst', 'nmuv',]),
        ], combs)


if __name__ == '__main__':
    unittest.main()
