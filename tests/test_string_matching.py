import unittest

from tests_bootstrapper import init_testing_environment
init_testing_environment()

from string_matching import StringPattern, read_cell_types, shrink_extra_inner_spaces, fix_sparse_words


class StringPatternTestCase(unittest.TestCase):
    def test_init1(self):
        p = StringPattern('\\w+')
        self.assertIsNotNone(p.match('abcde'))  # add assertion here
        self.assertIsNotNone(p.match('124'))
        self.assertIsNone(p.match('****'))

    def test_init2(self):
        p = StringPattern({'pattern': 'a bc+', 'confidence': 0.9, 'pattern_syntax': 're-spaces'})

        self.assertIsNotNone(p.match('abcde'))
        self.assertIsNone(p.match('124'))
        self.assertIsNotNone(p.match('a   bcccc'))


class CellTypeTestCase(unittest.TestCase):
    def test_init1(self):
        cell_types = read_cell_types()
        self.assertIn('teacher', cell_types)
        self.assertIn('room', cell_types)
        self.assertIn('discipline', cell_types)
        self.assertIsNotNone(cell_types['teacher'].match('доц. Грачёва Н.В.'))

    # def test_init2(self):
    #     cell_types = read_cell_types()
    #     group = cell_types['group']
    #


class ShrinkTestCase(unittest.TestCase):
    def test_1(self):
        self.assertEqual('a b', shrink_extra_inner_spaces('a    b'))
        self.assertEqual('a b', shrink_extra_inner_spaces('a  b'))
        self.assertEqual('a b', shrink_extra_inner_spaces('a b'))
        self.assertEqual('ab', shrink_extra_inner_spaces('ab'))


class SparseTestCase(unittest.TestCase):
    def test_real(self):
        self.assertEqual('МАТЕМАТИКА', fix_sparse_words('М А Т Е М А Т И К А'))
        self.assertEqual('ИН. ЯЗЫК', fix_sparse_words('И Н.   Я З Ы К'))
        self.assertEqual('ИНФОРМАТИКА', fix_sparse_words(
            'И       Н      Ф     О      Р        М       А      Т       И       К      А'))
        self.assertEqual('ФИЗИКА', fix_sparse_words(
            'Ф          И          З          И          К          А    '))
        self.assertEqual('ИСТОРИЯ РОССИИ', fix_sparse_words(
            'И   С   Т   О   Р   И   Я            Р   О   С   С   И   И'))

    def test_custom(self):
        self.assertEqual('word1 word2', fix_sparse_words('w o r d 1  w o r d 2'))

    def test_regression(self):
        self.assertEqual('ab', fix_sparse_words('a       b'))
        self.assertEqual('aa  cc  dd  bb', fix_sparse_words('aa  cc  dd  bb'))
        self.assertEqual('ab', fix_sparse_words('a  b'))
        self.assertEqual('ab', fix_sparse_words('a b'))
        self.assertEqual('ab', fix_sparse_words('ab'))
        self.assertEqual('ОСНОВЫ     РОССИЙСКОЙ     ГОСУДАРСТВЕННОСТИ', fix_sparse_words(
            'ОСНОВЫ     РОССИЙСКОЙ     ГОСУДАРСТВЕННОСТИ'))


if __name__ == '__main__':
    unittest.main()
