import unittest
from geom2d import Box, Point


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

        self.assertEqual(b.manhattan_distance_to(a), 2 * 7)

    def test_box_dist_2(self):
        # inside
        a = Box(-4, -3, 10,10)
        b = Box(4, 3, 1,1)

        self.assertEqual(b.manhattan_distance_to(a), 0)

    def test_box_dist_3(self):
        # overlaps and (1, 1) is outside
        a = Box(-4, -3, 10,10)
        b = Box(4, 3, 3,5)

        self.assertEqual(b.manhattan_distance_to(a), 1 + 1)




if __name__ == '__main__':
    unittest.main()
