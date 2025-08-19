import unittest

from geom1d import LinearSegment
from tests_bootstrapper import init_testing_environment

init_testing_environment()

from geom2d import Box, ManhattanDistance, Point, VariBox, PartialBox, RangedBox
from geom2d import parse_range, parse_size_range
from geom2d import open_range, RangedSegment


class BoxTestCase(unittest.TestCase):
    def test_in_1(self):
        b = Box(10, 20, 3, 4)
        r = Box(10, 20, 3, 4)

        self.assertIn(r, b)
        self.assertIn(b, r)

    def test_in_2(self):
        b = Box(10, 20, 3, 4)
        r = Box(11, 21, 2, 3)

        self.assertIn(r, b)
        self.assertNotIn(b, r)

    def test_in_3(self):
        b = Box(10, 20, 3, 4)
        r = Box(10, 20, 2, 3)

        self.assertIn(r, b)
        self.assertNotIn(b, r)

    def test_overlaps_1(self):
        b = Box(10, 20, 3, 4)
        r = Box(11, 21, 2, 3)

        self.assertTrue(b.overlaps(r))
        self.assertTrue(r.overlaps(b))

    def test_overlaps_2(self):
        b = Box(10, 20, 3, 4)
        r = Box(11, 21, 4, 4)

        self.assertTrue(b.overlaps(r))
        self.assertTrue(r.overlaps(b))

    def test_point_dist_0(self):
        # triangle: 2 * (3, 4, 5)
        a = Point(-4, -3)
        b = Point(4, 3)

        self.assertEqual(b.distance_to(a), 2 * 5)
        self.assertEqual(b.manhattan_distance_to(a), 2 * 7)

    def test_box_dist_1(self):
        # triangle: 2 * (3, 4, 5)
        a = Box(-4, -3, 1, 1)
        b = Box(4, 3, 1, 1)

        self.assertEqual(b.manhattan_distance_to_overlap(a), 2 * 7)
        self.assertEqual(b.manhattan_distance_to_touch(a), 2 * 7 - 2)
        self.assertEqual(b.manhattan_distance_to_contact(a), 2 * 7 - 1)

    def test_box_dist_2(self):
        a = Box(4, 1, 1, 1)
        b = Box(4, 3, 1, 1)

        self.assertEqual(b.manhattan_distance_to_overlap(a), 2)
        self.assertEqual(b.manhattan_distance_to_touch(a), 1)
        self.assertEqual(b.manhattan_distance_to_contact(a), 1)

    def test_box_dist_3(self):
        # inside
        a = Box(-4, -3, 10, 10)
        b = Box(4, 3, 1, 1)

        self.assertEqual(b.manhattan_distance_to_overlap(a), 0)
        self.assertEqual(b.manhattan_distance_to_touch(a), 0)
        self.assertEqual(b.manhattan_distance_to_contact(a), 0)

    def test_box_dist_4(self):
        # overlaps and (1, 1) is outside
        a = Box(-4, -3, 10, 10)
        b = Box(4, 3, 3, 5)

        self.assertEqual(b.manhattan_distance_to_overlap(a), 1 + 1)

        self.assertEqual(b.manhattan_distance_to_touch(a), 0)
        self.assertEqual(b.manhattan_distance_to_contact(a), 1)

    def test_box_dist_5(self):
        # overlaps and (1, 1) is outside
        a = Box(-4, -3, 10, 10)
        b = Box(4, 3, 3, 5)

        self.assertEqual(b.manhattan_distance_to_overlap(a, True), (1, 1))

        self.assertEqual(b.manhattan_distance_to_touch(a, True), (0, 0))
        self.assertEqual(b.manhattan_distance_to_contact(a, True), (0, 1))

    def test_box_dist_6(self):
        # triangle: 2 * (3, 4, 5)
        a = Box(-4, -3, 1, 1)
        b = Box(4, 3, 1, 1)

        self.assertEqual(b.manhattan_distance_to_overlap(a, True), 2 * 7)
        self.assertEqual(b.manhattan_distance_to_overlap(a, True), (8, 6))
        # equals to sum
        self.assertEqual(b.manhattan_distance_to_touch(a, True), 2 * 7 - 2)
        self.assertEqual(b.manhattan_distance_to_touch(a, True), ManhattanDistance(7, 5))

    def test_box_dist_7(self):
        # gap: 4 * 3
        a = Box(-10, -10, 10, 10)
        b = Box(4, 3, 8, 8)

        self.assertEqual(b.manhattan_distance_to_overlap(a), 7 + 8 * 2)
        self.assertEqual(b.manhattan_distance_to_overlap(a, True), (12, 11))
        self.assertEqual(b.manhattan_distance_to_touch(a), 7)
        self.assertEqual(b.manhattan_distance_to_contact(a), 7 + 8)

    def test_intersect_overlap(self):
        a = Box.from_2points(0, 0, 10, 10)
        b = Box.from_2points(5, 5, 15, 15)
        r = Box.from_2points(5, 5, 10, 10)

        self.assertEqual(r, a.intersect(b))
        self.assertEqual(r, b.intersect(a))

    def test_intersect_inside(self):
        a = Box.from_2points(0, 0, 15, 15)
        b = Box.from_2points(5, 5, 10, 10)
        r = Box.from_2points(5, 5, 10, 10)

        self.assertEqual(r, a.intersect(b))
        self.assertEqual(r, b.intersect(a))

    def test_intersect_none(self):
        a = Box.from_2points(0, 0, 5, 5)
        b = Box.from_2points(10, 10, 15, 15)

        self.assertEqual(None, a.intersect(b))
        self.assertEqual(None, b.intersect(a))

    def test_unite_overlap(self):
        a = Box.from_2points(0, 0, 10, 10)
        b = Box.from_2points(5, 5, 15, 15)
        r = Box.from_2points(0, 0, 15, 15)

        self.assertEqual(r, a.unite(b))
        self.assertEqual(r, b.unite(a))

    def test_unite_inside(self):
        a = Box.from_2points(0, 0, 15, 15)
        b = Box.from_2points(5, 5, 10, 10)
        r = Box.from_2points(0, 0, 15, 15)

        self.assertEqual(r, a.unite(b))
        self.assertEqual(r, b.unite(a))

    def test_unite_sparse(self):
        a = Box.from_2points(0, 0, 5, 5)
        b = Box.from_2points(10, 10, 15, 15)
        r = Box.from_2points(0, 0, 15, 15)

        self.assertEqual(r, a.unite(b))
        self.assertEqual(r, b.unite(a))

    def test_sort(self):
        a = Box.from_2points(0, 0, 5, 5)
        b = Box.from_2points(10, 10, 15, 15)
        r = Box.from_2points(0, 0, 15, 15)

        L = [a, b, r]
        L.sort()
        self.assertEqual([a, r, b], L)
        L.sort(reverse=True)
        self.assertEqual([b, r, a], L)


