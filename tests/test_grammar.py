import unittest

from tests_bootstrapper import init_testing_environment

init_testing_environment()

from pathlib import Path

from utils import find_file_under_path
from grid import Grid, Cell, TxtGrid
from grammar2d import read_grammar, GrammarMatcher


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


class GrammarMatchingTestCase(unittest.TestCase):
    def test_txt(self):
        g = TxtGrid(Path('test_data/grid1.tsv').read_text())
        # gw = g.get_view()

        grammar = read_grammar('test_data/simple_grammar_txt.yml')

        print()
        print(grammar)

        from pprint import pprint
        print()
        pprint(grammar.cell_types)
        print()
        # pprint(grammar.patterns)

        gm = GrammarMatcher(grammar=grammar)
        gm.run_match(g)

        print()
        print('type_to_cells ↓')
        print()
        pprint(gm.type_to_cells)
        print()
        print()
        print('_matches_by_position ↓')
        pprint(gm._matches_by_position)
        print()
        print('_matches_by_element ↓')
        pprint(gm._matches_by_element)
        print()
        print('_grid_view ↓')
        pprint(gm._grid_view)
        print()
        # pprint(grammar.patterns)


class GrammarTestCase(unittest.TestCase):
    def test_1(self):

        grammar = read_grammar()
        print()
        print(grammar)

        from pprint import pprint
        pprint(grammar.cell_types)
        pprint(grammar.patterns)




if __name__ == '__main__':
    # unittest.main()
    # GrammarTestCase.test_1(...)
    GrammarMatchingTestCase.test_txt(...)

