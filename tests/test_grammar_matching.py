import unittest

from geom2d import Point
from tests_bootstrapper import init_testing_environment

init_testing_environment()

from pathlib import Path

from converters.xlsx import ExcelGrid
from converters.text import TxtGrid
from grammar2d import read_grammar, GrammarMatcher


class GrammarMatchingTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # cls.grid1_t = TxtGrid(Path('test_data/grid1.tsv').read_text())
        # cls.grid1_x = ExcelGrid.read_xlsx(Path('test_data/grid1.xlsx'))

        cls.grid2_t = TxtGrid(Path('test_data/grid2.tsv').read_text())
        cls.grid2_x = ExcelGrid.read_xlsx(Path('test_data/grid2.xlsx'))

        # cls.simple_grammar = read_grammar('test_data/simple_grammar_txt.yml')
        cls.simple_grammar_2 = read_grammar('test_data/simple_grammar_2.yml')
        cls.simple_grammar_2_2 = read_grammar('test_data/simple_grammar_2.2.yml')

    def _test_txt_debug(self):
        # g = TxtGrid(Path('test_data/grid1.tsv').read_text())
        g = ExcelGrid.read_xlsx(Path('test_data/grid1.xlsx'))
        # gw = g.get_view()
        print()
        print("Grid had beed red.")
        print()

        grammar = read_grammar('test_data/simple_grammar_txt.yml')

        print()
        print(grammar)

        from pprint import pprint
        print()
        pprint(grammar.cell_types)
        print()
        # pprint(grammar.patterns)

        gm = GrammarMatcher(grammar=grammar)
        matched_documents = gm.run_match(g)

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
        print('matched root documents ↓')
        pprint(matched_documents)
        print()
        # pprint(grammar.patterns)

    def test_grid1(self):
        gm = GrammarMatcher(grammar=self.simple_grammar)

        for g in (
                self.grid1_x,
                self.grid1_t,
                self.grid1_x,
        ):
            print('using grid:', g)
            matched_documents = gm.run_match(g)

            self.assertEqual(1, len(matched_documents))
            root = matched_documents[0]
            self.assertEqual((9, 9), root.box.size)

            self.assertEqual((8, 1), root['letters'].box.size)
            self.assertEqual((1, 8), root['numbers'].box.size)
            self.assertEqual((8, 8), root['field'].box.size)

            self.assertEqual(('ABCDEFGH'), ''.join(root['letters'].get_text()))
            self.assertEqual(('87654321'), ''.join(root['numbers'].get_content()))

            root_content = root.get_content()
            root_content['field'] = set(root_content['field'])
            self.assertEqual({
                'field': {'o', 'o', 'o', 'o', 'o', 'o', 'o', 'o', 'o', 'o', 'o', 'o', '*', '*', '*', '*', '*', '*', '*',
                          '*', '*',
                          '*', '*', '*', },
                'numbers': ['8', '7', '6', '5', '4', '3', '2', '1'],
                'letters': ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']},
                root_content)

    def test_grid2(self):
        gm = GrammarMatcher(grammar=self.simple_grammar_2)

        for g in (
                # self.grid2_x,
                self.grid2_t,
                # self.grid2_x,
        ):
            print('using grid:', g)
            matched_documents = gm.run_match(g)

            self.assertEqual(1, len(matched_documents))
            root = matched_documents[0]
            self.assertEqual((8, 9), root.box.size)

            groups_3x3 = root['field'].get_children()
            self.assertEqual(5, len(groups_3x3))

            positions = [m.box.position for m in groups_3x3]
            # Note!
            self.assertSetEqual({
                    Point(x=1, y=2),
                    Point(x=1, y=5),
                    Point(x=4, y=4),
                    Point(x=4, y=7),
                    Point(x=6, y=1)},
                set(positions))
            # assert False, ('Intended fail for debugging. positions:', positions)

    def test_grid2_2(self):
        gm = GrammarMatcher(grammar=self.simple_grammar_2_2)

        for g in (
                # self.grid2_x,
                self.grid2_t,
                # self.grid2_x,
        ):
            print('using grid:', g)
            matched_documents = gm.run_match(g)

            self.assertEqual(1, len(matched_documents))
            root = matched_documents[0]
            self.assertEqual((8, 9), root.box.size)

            groups_3x3 = root['field'].get_children()
            self.assertEqual(5, len(groups_3x3))

            positions = [m.box.position for m in groups_3x3]
            # Note!
            self.assertSetEqual({
                    Point(x=1, y=2),
                    Point(x=1, y=5),
                    Point(x=4, y=4),
                    Point(x=4, y=7),
                    Point(x=6, y=1)},
                set(positions))


if __name__ == '__main__':
    # unittest.main()
    # GrammarMatchingTestCase._test_txt_debug(...)
    GrammarMatchingTestCase.setUpClass()
    GrammarMatchingTestCase.test_grid2(GrammarMatchingTestCase())
