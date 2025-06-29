import unittest

from tests_bootstrapper import init_testing_environment

init_testing_environment()

from clash import *


class ClashSetsTestCase(unittest.TestCase):
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


class ClashTestCase(unittest.TestCase):
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

    def test_clash_05_two_groups_rev_data(self):
        objs = [
            'ёx',
            'ёy',
            'ёz',
            'x',
            'y',
            'z',
        ]
        combs = find_combinations_of_compatible_elements(objs, components_getter=trivial_components_getter)

        self.assertEqual([
            (['x', 'y', 'z', ]),
            (['x', 'y', 'ёz', ]),
            (['x', 'z', 'ёy', ]),
            (['y', 'z', 'ёx', ]),
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
            [[1, 2], [3, 4]],  # +
            [[1, 2], [4, 5]],  # +
            [[2, 3], [4, 5]],  # !!!
            [[2, 3], [5, 1]],  # +
            [[3, 4], [5, 1]],  # !!!
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

        some_expected_combs = [
            # базовые квадраты
            sorted_list(Q1),
            sorted_list(Q2),
            # excessive arrangements ↓
            # # дальние стороны разных квадратов
            # sorted_list([*Q1[0:2], *Q2[2:4]]),
            # sorted_list([Q1[0], Q1[2], Q2[1], Q2[3]]),
            # # уголок из 3-х и отстоящий угол от другого квадрата
            # sorted_list([*Q1[0:3], Q2[3]]),
            # sorted_list([Q1[0], *Q2[1:4]]),
        ]

        print('resulting combs: ', len(combs))
        print(*combs, sep='\n')

        for objs in some_expected_combs:
            self.assertIn(objs, combs)


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

            # excessive arrangements ↓
            # # дальние стороны разных квадратов
            # sorted_list([*Q1[0:2], *Q2[2:4]]),
            # sorted_list([*Q1[0:2], *Q3[2:4]]),
            # sorted_list([*Q1[0:2], *Q4[2:4]]),
            # sorted_list([Q1[0], Q1[2], Q2[1], Q2[3]]),
            # sorted_list([Q1[0], Q1[2], Q3[1], Q3[3]]),
            # sorted_list([Q1[0], Q1[2], Q4[1], Q4[3]]),
            #
            # sorted_list([*Q2[0:2], *Q4[2:4]]),
            # sorted_list([Q2[0], Q2[2], Q4[1], Q4[3]]),
            # sorted_list([Q2[0], Q2[2], Q4[1], Q4[3]]),
            #
            # sorted_list([*Q3[0:2], *Q2[2:4]]),
            # sorted_list([*Q3[0:2], *Q4[2:4]]),
            # sorted_list([Q3[0], Q3[2], Q4[1], Q4[3]]),
            #
            # # уголок из 3-х и отстоящий угол от другого квадрата
            # sorted_list([*Q1[0:3], Q2[3]]),
            # sorted_list([*Q1[0:3], Q3[3]]),
            # sorted_list([*Q1[0:3], Q4[3]]),
            #
            # sorted_list([Q2[0], *Q2[2:4], Q1[1]]),
            # sorted_list([Q2[0], *Q2[2:4], Q3[1]]),
            # sorted_list([Q2[0], *Q2[2:4], Q4[1]]),
            #
            # sorted_list([*Q3[0:2], Q3[3], Q1[2]]),
            # sorted_list([*Q3[0:2], Q3[3], Q2[2]]),
            # sorted_list([*Q3[0:2], Q3[3], Q4[2]]),
            #
            # sorted_list([Q1[0], *Q4[1:4]]),
            # sorted_list([Q2[0], *Q4[1:4]]),
            # sorted_list([Q3[0], *Q4[1:4]]),
        ]

        print('resulting combs: ', len(combs))
        print(*combs, sep='\n')

        for objs in some_expected_combs:
            self.assertIn(objs, combs)

    def test_clash_6_grid_8x7_matches_2x2_shift(self):
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
        T = '''
        12345678
        AB_CDEFG
        HIJKLNMO
        PQRSTUVW
        ab9cdefg
        hijklnmo
        pqrstuvw
        '''.strip().replace(" ", '').splitlines()

        all_chars = [ch for line in T for ch in line]
        for ch in all_chars:
            if all_chars.count(ch) > 1:
                print(f"DUPLICATE OF CHAR: `{ch}`")
                assert False, ch

        W = 8
        H = 7
        D = 2

        def get(y, x) -> str:
            return ''.join(
                T[i][x:x + D]
                for i in range(y, y + D)
            )

        Q1 = [
            get(i, j)
            for i in range(0, H - D + 1, D)
            for j in range(0, W - D + 1, D)
        ]
        Q2 = [
            get(i, j)
            for i in range(0, H - D + 1, D)
            for j in range(1, W - D + 1, D)
        ]
        Q3 = [
            get(i, j)
            for i in range(1, H - D + 1, D)
            for j in range(0, W - D + 1, D)
        ]
        Q4 = [
            get(i, j)
            for i in range(1, H - D + 1, D)
            for j in range(1, W - D + 1, D)
        ]

        objs = Q1 + Q2 + Q3 + Q4

        combs = find_combinations_of_compatible_elements(objs, components_getter=trivial_components_getter)

        some_expected_combs = [
            sorted_list(Q1),
            sorted_list(Q2),
            sorted_list(Q3),
            sorted_list(Q4),
        ]

        print('resulting combs: ', len(combs))
        print(*combs, sep='\n')
        print('some expected combs: ', len(some_expected_combs))
        print(*some_expected_combs, sep='\n')


        for objs in some_expected_combs:
            self.assertIn(objs, combs)
        # self.assertEqual(, combs)

    def test_clash_7_line_1_shift(self):
        r"""
        Data, visually:

        0123456789ABCDEFGHIJKLNMOPQRSTUVWXYZ
        <><><><><><><><><><><><>
                   <><><><><><><><><><><><>
        """
        D = 2

        def chunks(s: str, D: int = D) -> list[str]:
            return [s[i:i+D] for i in range(0, len(s), D)]

        s1 = '0123456789ABCDEFGHIJKLNM'
        s2 = 'BCDEFGHIJKLNMOPQRSTUVWXY'

        objs = [
            *chunks(s1),
            *chunks(s2),
        ]

        combs = find_combinations_of_compatible_elements(objs, components_getter=trivial_components_getter)

        s1_free = '0123456789'
        s2_free = 'PQRSTUVWXY'

        some_expected_combs = [
            sorted_list([*chunks(s1), *chunks(s2_free)]),
            sorted_list([*chunks(s1_free), *chunks(s2)]),
        ]

        print('resulting combs: ', len(combs))
        print(*combs, sep='\n')

        for objs in some_expected_combs:
            self.assertIn(objs, combs)

    def test_clash_7_lines_per3(self):
        r"""
        Data, visually:

        0123456789ABCDEFGHIJKLNMOPQRSTUVWXYZ_+abcdefghi
        <–><–><–><–><–><–><•><•><•>
                  <–><–><–><•><•><•><–><–><–>
                            <•><•><•><–><–><–><–><–><–>
        """
        D = 3

        def chunks(s: str, D: int = D) -> list[str]:
            return [s[i:i+D] for i in range(0, len(s), D)]

        s1 = '0123456789ABCDEFGHIJKLNMOPQ'
        s2 = 'ABCDEFGHIJKLNMOPQRSTUVWXYZ_'
        s3 = 'KLNMOPQRSTUVWXYZ_+abcdefghi'

        objs = [
            *chunks(s1),
            *chunks(s2),
            *chunks(s3),
            # *chunks(s4),
        ]

        combs = find_combinations_of_compatible_elements(objs, components_getter=trivial_components_getter)

        s1_free2 = '012345678'
        s1_free3 = '0123456789ABCDEFGH'
        s2_free1 = 'STUVWXYZ_'
        s2_free3 = 'ABCDEFGHI'
        s3_free1 = 'TUVWXYZ_+abcdefghi'
        s3_free2 = 'abcdefghi'

        some_expected_combs = [
            # sorted_list([*chunks(s1), *chunks(s3_free1)]),
            sorted_list([*chunks(s1), *chunks(s2_free1), *chunks(s3_free2)]),
            sorted_list([*chunks(s1_free2), *chunks(s2), *chunks(s3_free2)]),
            # sorted_list([*chunks(s3), *chunks(s1_free3)]),
            sorted_list([*chunks(s3), *chunks(s2_free3), *chunks(s1_free2)]),
        ]

        print('resulting combs: ', len(combs))
        print(*combs, sep='\n')
        # print('expected combs: ', len(some_expected_combs))

        for objs in some_expected_combs:
            self.assertIn(objs, combs)

    def test_clash_8_8x8(self):

        # T = '''
        # 0 1 2 3 4 5 6 7 8
        # A ☺ ║ ═ ╗ 🂡 ☻ L ♥
        # B ╔ ▓ ▒ ╠ O X ♦ U
        # C * ┼ ▀ ♠ e a k ○
        # D R ─ s ♣ ╫ ⌂ ↨ <
        # E ▪ ▫ ▲ ▼ → • : ↓
        # F ♫ r b ⚐ ↑ _ ∟ ←
        # G > W ⚘ f N Y ! h
        # H ◘ o S / « … » ╜
        # '''.strip().replace(" ", '').splitlines()
        T = '''
        ! " # $ % & • (
        ) * + , - . / 0
        1 2 3 4 5 6 7 8
        9 : ; < = > ? @
        A B C D E F G H
        I J K L M N O P
        Q R S T U V W X
        Y Z [ | ] ^ _ ♣
        '''.strip().replace(" ", '').splitlines()

        all_chars = [ch for line in T for ch in line]
        for ch in all_chars:
            if all_chars.count(ch) > 1:
                print(f"DUPLICATE OF CHAR: `{ch}`")
                assert False, ch

        L = 8
        D = 2

        def get(y, x) -> str:
            return ''.join(
                T[i][x:x + D]
                for i in range(y, y + D)
            )

        objs = [
            get(i, j)
            for i in range(L - D + 1)
            for j in range(L - D + 1)
        ]

        combs = find_combinations_of_compatible_elements(objs, components_getter=trivial_components_getter)

        some_expected_combs = [
            sorted_list([
                get(i, j)
                for i in range(0, L - D + 1, D)
                for j in range(0, L - D + 1, D)
            ]),
            sorted_list([
                get(i, j)
                for i in range(1, L - D + 1, D)
                for j in range(0, L - D + 1, D)
            ]),
            sorted_list([
                get(i, j)
                for i in range(0, L - D + 1, D)
                for j in range(1, L - D + 1, D)
            ]),
            sorted_list([
                get(i, j)
                for i in range(1, L - D + 1, D)
                for j in range(1, L - D + 1, D)
            ]),
        ]

        print('resulting combs: ', len(combs))
        print(*combs, sep='\n')

        for objs in some_expected_combs:
            self.assertIn(objs, combs)


class ArrangementCase(unittest.TestCase):
    def test_arrangement_1(self):

        a = Arrangement.make(range(2))
        b = Arrangement.make(range(2, 10))
        u = Arrangement.make(range(10))

        self.assertEqual(b, a.select_candidates_from(u))
        self.assertEqual(a, b.select_candidates_from(u))
        self.assertEqual((True, set()), a.try_add_all(b))
        self.assertEqual(u, a)

    def test_arrangement_2(self):

        s = '12345678901'
        L = list(s[i:i + 3] for i in range(len(s) - 3 + 1))
        # print(L)  # ['123', '234', '345', '456', '567', '678', '789', '890', '901']

        u = ClashingElementSet.make(L, trivial_components_getter)
        fill_clashing_elements(u)
        su = list(sorted(u))

        # Adding all one by one...
        a = Arrangement()
        incompatible_with_a = su[1::3] + su[2::3]
        self.assertEqual((False, set(incompatible_with_a)), a.try_add_all(su))
        self.assertEqual(set(su[0::3]), a)

        # Adding all one by one...
        b = Arrangement()
        incompatible_with_b = su[2::3] + su[3::3]
        self.assertEqual((False, set(incompatible_with_b)), b.try_add_all(su[1:]))
        self.assertEqual(set(su[1::3]), b)

        neighbours_of_a = a.get_outer_neighbours()
        self.assertEqual(set(), neighbours_of_a)

        neighbours_of_b = b.get_outer_neighbours()
        self.assertEqual(set(), neighbours_of_b)

    def test_arrangement_3(self):

        # s = '1234567890x'
        # L = list(s[i:i + 3] for i in range(len(s) - 3 + 1))
        # print(L)
        L = ['123',  #  0
              '234', #  1
               '345',  # 2
                '456', # 3
                 '567',  # 4
                  '678', # 5
                   '789',  # 6
                    '890', # 7
                     '90x',# 8
             ]

        u = ClashingElementSet.make(L, trivial_components_getter)
        fill_clashing_elements(u)
        su = list(sorted(u))

        for el in su:
            assert all(
                other in el.data.globally_clashing
                for other in su
                if other != el and (set(el.obj) & set(other.obj))
            )

        # Adding some...
        a = Arrangement()
        self.assertEqual((True, set()), a.try_add_all(su[0::4]))
        self.assertEqual(set(su[0::4]), a)
        self.assertEqual(set(su) - set(su[0::4]), a.incompatible)

        # Adding some...
        b = Arrangement()
        self.assertEqual((True, set()), b.try_add_all(su[1::4]))
        self.assertEqual(set(su[1::4]), b)
        self.assertEqual(set(su[:-1]) - set(su[1::4]), b.incompatible)

        # Adding some...
        x = Arrangement()
        self.assertEqual((True, set()), x.try_add_all(su[2::4]))
        self.assertEqual(set(su[2::4]), x)
        self.assertEqual(set(su) - set(su[2::4]), x.incompatible)

        # Adding some...
        y = Arrangement()
        self.assertEqual((True, set()), y.try_add_all(su[3::4]))
        self.assertEqual(set(su[3::4]), y)
        self.assertEqual(set(su[1:]) - set(su[3::4]), y.incompatible)

        ### TODO
        neighbours_of_a = a.get_outer_neighbours()
        self.assertEqual(set(), neighbours_of_a)

        neighbours_of_b = b.get_outer_neighbours()
        self.assertEqual(set(su[-1:]), neighbours_of_b)

        neighbours_of_x = x.get_outer_neighbours()
        self.assertEqual(set(), neighbours_of_x)

        neighbours_of_y = y.get_outer_neighbours()
        self.assertEqual(set(su[:1]), neighbours_of_y)

        # self.assertEqual(set(), x - neighbours_of_a)
        #
        # neighbours_of_y = y.get_outer_neighbours()
        # self.assertNotEqual(set(), neighbours_of_y)
        # self.assertEqual(set(), b - y.select_neighbours_from(u))
        #
        # # self.assertEqual(u, neighbours_of_a | neighbours_of_b)


if __name__ == '__main__':
    unittest.main()
