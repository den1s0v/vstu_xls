import unittest
from geom2d import LinearSegment, LinearRelation
from geom2d import Box


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

        r = relation_from_two_strings(
            'a----------b',
            '     a-----b',
        )
        self.assertEqual('включает примыкающее справа', r.description)

        r = relation_from_two_strings(
            'a-----b     ',
            'a----------b',
        )
        self.assertEqual('включается, примыкая слева, в', r.description)

        r = relation_from_two_strings(
            'a----------b',
            'a-----b     ',
        )
        self.assertEqual('включает примыкающее слева', r.description)

        ### конфигурации перекрытия ###

    def test_relation_overlap(self):
        r = relation_from_two_strings(
            'a----------b    ',
            '         a-----b',
        )
        self.assertEqual('пересекается с', r.description)

        r = relation_from_two_strings(
            '         a-----b',
            'a----------b    ',
        )
        self.assertEqual('пересекается с', r.description)

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

        r = relation_from_two_strings(
            'a-----b      ',
            '      a-----b',
        )
        self.assertEqual('примыкает слева к', r.description)


class BoxTestCase(unittest.TestCase):
    def test_in_1(self):
        b = Box(10, 20, 3, 4)
        r = Box(10, 20, 3, 4)

        self.assertTrue(r in b)  # add assertion here

    def test_in_2(self):
        b = Box(10, 20, 3, 4)
        r = Box(11, 21, 2, 3)

        self.assertTrue(r in b)  # add assertion here

    def test_in_3(self):
        b = Box(10, 20, 3, 4)
        r = Box(10, 20, 2, 3)

        self.assertTrue(r in b)  # add assertion here

    def test_overlaps_1(self):
        b = Box(10, 20, 3, 4)
        r = Box(11, 21, 2, 3)

        self.assertTrue(b.overlaps(r))  # add assertion here




if __name__ == '__main__':
    unittest.main()