class VariBoxTestCase(unittest.TestCase):
    def test_in_1(self):
        b = VariBox(10, 20, 15, 4)
        r = VariBox(10, 20, 15, 4)

        self.assertIn(r, b)
        self.assertIn(b, r)

        b.x = 15
        self.assertEqual(15, b.left)

        r.left = 15
        r.w += 5
        self.assertEqual(b, r)

        r.w -= 5
        r.right = 30
        self.assertEqual(b, r)


class PartialBoxTestCase(unittest.TestCase):
    def test_ordinary(self):
        b = PartialBox(10, 20, 15, 4)
        r = PartialBox(10, 20, 15, 4)

        self.assertEqual(b, r)
        self.assertDictEqual({'left': 10, 'top': 20, 'w': 15, 'h': 4, 'right': 25, 'bottom': 24}, b.as_dict())

        self.assertIn(r, b)
        self.assertIn(b, r)

    def test_eq(self):
        b = PartialBox(10, 20, 15, 4)

        r = Box(10, 20, 15, 4)
        self.assertEqual(b, r)

        r = tuple((10, 20, 15, 4))
        self.assertEqual(b, r)

        r = VariBox(10, 20, 15, 4)
        self.assertEqual(b, r)

    def test_partially_filled(self):
        b = PartialBox()

        self.assertDictEqual({}, b.as_dict())

        b.bottom = 24
        self.assertDictEqual({'bottom': 24}, b.as_dict())

        b.h = 4  # infers `top`
        self.assertDictEqual({'top': 20, 'h': 4, 'bottom': 24}, b.as_dict())

        b.x = 10
        self.assertDictEqual({'left': 10, 'top': 20, 'h': 4, 'bottom': 24}, b.as_dict())

        b.right = 25  # infers `w`
        self.assertDictEqual({'left': 10, 'top': 20, 'w': 15, 'h': 4, 'right': 25, 'bottom': 24}, b.as_dict())

        r = Box(10, 20, 15, 4)
        self.assertEqual(b, r)

    def test_set_same(self):
        b = PartialBox(10, 20, 15, 4)

        b.x = 10

        r = PartialBox(10, 20, 15, 4)
        self.assertEqual(b, r)

    def test_set_different(self):
        b = PartialBox(10, 20, 15, 4)

        with self.assertRaises(ValueError):
            b.x = 15

    def test_set_invalid(self):
        b = PartialBox(10, 20, 15, 4)

        with self.assertRaises(AssertionError):
            b.h = -1  # negative

        with self.assertRaises(AssertionError):
            b.h = None

        with self.assertRaises(AssertionError):
            b.bottom = None


