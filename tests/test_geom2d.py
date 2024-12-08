import unittest

from tests_bootstrapper import init_testing_environment
init_testing_environment()

from geom2d import Box, ManhattanDistance, Point, VariBox, PartialBox


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

    def test_point_dist(self):
        # triangle: 2 * (3, 4, 5)
        a = Point(-4, -3)
        b = Point(4, 3)

        self.assertEqual(b.distance_to(a), 2 * 5)
        self.assertEqual(b.manhattan_distance_to(a), 2 * 7)

    def test_box_dist_1(self):
        # triangle: 2 * (3, 4, 5)
        a = Box(-4, -3, 1,1)
        b = Box(4, 3, 1,1)

        self.assertEqual(b.manhattan_distance_to_overlap(a), 2 * 7)
        self.assertEqual(b.manhattan_distance_to_touch(a), 2 * 7 - 2)

    def test_box_dist_2(self):
        a = Box(4, 1, 1,1)
        b = Box(4, 3, 1,1)

        self.assertEqual(b.manhattan_distance_to_overlap(a), 2)
        self.assertEqual(b.manhattan_distance_to_touch(a), 1)

    def test_box_dist_3(self):
        # inside
        a = Box(-4, -3, 10,10)
        b = Box(4, 3, 1,1)

        self.assertEqual(b.manhattan_distance_to_overlap(a), 0)
        self.assertEqual(b.manhattan_distance_to_touch(a), 0)

    def test_box_dist_4(self):
        # overlaps and (1, 1) is outside
        a = Box(-4, -3, 10,10)
        b = Box(4, 3, 3,5)

        self.assertEqual(b.manhattan_distance_to_overlap(a), 1 + 1)

        self.assertEqual(b.manhattan_distance_to_touch(a), 0)

    def test_box_dist_5(self):
        # overlaps and (1, 1) is outside
        a = Box(-4, -3, 10,10)
        b = Box(4, 3, 3,5)

        self.assertEqual(b.manhattan_distance_to_overlap(a, True), (1, 1))

        self.assertEqual(b.manhattan_distance_to_touch(a, True), (0, 0))

    def test_box_dist_6(self):
        # triangle: 2 * (3, 4, 5)
        a = Box(-4, -3, 1,1)
        b = Box(4, 3, 1,1)

        self.assertEqual(b.manhattan_distance_to_overlap(a, True), 2 * 7)
        self.assertEqual(b.manhattan_distance_to_overlap(a, True), (8, 6))
        self.assertEqual(b.manhattan_distance_to_touch(a, True), 2 * 7 - 2)
        self.assertEqual(b.manhattan_distance_to_touch(a, True), ManhattanDistance(7, 5))



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
            b.h = -1   # negative

        with self.assertRaises(AssertionError):
            b.h = None

        with self.assertRaises(AssertionError):
            b.bottom = None


if __name__ == '__main__':
    unittest.main()
