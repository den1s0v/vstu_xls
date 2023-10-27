import unittest

from confidence_matching import ConfidentPattern, read_cell_types


class ConfidentPatternTestCase(unittest.TestCase):
    def test_init1(self):
        p = ConfidentPattern('\\w+')
        self.assertIsNotNone(p.match('abcde'))  # add assertion here
        self.assertIsNotNone(p.match('124'))
        self.assertIsNone(p.match('****'))

    def test_init2(self):
        p = ConfidentPattern({'pattern': 'a bc+', 'confidence': 0.9, 'pattern_syntax': 're-spaces'})

        self.assertIsNotNone(p.match('abcde'))
        self.assertIsNone(p.match('124'))
        self.assertIsNotNone(p.match('a   bcccc'))


class CellTypeTestCase(unittest.TestCase):
    def test_init1(self):
        cell_types = read_cell_types()
        self.assertIn('teacher', cell_types)

    def test_init2(self):
        ...


if __name__ == '__main__':
    unittest.main()
