import unittest
from geom2d import Box


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




if __name__ == '__main__':
    unittest.main()
