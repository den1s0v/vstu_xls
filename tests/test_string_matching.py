import unittest

from tests_bootstrapper import init_testing_environment

init_testing_environment()

from string_matching import CellType, StringPattern, StringMatch
from string_matching.helper_transformers import shrink_extra_inner_spaces
from string_matching import read_cell_types, fix_sparse_words


class StringPatternTestCase(unittest.TestCase):
    def test_init1(self):
        p = StringPattern('\\w+')
        self.assertIsNotNone(p.match('abcde'))  # add assertion here
        self.assertIsNotNone(p.match('124'))
        self.assertIsNone(p.match('****'))
        p.confidence = 1
        self.assertEqual(1, p.match('abcd123_').precision)

    def test_init2(self):
        p = StringPattern('a bc+', 0.9, 're-spaces')

        self.assertIsNotNone(p.match('abcde'))
        self.assertIsNone(p.match('124'))
        self.assertIsNone(p.match('ab'))
        self.assertIsNotNone(p.match('a   bcccc'))

    def test_init3(self):
        p = StringPattern(**{'pattern': 'a bc+', 'confidence': 0.9, 'pattern_syntax': 're-spaces'})

        self.assertIsNotNone(p.match('abcde'))
        self.assertIsNone(p.match('124'))
        self.assertIsNotNone(p.match('a   bcccc'))

    def test_init4_re_spaces(self):
        p = StringPattern({'pattern': 'a bc+', 'confidence': 0.9, 'pattern_syntax': 're-spaces'})

        self.assertIsNotNone(p.match('abcde'))
        self.assertIsNone(p.match('124'))
        self.assertIsNotNone(p.match('a   bcccc'))

    def test_plain(self):
        p = StringPattern(pattern='ab', pattern_syntax='plain')

        self.assertIsNotNone(p.match('ab'))
        self.assertIsNotNone(p.match(' ab '))  # strip works :)

        self.assertIsNone(p.match('abcde'))
        self.assertIsNone(p.match('a  b'))
        self.assertIsNone(p.match('cdefab'))

        s = 'ab'
        m = p.match(s)
        self.assertIsNotNone(m)
        self.assertEqual(s, m[0])
        self.assertIn(0, m)

        self.assertDictEqual({}, m.groupdict())

    def test_capture2(self):
        p = StringPattern(r'=(\w+)\+(\w+)=')

        s = '=a+b='
        m = p.match(s)
        self.assertIsNotNone(m)
        self.assertIs(p, m.pattern)
        self.assertEqual(p.confidence, m.confidence)

        self.assertEqual(s, m[0])
        self.assertEqual('a', m[1])
        self.assertEqual('b', m[2])

        self.assertDictEqual({1: 'a', 2: 'b'}, m.groupdict())

    def test_capture3(self):
        p = StringPattern(r'=(\w+)\+(\w+)=', captures=('left', 'right'))

        s = '=a+b='
        m = p.match(s)
        self.assertIsNotNone(m)
        self.assertEqual(s, m[0])
        self.assertEqual('a', m[1])
        self.assertEqual('a', m['left'])
        self.assertEqual('b', m[2])
        self.assertEqual('b', m['right'])

        self.assertIn('left', m)
        self.assertNotIn('BAD_INDEX', m)

        self.assertDictEqual({'left': 'a', 'right': 'b'}, m.groupdict())

    def test_capture4_named(self):
        p = StringPattern(r'=(?P<left>\w+)\+(?P<right>\w+)=', captures=('left', 'right'))

        s = '=a+b='
        m = p.match(s)
        self.assertIsNotNone(m)
        self.assertEqual(s, m[0])
        self.assertEqual('a', m[1])
        self.assertEqual('a', m['left'])
        self.assertEqual('b', m[2])
        self.assertEqual('b', m['right'])

        self.assertIn('left', m)
        self.assertNotIn('BAD_INDEX', m)

        self.assertDictEqual({'left': 'a', 'right': 'b'}, m.groupdict())

    def test_capture5_names_reversed(self):
        p = StringPattern(r'=(?P<left>\w+)\+(?P<right>\w+)=', captures=('right', 'left', ))

        s = '=a+b='
        m = p.match(s)
        self.assertIsNotNone(m)
        self.assertEqual(s, m[0])
        self.assertEqual('a', m[2])  # Note: indexed by `captures` order, not by regex.
        self.assertEqual('a', m['left'])
        self.assertEqual('b', m[1])  # The same applies.
        self.assertEqual('b', m['right'])

        self.assertIn('right', m)
        self.assertNotIn('BAD_INDEX', m)
        self.assertNotIn('RIGHT', m)

        self.assertDictEqual({'left': 'a', 'right': 'b'}, m.groupdict())

    def test_capture6_unnamed_mixed(self):
        p = StringPattern(
            # Note: left group in not named
            r'=(\w+)\+(?P<middle>\w+)\+(?P<right>\w+)=',
            # captures=('right', 'left', )
        )

        s = '=a+b+f=='
        m = p.match(s)
        self.assertIsNotNone(m)
        self.assertEqual('=a+b+f=', m[0])
        self.assertEqual('a', m[1])
        # self.assertEqual('a', m['left'])
        self.assertEqual('b', m[2])
        # self.assertEqual('b', m['middle'])
        self.assertEqual('f', m[3])
        # self.assertEqual('f', m['right'])

        # self.assertIn('middle', m)
        # self.assertIn('right', m)
        self.assertNotIn('BAD_INDEX', m)
        self.assertNotIn('RIGHT', m)

        self.assertDictEqual({
            1: 'a',
            2: 'b',
            3: 'f',
            'middle': 'b',
            'right': 'f'
        }, m.groupdict())

    def test_capture7_named_mixed(self):
        p = StringPattern(
            # Note: left group in not named
            r'=(\w+)\+(?P<middle>\w+)\+(?P<right>\w+)=',
            captures=('left', 'middle', 'right', )
        )

        s = '=a+b+f=='
        m = p.match(s)
        self.assertIsNotNone(m)
        self.assertEqual('=a+b+f=', m[0])
        self.assertEqual('a', m[1])
        self.assertEqual('a', m['left'])
        self.assertEqual('b', m[2])
        self.assertEqual('b', m['middle'])
        self.assertEqual('f', m[3])
        self.assertEqual('f', m['right'])

        self.assertIn('left', m)
        self.assertIn('middle', m)
        self.assertIn('right', m)
        self.assertNotIn('RIGHT', m)
        self.assertNotIn('BAD_INDEX', m)
        self.assertIsNone(m['BAD_INDEX'])

        self.assertDictEqual({
            'left': 'a',
            'middle': 'b',
            'right': 'f'
        }, m.groupdict())

        p.confidence = 1
        # last char of 8 is not included
        self.assertEqual(7/8, m.precision)


    def test_preprocess0(self):
        p = StringPattern(
            pattern=r'абхч, где ёж?',
            pattern_syntax='plain',
            preprocess=(),
        )
        # Note: str.strip & shrink_extra_inner_spaces work anyway.

        self.assertIsNotNone(p.match('абхч, где ёж?'))
        self.assertIsNotNone(p.match('    абхч, где ёж?   '))
        self.assertIsNotNone(p.match('абхч,     где     ёж?'))
        self.assertIsNotNone(p.match('    абхч,     где     ёж?    '))

    def test_preprocess1(self):
        p = StringPattern(
            pattern=r'абвгдеёжз',
            preprocess=('remove_all_spaces', )
        )

        self.assertIsNotNone(p.match('абвгдеёжз'))
        self.assertIsNotNone(p.match('а бвгдеёжз'))
        self.assertIsNotNone(p.match('а б в г д е ё ж з'))
        self.assertIsNotNone(p.match('  а б в г д е ё ж з  '))
        self.assertIsNotNone(p.match('  а  б  в  г  д  е  ё  ж  з  '))

    def test_preprocess2(self):
        p = StringPattern(
            pattern=r'что-нибудь',
            preprocess=('remove_spaces_around_hypen', )
        )

        self.assertIsNotNone(p.match('что-нибудь'))
        self.assertIsNotNone(p.match(' что-нибудь '))
        self.assertIsNotNone(p.match('что -нибудь'))
        self.assertIsNotNone(p.match('что- нибудь'))
        self.assertIsNotNone(p.match('что - нибудь'))
        self.assertIsNotNone(p.match('что     -    нибудь'))

        self.assertIsNone(p.match('что--нибудь'))
        self.assertIsNone(p.match('что     --    нибудь'))

    def test_preprocess21(self):
        p = StringPattern(
            pattern=r'кое-что когда-нибудь',
            preprocess=('remove_spaces_around_hypen', )
        )

        self.assertIsNotNone(p.match('кое-что когда-нибудь'))
        self.assertIsNotNone(p.match('кое-что     когда-нибудь'))
        self.assertIsNotNone(p.match('кое -что когда- нибудь'))
        self.assertIsNotNone(p.match('кое- что когда -нибудь'))
        self.assertIsNotNone(p.match('кое - что когда - нибудь'))
        self.assertIsNotNone(p.match('кое - что когда - нибудь'))
        self.assertIsNotNone(p.match('кое  -  что когда  -  нибудь'))

    def test_preprocess3(self):
        p = StringPattern(
            pattern=r'антимонии анти-мониалэ',
            preprocess=('fix_sparse_words', 'remove_spaces_around_hypen', )
        )

        self.assertIsNotNone(p.match('антимонии анти-мониалэ'))
        self.assertIsNotNone(p.match('а н т и м о н и и  а н т и - м о н и а л э'))
        self.assertIsNotNone(p.match('а  н  т  и  м  о  н  и  и    а  н  т  и -  м  о  н  и  а  л  э'))
        self.assertIsNotNone(p.match('а  н  т  и  м  о  н  и  и    а  н  т  и  -м  о  н  и  а  л  э'))

class CellTypeTestCase(unittest.TestCase):
    def test_init1(self):
        ct = CellType('test_type', patterns=[
            StringPattern('one two three', confidence=1)
        ])

        m = ct.match('one two three')
        self.assertIsNotNone(m)
        self.assertTrue(isinstance(m, StringMatch))
        self.assertEqual(1, m.precision)

    def test_config(self):
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
        self.assertEqual('word1 word2', fix_sparse_words('word1 word2'))
        self.assertEqual('word1 word2', fix_sparse_words('w o r d 1  w o r d 2'))
        self.assertEqual('word1 word2', fix_sparse_words('wo r d1   w o r d 2'))
        self.assertEqual('wo rd 12 word2', fix_sparse_words('wo   rd  12   w o r d 2'))

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
