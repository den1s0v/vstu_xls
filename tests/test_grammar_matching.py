import unittest

from geom2d import Point, Box
from tests_bootstrapper import init_testing_environment

init_testing_environment()

from pathlib import Path

from converters.xlsx import ExcelGrid
from converters.text import TxtGrid
from grammar2d import read_grammar, GrammarMatcher


class GrammarMatchingTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.grid1_t = TxtGrid(Path('test_data/grid1.tsv').read_text())
        cls.grid1_x = ExcelGrid.read_xlsx(Path('test_data/grid1.xlsx'))

        cls.grid2_t = TxtGrid(Path('test_data/grid2.tsv').read_text())
        cls.grid2_x = ExcelGrid.read_xlsx(Path('test_data/grid2.xlsx'))

        cls.grid4_t = TxtGrid(Path('test_data/grid4.tsv').read_text())

        cls.grid5_t = TxtGrid(Path('test_data/grid5.tsv').read_text(), sep='')
        cls.grid5_x = ExcelGrid.read_xlsx(Path('test_data/grid5.xlsx'))

        cls.simple_grammar = read_grammar('test_data/simple_grammar_txt.yml')
        cls.simple_grammar_2 = read_grammar('test_data/simple_grammar_2.yml')
        cls.simple_grammar_2_2 = read_grammar('test_data/simple_grammar_2.2.yml')
        cls.simple_grammar_2_3 = read_grammar('test_data/simple_grammar_2.3.yml')
        cls.simple_grammar_2_4 = read_grammar('test_data/simple_grammar_2.4.yml')
        cls.simple_grammar_2_5 = read_grammar('test_data/simple_grammar_2.5.yml')
        cls.simple_grammar_2_6 = read_grammar('test_data/simple_grammar_2.6.yml')

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

    def test_grid2_1(self):
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

    def test_grid2_3(self):
        gm = GrammarMatcher(grammar=self.simple_grammar_2_3)

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

    def test_grid2_4(self):
        gm = GrammarMatcher(grammar=self.simple_grammar_2_4)

        for g in (
                self.grid5_t,
                # self.grid2_x,
        ):
            print('using grid:', g)
            matched_documents = gm.run_match(g)

            self.assertEqual(1, len(matched_documents))
            root = matched_documents[0]
            # self.assertEqual((8, 9), root.box.size)

            marks_array = root['field'].get_children()
            # self.assertEqual(5, len(marks_array))

            positions = [m.box for m in marks_array]
            # Note!
            self.assertSetEqual({
                   Box(28,5, 1,12),
                   Box(21,14, 4,4),
                   Box(2,4, 20,11),
                   Box(0,1, 31,1),
                },
                set(positions))

    def test_grid2_5(self):
        gm = GrammarMatcher(grammar=self.simple_grammar_2_5)

        for g in (
                self.grid5_t,
                self.grid5_x,
        ):
            print('using grid:', g)
            matched_documents = gm.run_match(g)

            self.assertEqual(1, len(matched_documents))
            root = matched_documents[0]
            # self.assertEqual((8, 9), root.box.size)

            marks_array = root['field'].get_children()
            # self.assertEqual(5, len(marks_array))

            positions = [m.box for m in marks_array]
            # Note!
            self.assertSetEqual({
                Box(0,1, 4,1),
                Box(10,14, 4,1),
                Box(10,4, 4,1),
                Box(12,1, 4,1),
                Box(14,13, 4,2),
                Box(14,4, 4,2),
                Box(16,1, 4,1),
                Box(18,12, 2,1),
                Box(18,6, 3,2),
                Box(2,8, 2,4),
                Box(20,1, 4,1),
                Box(20,8, 2,4),
                Box(21,14, 4,4),
                Box(24,1, 4,1),
                Box(28,1, 3,1),
                Box(28,13, 1,4),
                Box(28,5, 1,4),
                Box(28,9, 1,4),
                Box(3,6, 3,2),
                Box(4,1, 4,1),
                Box(4,12, 2,1),
                Box(6,13, 4,2),
                Box(6,4, 4,2),
                Box(8,1, 4,1),
            }, set(positions))

    def test_grid2_6(self):
        gm = GrammarMatcher(grammar=self.simple_grammar_2_6)

        for g in (
                self.grid5_t,
                self.grid5_x,
        ):
            print('using grid:', g)
            matched_documents = gm.run_match(g)

            self.assertEqual(1, len(matched_documents))
            root = matched_documents[0]
            # self.assertEqual((8, 9), root.box.size)

            marks_array = root['field'].get_children()
            # self.assertEqual(5, len(marks_array))

            positions = [m.box for m in marks_array]
            # Note!
            self.assertSetEqual({
                Box(0,1, 4,1),
                ...
            }, set(positions))


if __name__ == '__main__':
    # unittest.main()
    # GrammarMatchingTestCase._test_txt_debug(...)
    GrammarMatchingTestCase.setUpClass()
    GrammarMatchingTestCase.test_grid2_4(GrammarMatchingTestCase())