class RangeTestCase(unittest.TestCase):

    def test_open_range(self):
        self.assertNotIn(-1, range(0, 5))
        self.assertIn(0, range(0, 5))
        self.assertIn(4, range(0, 5))
        self.assertNotIn(5, range(0, 5))

        self.assertNotIn(-1, open_range(0, 5))
        self.assertIn(0, open_range(0, 5))
        self.assertIn(5, open_range(0, 5))
        self.assertNotIn(6, open_range(0, 5))

        self.assertNotIn(0, open_range(1, 1))
        self.assertIn(1, open_range(1, 1))
        self.assertNotIn(2, open_range(1, 1))

        self.assertNotIn(-1, open_range(0, None))
        self.assertIn(0, open_range(0, None))
        self.assertIn(1, open_range(0, None))
        self.assertIn(999, open_range(0, None))

        self.assertNotIn(6, open_range(None, 5))
        self.assertIn(5, open_range(None, 5))
        self.assertIn(4, open_range(None, 5))
        self.assertIn(-999, open_range(None, 5))

        self.assertIn(999, open_range(None, None))
        self.assertIn(4, open_range(None, None))
        self.assertIn(-999, open_range(None, None))

        # neg
        self.assertEqual(open_range(-10, -2), -open_range(2, 10))
        self.assertEqual(open_range(None, -2), -open_range(2, None))
        self.assertEqual(open_range(5, None), -open_range(None, -5))
        self.assertEqual(open_range(None, None), -open_range(None, None))

        # sum
        self.assertEqual(open_range(None, None), 11 + open_range(None, None))
        self.assertEqual(open_range(32, None), 11 + open_range(21, None))
        self.assertEqual(open_range(None, 12), 11 + open_range(None, 1))
        self.assertEqual(open_range(25, 32), 11 + open_range(14, 21))

        # range + range
        self.assertEqual(open_range(8, 12), open_range(4, 6) + open_range(4, 6))
        self.assertEqual(open_range(8, None), open_range(4, 6) + open_range(4, None))

        # sub
        self.assertEqual(open_range(None, None), open_range(None, None) - 5)
        self.assertEqual(open_range(10, None), open_range(15, None) - 5)
        self.assertEqual(open_range(None, -10), open_range(None, -5) - 5)
        self.assertEqual(open_range(3, 10), open_range(8, 15) - 5)

        # range - range
        self.assertEqual(open_range(-12, 0), open_range(0, 6) - open_range(6, 12))
        self.assertEqual(open_range(16, 28), open_range(20, 30) - open_range(2, 4))
        self.assertEqual(open_range(None, 28), open_range(20, 30) - open_range(2, None))

    def test_open_range_parsed(self):
        self.assertEqual(range(1, 1 + 1), open_range(1, 1))
        self.assertEqual(range(1, 1 + 1), open_range.parse('1, 1'))

    def test_parse_range(self):

        expr = '1'
        self.assertEqual(range(1, 1 + 1), parse_range(expr))

        expr = '9'
        self.assertEqual(range(9, 9 + 1), parse_range(expr))

        expr = '194'
        self.assertEqual(range(194, 194 + 1), parse_range(expr))

        expr = '0+'
        self.assertEqual(open_range(0, None), parse_range(expr))

        expr = '0-'
        self.assertEqual(open_range(None, 0), parse_range(expr))

        expr = '3'
        self.assertEqual(range(3, 3 + 1), parse_range(expr))

        expr = '+3'
        self.assertEqual(range(3, 3 + 1), parse_range(expr))

        expr = '3+'
        self.assertEqual(open_range(3, None), parse_range(expr))

        expr = '+3+'
        self.assertEqual(open_range(3, None), parse_range(expr))

        expr = '3-'
        self.assertEqual(open_range(None, 3), parse_range(expr))

        expr = ' * '
        self.assertEqual(open_range(None, None), parse_range(expr))

        expr = '3..5'
        self.assertEqual(range(3, 5 + 1), parse_range(expr))

        expr = '3, 5'
        self.assertEqual(range(3, 5 + 1), parse_range(expr))

        expr = '-3'
        self.assertEqual(range(-3, -3 + 1), parse_range(expr))

        expr = '-3+'
        self.assertEqual(open_range(-3, None), parse_range(expr))

        expr = '-3-'
        self.assertEqual(open_range(None, -3), parse_range(expr))

        expr = '-5..-3'
        self.assertEqual(range(-5, -3 + 1), parse_range(expr))

        expr = '-5 ... -3'
        self.assertEqual(range(-5, -3 + 1), parse_range(expr))

        expr = '-5, -3'
        self.assertEqual(range(-5, -3 + 1), parse_range(expr))

        expr = '-5, *'
        self.assertEqual(open_range(-5, None), parse_range(expr))

        expr = '-5 .. *'
        self.assertEqual(open_range(-5, None), parse_range(expr))

        expr = '* .. 5'
        self.assertEqual(open_range(None, 5), parse_range(expr))

        expr = '* .. *'
        self.assertEqual(open_range(None, None), parse_range(expr))

    def test_parse_size_range(self):

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
            open_range(8, None),
            range(1, 1 + 1)),
            parse_size_range(expr))

        expr = '4+ x 1..2'
        self.assertEqual((
            open_range(4, None),
            range(1, 2 + 1)),
            parse_size_range(expr))

        expr = '5- x 59+'
        self.assertEqual((
            open_range(None, 5),
            open_range(59, None)),
            parse_size_range(expr))

        expr = '1 x 1'
        self.assertEqual((
            range(1, 1 + 1),
            range(1, 1 + 1)),
            parse_size_range(expr))

        expr = '5+ x 4'
        self.assertEqual((
            open_range(5, None),
            range(4, 4 + 1)),
            parse_size_range(expr))

        expr = '1..4 x 2+'
        self.assertEqual((
            range(1, 4 + 1),
            open_range(2, None)),
            parse_size_range(expr))

    @unittest.expectedFailure
    def test_size_range_empty_error1(self):
        """ Reversed range """
        expr = '-5, -8'
        parse_range(expr)

    @unittest.expectedFailure
    def test_size_range_empty_error2(self):
        """ Reversed range """
        expr = '-5000, -5001'
        parse_range(expr)

    def test_point(self):
        self.assertTrue(open_range(1, 1).is_point())

        self.assertEqual(1, open_range(1, 1).point())
        self.assertIsNone(open_range(1, 2).point())

        self.assertFalse(open_range(1, 1).is_open())
        self.assertTrue(open_range(None, 1).is_open())
        self.assertTrue(open_range(1, None).is_open())
        self.assertTrue(open_range(None, None).is_open())

    def test_intersect(self):
        self.assertEqual(open_range(1, 1),
                         open_range(1, 1).intersect(open_range(1, 1)))
        self.assertEqual(open_range(1, 2),
                         open_range(1, 2).intersect(open_range(1, 2)))

        self.assertEqual(open_range(1, 1),
                         open_range(1, 2).intersect(open_range(0, 1)))
        self.assertEqual(open_range(1, 1),
                         open_range(0, 2).intersect(open_range(1, 1)))

        self.assertEqual(open_range(1, 1),
                         open_range(1, None).intersect(open_range(0, 1)))
        self.assertEqual(open_range(1, 1),
                         open_range(1, 2).intersect(open_range(None, 1)))
        self.assertEqual(open_range(1, 1),
                         open_range(None, None).intersect(open_range(1, 1)))
        # ← →
        self.assertEqual(None,
                         open_range(1, 2).intersect(open_range(3, 4)))
        self.assertEqual(None,
                         open_range(None, 2).intersect(open_range(3, None)))
        self.assertEqual(None,
                         open_range(1, None).intersect(open_range(None, -1)))
        # →←
        self.assertEqual(open_range(1, 1),
                         open_range(1, None).intersect(open_range(None, 1)))
        self.assertEqual(open_range(1, 10),
                         open_range(1, None).intersect(open_range(None, 10)))

        self.assertEqual(open_range(None, None),
                         open_range(None, None).intersect(open_range(None, None)))

        self.assertEqual(open_range(50, 60),
                         open_range(40, 60).intersect(open_range(50, None)))

    def test_union(self):
        self.assertEqual(open_range(1, 1),
                         open_range(1, 1).union(open_range(1, 1)))
        self.assertEqual(open_range(1, 2),
                         open_range(1, 2).union(open_range(1, 2)))

        self.assertEqual(open_range(0, 2),
                         open_range(1, 2).union(open_range(0, 1)))
        self.assertEqual(open_range(0, 2),
                         open_range(0, 2).union(open_range(1, 1)))

        self.assertEqual(open_range(0, None),
                         open_range(1, None).union(open_range(0, 1)))
        self.assertEqual(open_range(None, 2),
                         open_range(1, 2).union(open_range(None, 1)))
        self.assertEqual(open_range(None, None),
                         open_range(None, None).union(open_range(1, 1)))
        # ← →
        self.assertEqual(open_range(1, 4),
                         open_range(1, 2).union(open_range(3, 4)))
        self.assertEqual(open_range(None, None),
                         open_range(None, 2).union(open_range(3, None)))
        self.assertEqual(open_range(None, None),
                         open_range(1, None).union(open_range(None, -1)))
        # →←
        self.assertEqual(open_range(None, None),
                         open_range(1, None).union(open_range(None, 1)))
        self.assertEqual(open_range(None, None),
                         open_range(1, None).union(open_range(None, 10)))

        self.assertEqual(open_range(None, None),
                         open_range(None, None).union(open_range(None, None)))

    def test_strict_union(self):
        self.assertEqual(open_range(1, 1),
                         open_range(1, 1).strict_union(open_range(1, 1)))
        self.assertEqual(open_range(1, 2),
                         open_range(1, 2).strict_union(open_range(1, 2)))

        self.assertEqual(open_range(0, 2),
                         open_range(1, 2).strict_union(open_range(0, 1)))
        self.assertEqual(open_range(0, 2),
                         open_range(0, 2).strict_union(open_range(1, 1)))

        self.assertEqual(open_range(0, None),
                         open_range(1, None).strict_union(open_range(0, 1)))
        self.assertEqual(open_range(None, 2),
                         open_range(1, 2).strict_union(open_range(None, 1)))
        self.assertEqual(open_range(None, None),
                         open_range(None, None).strict_union(open_range(1, 1)))
        # ← → TODO !!!!!!!!!!
        self.assertEqual(None, # open_range(1, 4),
                         open_range(1, 2).strict_union(open_range(3, 4)))
        self.assertEqual(None, # open_range(None, None),
                         open_range(None, 2).strict_union(open_range(3, None)))
        self.assertEqual(None, # open_range(None, None),
                         open_range(1, None).strict_union(open_range(None, -1)))
        # →←
        self.assertEqual(open_range(None, None),
                         open_range(1, None).strict_union(open_range(None, 1)))
        self.assertEqual(open_range(None, None),
                         open_range(1, None).strict_union(open_range(None, 10)))

        self.assertEqual(open_range(None, None),
                         open_range(None, None).strict_union(open_range(None, None)))

    def test_union_limited(self):
        self.assertEqual(open_range(1, 1),
                         open_range(1, 1).union_limited(open_range(1, 1)))
        self.assertEqual(open_range(1, 2),
                         open_range(1, 2).union_limited(open_range(1, 2)))

        self.assertEqual(open_range(0, 2),
                         open_range(1, 2).union_limited(open_range(0, 1)))
        self.assertEqual(open_range(0, 2),
                         open_range(0, 2).union_limited(open_range(1, 1)))

        self.assertEqual(open_range(0, 1),
                         open_range(1, None).union_limited(open_range(0, 1)))
        self.assertEqual(open_range(1, 2),
                         open_range(1, 2).union_limited(open_range(None, 1)))
        self.assertEqual(open_range(1, 1),
                         open_range(None, None).union_limited(open_range(1, 1)))
        # ← →
        self.assertEqual(open_range(1, 4),
                         open_range(1, 2).union_limited(open_range(3, 4)))
        self.assertEqual(None,
                         open_range(None, 2).union_limited(open_range(3, None)))
        self.assertEqual(None,
                         open_range(1, None).union_limited(open_range(None, -1)))
        # →←
        self.assertEqual(open_range(1, 1),
                         open_range(1, None).union_limited(open_range(None, 1)))
        self.assertEqual(open_range(1, 10),
                         open_range(1, None).union_limited(open_range(None, 10)))

        self.assertEqual(open_range(None, None),
                         open_range(None, None).union_limited(open_range(None, None)))


