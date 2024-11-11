import unittest
from geom2d import Box, ManhattanDistance, Point, VariBox


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



if __name__ == '__main__':
    unittest.main()
