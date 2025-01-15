import unittest

from tests_bootstrapper import init_testing_environment

init_testing_environment()

from pathlib import Path

from utils import find_file_under_path
from grammar2d import read_grammar


class UtilsTestCase(unittest.TestCase):
    def test_find_file_under_path_1(self):
        source_path = '../cnf/cell_types.yml'
        expected_path = Path(source_path).resolve()

        resolved_path = find_file_under_path(source_path, '../cnf/grammar_root.yml')

        self.assertIsNotNone(resolved_path)
        self.assertEqual(expected_path, resolved_path)

    def test_find_file_under_path_2(self):
        source_path = 'cnf/cell_types.yml'
        expected_path = Path('./../', source_path).resolve()

        resolved_path = find_file_under_path(source_path, '../cnf/grammar_root.yml')

        self.assertIsNotNone(resolved_path)
        self.assertEqual(expected_path, resolved_path)

    def test_find_file_under_path_3(self):
        source_path = 'cell_types.yml'
        expected_path = Path('./../cnf/', source_path).resolve()

        resolved_path = find_file_under_path(source_path, '../cnf/grammar_root.yml')

        self.assertIsNotNone(resolved_path)
        self.assertEqual(expected_path, resolved_path)


class GrammarTestCase(unittest.TestCase):
    def test_1(self):
        grammar = read_grammar()
        print(grammar)

        from pprint import pprint
        pprint(grammar.patterns)


if __name__ == '__main__':
    # unittest.main()
    GrammarTestCase.test_1(...)