class RangedSegmentTestCase(unittest.TestCase):

    def test_init(self):
        rs = RangedSegment((0, 5), (15, 20))
        self.assertEqual(open_range(0, 5), rs.a)
        self.assertEqual(open_range(15, 20), rs.b)

        rs = RangedSegment((0, 5), (5, 10))
        self.assertEqual(open_range(0, 5), rs.a)
        self.assertEqual(open_range(5, 10), rs.b)

        rs = RangedSegment((0, None), (5, 10), validate=True)
        self.assertEqual(open_range(0, 5), rs.a)
        self.assertEqual(open_range(5, 10), rs.b)
        rs.minimal_range()  # No exception.

        rs = RangedSegment((0, 5), (None, 10), validate=True)
        self.assertEqual(open_range(0, 5), rs.a)
        self.assertEqual(open_range(5, 10), rs.b)
        rs.minimal_range()  # No exception.

        rs = RangedSegment((0, 5), (None, None), validate=True)
        self.assertEqual(open_range(0, 5), rs.a)
        self.assertEqual(open_range(None, None), rs.b)
        rs.minimal_range()  # No exception.

        rs = RangedSegment((None, 5), (None, None), validate=True)
        self.assertEqual(open_range(None, 5), rs.a)
        self.assertEqual(open_range(None, None), rs.b)
        rs.minimal_range()  # No exception.

        # No clamping ↓
        rs = RangedSegment((None, None), (None, None))
        self.assertEqual(open_range(None, None), rs.a)
        self.assertEqual(open_range(None, None), rs.b)
        rs.minimal_range()  # No exception.

    @unittest.expectedFailure
    def test_detect_invalid_range_1(self):
        rs = RangedSegment((20, 25), (5, 10), validate=True)

    @unittest.expectedFailure
    def test_detect_invalid_range_2(self):
        rs = RangedSegment((20, 20), (19, 19), validate=True)

    def test_point(self):
        rs = RangedSegment(5, 5)

        self.assertFalse(rs.is_open())
        self.assertTrue(rs.is_deterministic())
        self.assertTrue(rs.a.is_point())
        self.assertTrue(rs.b.is_point())
        self.assertEqual(5, rs.a.point())
        self.assertEqual(5, rs.b.point())

        self.assertNotIn(4, rs.minimal_range())
        self.assertIn(5, rs.minimal_range())
        self.assertNotIn(6, rs.minimal_range())

        self.assertNotIn(4, rs.maximal_range())
        self.assertIn(5, rs.maximal_range())
        self.assertNotIn(6, rs.maximal_range())

    def test_finite(self):
        rs = RangedSegment((0, 5), (10, 15))

        self.assertFalse(rs.is_open())
        self.assertFalse(rs.is_deterministic())
        self.assertFalse(rs.a.is_point())
        self.assertFalse(rs.b.is_point())
        self.assertIsNone(rs.a.point())
        self.assertIsNone(rs.b.point())

        self.assertNotIn(4, rs.minimal_range())
        self.assertIn(5, rs.minimal_range())
        self.assertIn(10, rs.minimal_range())
        self.assertNotIn(11, rs.minimal_range())

        self.assertNotIn(-1, rs.maximal_range())
        self.assertIn(0, rs.maximal_range())
        self.assertIn(15, rs.maximal_range())
        self.assertNotIn(16, rs.maximal_range())

    def test_infinite(self):
        rs = RangedSegment((5, 5), (10, None))

        self.assertTrue(rs.is_open())
        self.assertFalse(rs.is_deterministic())
        self.assertTrue(rs.a.is_point())
        self.assertFalse(rs.b.is_point())
        self.assertIsNotNone(rs.a.point())
        self.assertIsNone(rs.b.point())

        self.assertNotIn(4, rs.minimal_range())
        self.assertIn(5, rs.minimal_range())
        self.assertIn(10, rs.minimal_range())
        self.assertNotIn(11, rs.minimal_range())

        self.assertNotIn(4, rs.maximal_range())
        self.assertIn(5, rs.maximal_range())
        self.assertIn(10, rs.maximal_range())
        self.assertIn(15, rs.maximal_range())
        self.assertIn(9999, rs.maximal_range())

    def test_intersect_union_combine(self):
        r1 = RangedSegment((5, 5), (15, 15))
        r2 = RangedSegment((10, 10), (20, 20))

        self.assertEqual(RangedSegment((10, 10), (15, 15)), r1.intersect(r2))
        self.assertEqual(RangedSegment((5, 5), (20, 20)), r1.union(r2))
        self.assertEqual(RangedSegment((10, 10), (15, 15)), r1.combine(r2))

        r1 = RangedSegment((0, 5), (15, 20))
        r2 = RangedSegment((5, 10), (20, 25))

        self.assertEqual(RangedSegment((5, 10), (15, 20)), r1.intersect(r2))
        self.assertEqual(RangedSegment((0, 5), (20, 25)), r1.union(r2))
        self.assertEqual(RangedSegment((5, 5), (20, 20)), r1.combine(r2))

        r1 = RangedSegment((0, 0), (0, 0))
        r2 = RangedSegment((0, 0), (0, 0))

        self.assertEqual(RangedSegment((0, 0), (0, 0)), r1.intersect(r2))
        self.assertEqual(RangedSegment((0, 0), (0, 0)), r1.union(r2))
        self.assertEqual(RangedSegment((0, 0), (0, 0)), r1.combine(r2))

        r1 = RangedSegment((0, 0), (0, 0))
        r2 = RangedSegment((None, None), (None, None))

        self.assertEqual(RangedSegment((0, 0), (0, 0)), r1.intersect(r2))
        self.assertEqual(RangedSegment((None, None), (None, None)), r1.union(r2))
        self.assertEqual(RangedSegment((0, 0), (0, 0)), r1.combine(r2))

        r1 = RangedSegment((0, 0), (0, 0))
        r2 = RangedSegment((22, 22), (22, 22))

        self.assertEqual(None, r1.intersect(r2))
        self.assertEqual(RangedSegment((0, 0), (22, 22)), r1.union(r2))
        self.assertEqual(None, r1.combine(r2))

        r1 = RangedSegment((None, 0), (0, 0))
        r2 = RangedSegment((22, 22), (22, None))

        self.assertEqual(None, r1.intersect(r2))
        self.assertEqual(RangedSegment((None, 0), (22, None)), r1.union(r2))
        self.assertEqual(None, r1.combine(r2))

        r1 = RangedSegment((None, None), (None, None))
        r2 = RangedSegment((None, None), (None, None))

        self.assertEqual(RangedSegment((None, None), (None, None)), r1.intersect(r2))
        self.assertEqual(RangedSegment((None, None), (None, None)), r1.union(r2))
        self.assertEqual(RangedSegment((None, None), (None, None)), r1.combine(r2))

    def test_intersect_union_combine_2(self):
        r1 = RangedSegment((0, 0), (0, None))
        r2 = RangedSegment((None, 22), (22, 22))

        self.assertEqual(None, r1.intersect(r2))
        self.assertEqual(RangedSegment((None, 0), (22, None)), r1.union(r2))
        self.assertEqual(RangedSegment((0, 0), (22, 22)), r1.combine(r2))

        r1 = RangedSegment((0, 0), (11, None))
        r2 = RangedSegment((None, 11), (22, 22))

        self.assertEqual(RangedSegment((0, 11), (11, 22)), r1.intersect(r2))
        self.assertEqual(RangedSegment((None, 0), (22, None)), r1.union(r2))
        self.assertEqual(RangedSegment((0, 0), (22, 22)), r1.combine(r2))

    def test_intersect_union_combine_3(self):
        r1 = RangedSegment((30, 40), (60, 70))
        r2 = RangedSegment((50, 50), (None, None),
                           # validate=False
                           )

        self.assertEqual(
                RangedSegment((50, 50), (60, 70)),
            r1.intersect(r2))
        self.assertEqual(
                RangedSegment((30, 40), (None, None)),
            r1.union(r2))
        self.assertEqual(
                RangedSegment((50, 50), (60, 70)),
            r1.combine(r2))

    def test_intersect_union_combine_4(self):
        r1 = RangedSegment((3, 3), (4, 4))
        r2 = RangedSegment((None, 1), (2, None))

        self.assertEqual(
                None,
            r1.intersect(r2))
        self.assertEqual(
                RangedSegment((None, 1), (4, None)),
            r1.union(r2))
        self.assertEqual(
                RangedSegment((3, 3), (4, 4)),
            r1.combine(r2))

    def test_restricted_by_size_1(self):
        r1 = RangedSegment((3, 4), (6, 7))

        self.assertEqual(r1,
            r1.restricted_by_size(open_range(0, 3)))
        self.assertEqual(r1,
            r1.restricted_by_size(open_range(3, 3)))
        self.assertEqual(RangedSegment((4, 4), (6, 6)),
            r1.restricted_by_size(open_range(2, 2)))
        self.assertEqual(RangedSegment((3, 3), (7, 7)),
            r1.restricted_by_size(open_range(4, 4)))

        r2 = RangedSegment((0, 5), (100, 110))

        self.assertEqual(r2,
            r2.restricted_by_size(open_range(100, 105)))

        self.assertEqual(RangedSegment((0, 5), (100, 105)),
            r2.restricted_by_size(open_range(100, 100)))

        self.assertEqual(RangedSegment((0, 5), (105, 110)),
            r2.restricted_by_size(open_range(105, 105)))

        self.assertEqual(RangedSegment((2, 5), (100, 103)),
            r2.restricted_by_size(open_range(98, 98)))

        self.assertEqual(RangedSegment((0, 3), (107, 110)),
            r2.restricted_by_size(open_range(107, 107)))

        self.assertEqual(RangedSegment((0, 0), (110, 110)),
            r2.restricted_by_size(open_range(110, 110)))

        self.assertEqual(RangedSegment((5, 5), (100, 100)),
            r2.restricted_by_size(open_range(95, 95)))

        self.assertEqual(None,
            r2.restricted_by_size(open_range(None, 94)))

        self.assertEqual(None,
            r2.restricted_by_size(open_range(111, None)))

        r3 = RangedSegment((None, 10), (100, None))

        self.assertEqual(r3,
            r3.restricted_by_size(open_range(90, None)))

        self.assertEqual(r3,
            r3.restricted_by_size(open_range(180, None)))

        self.assertEqual(RangedSegment((0, 10), (100, 110)),
            r3.restricted_by_size(open_range(100, 100)))

        self.assertEqual(RangedSegment((0, 10), (100, 110)),
            r3.restricted_by_size(open_range(None, 100)))

        self.assertEqual(RangedSegment((9, 10), (100, 101)),
            r3.restricted_by_size(open_range(None, 91)))

    def test_covers(self):
        r1 = RangedSegment((3, 4), (6, 7))

        r2 = RangedSegment((3, 4), (6, 7))
        self.assertTrue(r1.covers(r2))

        r2 = RangedSegment((3, 3), (7, 7))
        self.assertTrue(r1.covers(r2))

        r2 = LinearSegment(4, 6)
        self.assertTrue(r1.covers(r2))

        r2 = RangedSegment((None, 4), (6, 7))
        self.assertFalse(r1.covers(r2))

        r2 = RangedSegment((3, 4), (6, None))
        self.assertFalse(r1.covers(r2))

        r2 = RangedSegment((3, 3), (5, 7))
        self.assertFalse(r1.covers(r2))

        r2 = RangedSegment((3, 5), (6, 7))
        self.assertFalse(r1.covers(r2))

        r2 = LinearSegment(5, 6)
        self.assertFalse(r1.covers(r2))


