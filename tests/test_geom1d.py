import math
import unittest

from tests_bootstrapper import init_testing_environment

init_testing_environment()

from geom1d import LinearSegment, LinearRelation


def get_relation(segment1, segment2) -> LinearRelation:
    # return LinearRelation(LinearSegment(segment1), LinearSegment(segment2))
    s1 = LinearSegment(*segment1)
    s2 = LinearSegment(*segment2)
    return LinearRelation(s1, s2)


def str_to_segment(s: str):
    return (
        s.find('a'),
        s.find('b'),
    )


def relation_from_two_strings(s1, s2) -> LinearRelation:
    return get_relation(
        str_to_segment(s1),
        str_to_segment(s2),
    )


class RelationTestCase(unittest.TestCase):

    ### Внутренние конфигурации ###

    def test_relation_eq(self):
        # self.assertEqual(True, False)  # add assertion here

        r = relation_from_two_strings(
            'a-----b',
            'a-----b',
        )
        self.assertEqual('совпадает с', r.description)
        self.assertEqual(6, r.s1.intersect(r.s2).size)

        r = relation_from_two_strings(
            'ab',
            'ab',
        )
        self.assertEqual('совпадает с', r.description)

    def test_relation_in(self):
        r = relation_from_two_strings(
            'a----------b',
            '  a-----b   ',
        )
        self.assertEqual('включает', r.description)  # охватывает (?)
        self.assertEqual(6, r.s1.intersect(r.s2).size)

        r = relation_from_two_strings(
            '  a-----b   ',
            'a----------b',
        )
        self.assertEqual('входит в', r.description)

    def test_relation_inner_touch(self):
        r = relation_from_two_strings(
            '     a-----b',
            'a----------b',
        )
        self.assertEqual('включается, примыкая справа, в', r.description)
        self.assertEqual(6, r.s1.intersect(r.s2).size)

        r = relation_from_two_strings(
            'a----------b',
            '     a-----b',
        )
        self.assertEqual('включает примыкающее справа', r.description)
        self.assertEqual(6, r.s1.intersect(r.s2).size)

        r = relation_from_two_strings(
            'a-----b     ',
            'a----------b',
        )
        self.assertEqual('включается, примыкая слева, в', r.description)
        self.assertEqual(6, r.s1.intersect(r.s2).size)

        r = relation_from_two_strings(
            'a----------b',
            'a-----b     ',
        )
        self.assertEqual('включает примыкающее слева', r.description)
        self.assertEqual(6, r.s1.intersect(r.s2).size)

        ### конфигурации перекрытия ###

    def test_relation_overlap(self):
        r = relation_from_two_strings(
            'a----------b    ',
            '         a-----b',
        )
        self.assertEqual('пересекается с', r.description)
        self.assertEqual(2, r.s1.intersect(r.s2).size)

        r = relation_from_two_strings(
            '         a-----b',
            'a----------b    ',
        )
        self.assertEqual('пересекается с', r.description)
        self.assertEqual(2, r.s1.intersect(r.s2).size)

        ### Наружные конфигурации ###

    def test_relation_far1(self):
        r = relation_from_two_strings(
            'a-----b           ',
            '           a-----b',
        )
        self.assertEqual('на удалении слева от', r.description)

    def test_relation_far2(self):
        r = relation_from_two_strings(
            '           a-----b',
            'a-----b           ',
        )
        self.assertEqual('на удалении справа от', r.description)

    def test_relation_outer_touch(self):
        r = relation_from_two_strings(
            '      a-----b',
            'a-----b      ',
        )
        self.assertEqual('примыкает справа к', r.description)
        self.assertEqual(0, r.s1.intersect(r.s2).size)

        r = relation_from_two_strings(
            'a-----b      ',
            '      a-----b',
        )
        self.assertEqual('примыкает слева к', r.description)
        self.assertEqual(0, r.s1.intersect(r.s2).size)


class LinearSegmentTestCase(unittest.TestCase):
    def test_ints(self):
        LS = LinearSegment
        s = LS(1, 1)
        self.assertIn(1, s)
        self.assertNotIn(0, s)
        self.assertNotIn(2, s)

        s = LS(-1, 10)
        self.assertIn(1, s)
        self.assertIn(-1, s)
        self.assertNotIn(-2, s)
        self.assertIn(9, s)
        self.assertIn(10, s)
        self.assertNotIn(11, s)

    def test_inf(self):
        LS = LinearSegment
        s = LS(1, math.inf)
        self.assertNotIn(-10, s)
        self.assertNotIn(0, s)
        self.assertIn(1, s)
        self.assertIn(2, s)
        self.assertIn(999999, s)

        s = LS(-math.inf, 10)
        self.assertIn(-999999, s)
        self.assertIn(-1, s)
        self.assertIn(0, s)
        self.assertIn(1, s)
        self.assertIn(9, s)
        self.assertIn(10, s)
        self.assertNotIn(11, s)
        self.assertNotIn(15, s)


if __name__ == '__main__':
    unittest.main()