class RangedBoxTestCase(unittest.TestCase):
    def test_init(self):
        b = RangedBox((10, 20), (3, 5))

        self.assertEqual(Box.from_2points(10, 3, 20, 5), b.to_box())
        self.assertEqual(Box.from_2points(10, 3, 20, 5), b.minimal_box())
        self.assertEqual(Box.from_2points(10, 3, 20, 5), b.maximal_box())

        self.assertEqual(RangedSegment(10, 20), b.project('h'))
        self.assertEqual(RangedSegment(3, 5), b.project('v'))

        b = RangedBox(
            RangedSegment((0, 10), (20, 30)),
            RangedSegment((1, 3), (5, 7)))

        self.assertEqual(Box.from_2points(10, 3, 20, 5), b.minimal_box())
        self.assertEqual(Box.from_2points(0, 1, 30, 7), b.maximal_box())

        self.assertEqual(RangedSegment((0, 10), (20, 30)), b.project('h'))
        self.assertEqual(RangedSegment((1, 3), (5, 7)), b.project('v'))

    def test_intersect_union_combine(self):
        b = RangedBox((10, 20), (3, 5))
        r = RangedBox((10, 20), (3, 5))

        self.assertEqual(Box.from_2points(10, 3, 20, 5), b.intersect(r).to_box())
        self.assertEqual(Box.from_2points(10, 3, 20, 5), b.union(r).to_box())
        self.assertEqual(Box.from_2points(10, 3, 20, 5), b.combine(r).to_box())
        self.assertEqual(Box.from_2points(10, 3, 20, 5), b.intersect_borders(r).to_box())

        b = RangedBox((10, 20), (3, 15))
        r = RangedBox((12, 22), (13, 25))

        self.assertEqual(RangedBox(
            (12, 20), (13, 15)),
            b.intersect(r))
        self.assertEqual(RangedBox(
            (10, 22), (3, 25)),
            b.union(r))
        self.assertEqual(RangedBox(
            (12, 20), (13, 15)),
            b.combine(r))
        self.assertEqual(None,
            b.intersect_borders(r))

        b = RangedBox((10, 20), (3, 15))
        r = RangedBox((20, 22), (15, 25))

        self.assertEqual(RangedBox(
            (20, 20), (15, 15)),
            b.intersect(r))
        self.assertEqual(RangedBox(
            (10, 22), (3, 25)),
            b.union(r))
        self.assertEqual(RangedBox(
            (20, 20), (15, 15)),
            b.combine(r))
        self.assertEqual(None,
            b.intersect_borders(r))

        b = RangedBox((10, 18), (3, 12))
        r = RangedBox((20, 22), (15, 25))

        self.assertEqual(None, b.intersect(r))
        self.assertEqual(RangedBox(
            (10, 22), (3, 25)),
            b.union(r))
        self.assertEqual(None, b.combine(r))
        self.assertEqual(None, b.intersect_borders(r))

    def test_intersect_union_combine_complex_TODO(self):
        b = RangedBox(rx=('6-', '7+'), ry=('1-', '3+'))
        r = RangedBox(rx=('4+', '*'), ry=('3-', '2+'))

        self.assertEqual(RangedBox(
            ('4..6', '7+'), ('1-', '3+')),
            b.intersect(r))
        # self.assertEqual(RangedBox(
        #     ('*', '*'), RangedSegment('1-', '3+', validate=False)),
        #     b.union(r))  # ??????
        self.assertEqual(RangedBox(
            ('4..6', '7+'), ('3-', '3+')),
            b.combine(r))  # ??????
        self.assertEqual(RangedBox(
            ('4+', '7+'), ('3-', '3+')),
            b.intersect_borders(r))

    def test_intersect_union_combine_unrestricted(self):
        # unrestricted maximal / outer / probable ranges...
        # equal
        b = RangedBox(
            RangedSegment((None, 10), (20, None)),
            RangedSegment((None, 3), (5, None)))
        r = RangedBox(
            RangedSegment((None, 10), (20, None)),
            RangedSegment((None, 3), (5, None)))

        self.assertEqual(RangedBox(
                RangedSegment((None, 10), (20, None)),
                RangedSegment((None, 3), (5, None))),
            b.intersect(r))
        self.assertEqual(RangedBox(
                RangedSegment((None, 10), (20, None)),
                RangedSegment((None, 3), (5, None))),
            b.union(r))
        self.assertEqual(RangedBox(
                RangedSegment((None, 10), (20, None)),
                RangedSegment((None, 3), (5, None))),
            b.combine(r))

        # overlap
        b = RangedBox(
            RangedSegment((None, 10), (20, None)),
            RangedSegment((None, 3), (7, None)))
        r = RangedBox(
            RangedSegment((None, 15), (25, None)),
            RangedSegment((None, 5), (9, None)))

        self.assertEqual(RangedBox(
                RangedSegment((None, 15), (20, None)),
                RangedSegment((None, 5), (7, None))),
            b.intersect(r))
        self.assertEqual(RangedBox(
                RangedSegment((None, 10), (25, None)),
                RangedSegment((None, 3), (9, None))),
            b.union(r))
        self.assertEqual(RangedBox(
                RangedSegment((None, 10), (25, None)),
                RangedSegment((None, 3), (9, None))),
            b.combine(r))

        # touch at a point
        b = RangedBox(
            RangedSegment((None, 10), (20, None)),
            RangedSegment((None, 3), (7, None)))
        r = RangedBox(
            RangedSegment((None, 20), (25, None)),
            RangedSegment((None, 7), (9, None)))

        self.assertEqual(RangedBox(
                RangedSegment((None, 20), (20, None)),
                RangedSegment((None, 7), (7, None))),
            b.intersect(r))
        self.assertEqual(RangedBox(
                RangedSegment((None, 10), (25, None)),
                RangedSegment((None, 3), (9, None))),
            b.union(r))
        self.assertEqual(RangedBox(
                RangedSegment((None, 10), (25, None)),
                RangedSegment((None, 3), (9, None))),
            b.combine(r))

        # not connected
        b = RangedBox(
            RangedSegment((None, 10), (12, None)),
            RangedSegment((None, 3), (4, None)))
        r = RangedBox(
            RangedSegment((None, 20), (25, None)),
            RangedSegment((None, 7), (9, None)))

        self.assertEqual(None,
                         b.intersect(r))
        self.assertEqual(RangedBox(
                RangedSegment((None, 10), (25, None)),
                RangedSegment((None, 3), (9, None))),
            b.union(r))
        self.assertEqual(RangedBox(
                RangedSegment((None, 10), (25, None)),
                RangedSegment((None, 3), (9, None))),
            b.combine(r))

    def test_intersect_union_combine_inner_unset(self):
        # unrestricted minimal / inner / definite ranges...
        # equal
        b = RangedBox(
            RangedSegment((10, None), (None, 20)),
            RangedSegment((3, None), (None, 5)))
        r = RangedBox(
            RangedSegment((10, None), (None, 20)),
            RangedSegment((3, None), (None, 5)))

        # inner range was trimmed:
        self.assertEqual(RangedBox(
                RangedSegment((10, 10), (20, 20)),
                RangedSegment((3, 3), (5, 5))),
            b.intersect(r))
        self.assertEqual(RangedBox(
                RangedSegment((10, 10), (20, 20)),
                RangedSegment((3, 3), (5, 5))),
            b.union(r))
        self.assertEqual(RangedBox(
                RangedSegment((10, 10), (20, 20)),
                RangedSegment((3, 3), (5, 5))),
            b.combine(r))

        # overlap
        b = RangedBox(
            RangedSegment((10, None), (None, 20)),
            RangedSegment((3, None), (None, 7)))
        r = RangedBox(
            RangedSegment((15, None), (None, 25)),
            RangedSegment((5, None), (None, 9)))

        # inner range was trimmed:
        self.assertEqual(RangedBox(
                RangedSegment((15, 15), (20, 20)),
                RangedSegment((5, 5), (7, 7))),
            b.intersect(r))
        self.assertEqual(RangedBox(
                RangedSegment((10, 10), (25, 25)),
                RangedSegment((3, 3), (9, 9))),
            b.union(r))
        self.assertEqual(RangedBox(
                RangedSegment((15, 15), (20, 20)),
                RangedSegment((5, 5), (7, 7))),
            b.combine(r))

        # touch at a point
        b = RangedBox(
            RangedSegment((10, None), (None, 15)),
            RangedSegment((3, None), (None, 6)))
        r = RangedBox(
            RangedSegment((15, None), (None, 25)),
            RangedSegment((6, None), (None, 9)))

        # inner range was trimmed:
        self.assertEqual(RangedBox(
                RangedSegment((15, 15), (15, 15)),
                RangedSegment((6, 6), (6, 6))),
            b.intersect(r))
        self.assertEqual(RangedBox(
                RangedSegment((10, 10), (25, 25)),
                RangedSegment((3, 3), (9, 9))),
            b.union(r))
        self.assertEqual(RangedBox(
                RangedSegment((15, 15), (15, 15)),
                RangedSegment((6, 6), (6, 6))),
            b.combine(r))

        # not connected
        b = RangedBox(
            RangedSegment((10, None), (None, 14)),
            RangedSegment((3, None), (None, 5)))
        r = RangedBox(
            RangedSegment((14, None), (None, 25)),
            RangedSegment((6, None), (None, 9)))

        self.assertEqual(None,
                         b.intersect(r))
        self.assertEqual(RangedBox(
                RangedSegment((10, 10), (25, 25)),
                RangedSegment((3, 3), (9, 9))),
            b.union(r))
        self.assertEqual(None,
                         b.combine(r))

    def test_intersect_union_combine_outer_cross(self):
        # two far areas look outside and their looks cross
        # look down & right
        b = RangedBox(
            RangedSegment((30, 40), (60, 70)),
            RangedSegment((0, None), (None, None)))
        r = RangedBox(
            RangedSegment((0, None), (None, None)),
            RangedSegment((5, 10), (20, 25)))

        self.assertEqual(RangedBox(
                RangedSegment((30, 40), (60, 70)),
                RangedSegment((5, 10), (20, 25))),
            b.intersect(r))
        # inner range was trimmed:
        self.assertEqual(RangedBox(
                RangedSegment((0, 0), (None, None)),
                RangedSegment((0, 0), (None, None))),
            b.union(r))
        self.assertEqual(RangedBox(
                # RangedSegment((30, 40), (60, 70)),
                # RangedSegment((5, 10), (20, 25))),
                RangedSegment((30, 30), (60, 70)),
                RangedSegment((5, 5), (20, 25))),
            b.combine(r))

    def test_intersect_union_combine_outer_cross_2(self):
        # two far areas look outside and their looks cross
        # look down & right
        # the look to right starts at 50, covering other area partially
        b = RangedBox(
            RangedSegment((30, 40), (60, 70)),
            RangedSegment((0, None), (None, None)))
        r = RangedBox(
            RangedSegment((50, None), (None, None)),
            RangedSegment((5, 10), (20, 25)))

        self.assertEqual(RangedBox(
                RangedSegment((50, 50), (60, 70)),
                RangedSegment((5, 10), (20, 25))),
            b.intersect(r))
        self.assertEqual(RangedBox(
                RangedSegment((30, 40), (None, None)),
                RangedSegment((0, 0), (None, None))),
            b.union(r))
        self.assertEqual(RangedBox(
                RangedSegment((50, 50), (60, 70)),
                RangedSegment((5, 5), (20, 25))),
            b.combine(r))

        # the look to right starts at 100, not covering other area at all
        b = RangedBox(
            RangedSegment((30, 40), (60, 70)),
            RangedSegment((0, None), (None, None)))
        r = RangedBox(
            RangedSegment((100, None), (None, None)),
            RangedSegment((5, 10), (20, 25)))

        self.assertEqual(None, b.intersect(r))
        self.assertEqual(RangedBox(
                RangedSegment((30, 40), (None, None)),
                RangedSegment((0, 0), (None, None))),
            b.union(r))
        self.assertEqual(None, b.combine(r))

    def test_combine_several_1(self):
        # imitate combining of 4 elements into one match
        #  each element is a corner
        lt = RangedBox(
            RangedSegment((10, 11), (12, None)),
            RangedSegment((20, 21), (22, None)))
        rt = RangedBox(
            RangedSegment((None, 89), (90, 91)),
            RangedSegment((20, 21), (22, None)))
        lb = RangedBox(
            RangedSegment((10, 11), (12, None)),
            RangedSegment((None, 79), (80, 81)))
        rb = RangedBox(
            RangedSegment((None, 89), (90, 91)),
            RangedSegment((None, 79), (80, 81)))

        res = RangedBox.combine_many(lt, rt, lb, rb)

        self.assertEqual(RangedBox(
                RangedSegment((10, 11), (90, 91)),
                RangedSegment((20, 21), (80, 81))),
            res)

    def test_combine_several_2(self):
        # imitate combining of 4 elements into one match
        # each element defines only one side
        L = RangedBox(
            RangedSegment((10, 11), (12, None)),
            RangedSegment())
        t = RangedBox(
            RangedSegment(),
            RangedSegment((20, 21), (22, None)))
        r = RangedBox(
            RangedSegment((None, 89), (90, 91)),
            RangedSegment())
        b = RangedBox(
            RangedSegment(),
            RangedSegment((None, 79), (80, 81)))

        res = RangedBox.combine_many(L, t, r, b)

        self.assertEqual(RangedBox(
                RangedSegment((10, 11), (90, 91)),
                RangedSegment((20, 21), (80, 81))),
            res)

    def test_combine_several_3(self):
        # imitate combining of 4 elements into one match
        # each element defines only one side
        # BUT nothing should match as horizontal items do not overlap
        L = RangedBox(
            RangedSegment((100, 101), (102, None)),
            RangedSegment())
        t = RangedBox(
            RangedSegment(),
            RangedSegment((20, 21), (22, None)))
        r = RangedBox(
            RangedSegment((None, 89), (90, 91)),
            RangedSegment())
        b = RangedBox(
            RangedSegment(),
            RangedSegment((None, 79), (80, 81)))

        res = RangedBox.combine_many(L, t, r, b)

        self.assertIsNone(res)

    def test_combine_several_4(self):
        # imitate combining of 4 elements into one match
        # each element defines only one side
        # BUT nothing should match as vertical items do not overlap
        L = RangedBox(
            RangedSegment((10, 11), (12, None)),
            RangedSegment())
        t = RangedBox(
            RangedSegment(),
            RangedSegment((200, 201), (202, None)))
        r = RangedBox(
            RangedSegment((None, 89), (90, 91)),
            RangedSegment())
        b = RangedBox(
            RangedSegment(),
            RangedSegment((None, 79), (80, 81)))

        res = RangedBox.combine_many(L, t, r, b)

        self.assertIsNone(res)


if __name__ == '__main__':
    unittest.main()
