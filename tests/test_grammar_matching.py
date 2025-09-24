import unittest

from geom2d import Point, Box
from pprint import pprint
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
        cls.grid6_x = ExcelGrid.read_xlsx(Path('test_data/grid6.xlsx'))

        cls.grid_vstusched_week = ExcelGrid.read_xlsx(Path('test_data/vstusched_week.xlsx'))

        cls.grid_vstu_fevt3 = ExcelGrid.read_xlsx(Path('test_data/ОН_ФЭВТ_4 курс 2023.xlsx'))

        cls.vstu_grammar = read_grammar('../cnf/grammar_root.yml')

        cls.simple_grammar = read_grammar('test_data/simple_grammar_txt.yml')
        cls.simple_grammar_2 = read_grammar('test_data/simple_grammar_2.yml')
        cls.simple_grammar_2_2 = read_grammar('test_data/simple_grammar_2.2.yml')
        cls.simple_grammar_2_3 = read_grammar('test_data/simple_grammar_2.3.yml')
        cls.simple_grammar_2_4 = read_grammar('test_data/simple_grammar_2.4.yml')
        cls.simple_grammar_2_5 = read_grammar('test_data/simple_grammar_2.5.yml')
        cls.simple_grammar_2_6 = read_grammar('test_data/simple_grammar_2.6.yml')
        cls.simple_grammar_2_7 = read_grammar('test_data/simple_grammar_2.7.yml')

        # sea
        cls.sea_0_t = TxtGrid(Path('test_data/sea_0.tsv').read_text())
        cls.sea_1_t = TxtGrid(Path('test_data/sea_1.tsv').read_text())
        ...
        cls.sea_6_t = TxtGrid(Path('test_data/sea_6.tsv').read_text())

        cls.sea_9_x = ExcelGrid.read_xlsx(Path('test_data/sea9.xlsx'))

        cls.sea_grammar_1 = read_grammar('test_data/sea_grammar_1.yml')
        cls.sea_grammar_2 = read_grammar('test_data/sea_grammar_2.yml')
        cls.sea_grammar_22 = read_grammar('test_data/sea_grammar_2.2.yml')
        cls.sea_grammar_6 = read_grammar('test_data/sea_grammar_6.yml')
        cls.sea_grammar_62 = read_grammar('test_data/sea_grammar_6.2.yml')
        ...

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

            self.assertEqual('ABCDEFGH', ''.join(root['letters'].get_text()))
            self.assertEqual('87654321', ''.join(root['numbers'].get_content()))

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
            self.assertEqual((7, 9), root.box.size)

            groups_3x3 = root['field'].get_children()
            self.assertEqual(5, len(groups_3x3))

            positions = [m.box for m in groups_3x3]
            # Note!
            self.assertSetEqual({
                    Box(1,2, 3,3),
                    Box(1,5, 3,3),
                    Box(4,4, 3,3),
                    Box(4,7, 3,3),
                    Box(5,1, 3,3),
            }, set(positions))

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
                Box(0,1, 6,1),
                Box(6,1, 6,1),
                Box(12,1, 6,1),
                Box(18,1, 5,1),
                Box(23,1, 4,1),
                Box(27,1, 4,1),
                Box(28,5, 1,6),
                Box(28,11, 1,6),
                Box(3,5, 6,3),
                Box(2,8, 4,5),
                Box(9,4, 6,1),
                Box(6,13, 6,2),
                Box(15,5, 6,3),
                Box(12,13, 6,2),
                Box(18,8, 4,5),
                Box(21,15, 4,3),
            }, set(positions))

    def test_grid2_7(self):
        gm = GrammarMatcher(grammar=self.simple_grammar_2_7)

        for g in (
                # self.grid5_t,
                self.grid6_x,
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
                Box(0,1, 5,1), Box(21,15, 4,2), Box(10,23, 3,3), Box(1,5, 5,1), Box(13,25, 3,2), Box(7,14, 2,4), Box(19,1, 4,1), Box(10,26, 3,2), Box(9,17, 3,3), Box(16,9, 2,2), Box(11,23, 5,1), Box(27,1, 4,1), Box(11,3, 5,1), Box(3,17, 3,2), Box(26,5, 4,1), Box(16,3, 5,1), Box(17,7, 4,1), Box(15,1, 4,1), Box(6,3, 5,1), Box(1,3, 5,1), Box(25,20, 4,1), Box(25,12, 3,2), Box(11,9, 1,5), Box(10,1, 5,1), Box(16,5, 5,1), Box(18,15, 2,4), Box(9,9, 1,4), Box(23,9, 2,3), Box(11,15, 4,2), Box(25,15, 5,1), Box(23,17, 2,4), Box(6,5, 5,1), Box(11,24, 5,1), Box(3,14, 3,2), Box(24,17, 4,2), Box(19,18, 3,3), Box(16,12, 3,2), Box(23,1, 4,1), Box(29,16, 1,5), Box(26,3, 5,1), Box(21,3, 5,1), Box(12,18, 3,3), Box(10,22, 5,1), Box(4,19, 4,2), Box(12,7, 4,1), Box(19,9, 2,3), Box(11,27, 4,1), Box(20,12, 3,2), Box(21,5, 5,1), Box(22,7, 5,1), Box(5,1, 5,1), Box(11,5, 5,1),
            }, set(positions))

    def test_grid_sea_1_1(self):
        gm = GrammarMatcher(grammar=self.sea_grammar_1)

        for g in (
                self.sea_1_t,
        ):
            # print('using grid:', g)
            matched_documents = gm.run_match(g)

            self.assertEqual(1, len(matched_documents))
            root = matched_documents[0]
            # self.assertEqual((8, 9), root.box.size)

            children = root['field'].get_children()
            self.assertEqual(1, len(children))

            positions = [m.box for m in children]
            # Note!
            self.assertSetEqual({
                Box(2,2, 4,3),
            }, set(positions))

    def test_grid_sea_1_22(self):
        gm = GrammarMatcher(grammar=self.sea_grammar_22)

        for g in (
                self.sea_1_t,
        ):
            # print('using grid:', g)
            matched_documents = gm.run_match(g)

            self.assertEqual(1, len(matched_documents))
            root = matched_documents[0]
            # self.assertEqual((8, 9), root.box.size)

            children = root['field'].get_children()
            self.assertEqual(2, len(children))

            positions = [m.box for m in children]
            # Note!
            self.assertSetEqual({
                Box(2,2, 1,3),
                Box(5,2, 1,3),
            }, set(positions))

            self.assertEqual(3,
                len(gm.matches_by_element[gm.grammar['beach-L']]))
            self.assertEqual(3,
                len(gm.matches_by_element[gm.grammar['beach-R']]))

    def test_grid_sea_0_2(self):
        gm = GrammarMatcher(grammar=self.sea_grammar_2)

        for g in (
                self.sea_0_t,
        ):
            # print('using grid:', g)
            matched_documents = gm.run_match(g)

            self.assertEqual(1, len(matched_documents))
            root = matched_documents[0]
            # self.assertEqual((8, 9), root.box.size)

            children = root['field'].get_children()
            self.assertEqual(1, len(children))

            positions = [m.box for m in children]
            # Note!
            self.assertSetEqual({
                Box(3,3, 2,1),
            }, set(positions))

    def test_grid_sea_0_22(self):
        gm = GrammarMatcher(grammar=self.sea_grammar_22)

        for g in (
                self.sea_0_t,
        ):
            # print('using grid:', g)
            matched_documents = gm.run_match(g)

            self.assertEqual(1, len(matched_documents))
            root = matched_documents[0]
            # self.assertEqual((8, 9), root.box.size)

            children = root['field'].get_children()
            self.assertEqual(1, len(children))

            positions = [m.box for m in children]
            # Note!
            self.assertSetEqual({
                Box(3,3, 2,1),
            }, set(positions))

            self.assertEqual(1,
                len(gm.matches_by_element[gm.grammar['beach-L']]))
            self.assertEqual(1,
                len(gm.matches_by_element[gm.grammar['beach-R']]))

    def test_grid_sea_6_6(self):
        gm = GrammarMatcher(grammar=self.sea_grammar_6)

        for g in (
                self.sea_6_t,
        ):
            # print('using grid:', g)
            matched_documents = gm.run_match(g)

            self.assertEqual(1, len(matched_documents))
            root = matched_documents[0]
            # self.assertEqual((8, 9), root.box.size)

            children = root['field'].get_children()
            self.assertEqual(1, len(children))

            # positions = [m.box for m in children]
            # # Note!
            # self.assertSetEqual({
            #     Box(3,3, 2,1),
            # }, set(positions))

            # self.assertEqual(1,
            #     len(gm.matches_by_element[gm.grammar['beach-L']]))
            # self.assertEqual(1,
            #     len(gm.matches_by_element[gm.grammar['beach-R']]))

    def test_grid_sea_9_6(self):
        gm = GrammarMatcher(grammar=self.sea_grammar_6)

        for g in (
                self.sea_9_x,
        ):
            # print('using grid:', g)
            matched_documents = gm.run_match(g)

            self.assertEqual(1, len(matched_documents))
            root = matched_documents[0]
            self.assertEqual((15, 15), root.box.size)

            children = root['field'].get_children()
            self.assertEqual(12, len(children))

            positions = [
                (m.box, 'has other:', m['other'].box)
                for m in children
            ]
            # print(*positions, sep=' \n')
            self.assertTrue(any(
                (t[0] == Box(26,6, 3,7)
                 and
                 t[2] == Box(16,6, 1,3))
                for t in positions
            ))

    def test_grid_sea_9_62(self):
        gm = GrammarMatcher(grammar=self.sea_grammar_62)

        for g in (
                self.sea_9_x,
        ):
            # print('using grid:', g)
            matched_documents = gm.run_match(g)

            self.assertEqual(1, len(matched_documents))
            root = matched_documents[0]
            self.assertEqual((17, 15), root.box.size)

            children = root['field'].get_children()
            self.assertEqual(13, len(children))

            positions = [
                (m.box, 'has other:', m['other'].box)
                for m in children
            ]
            # print(*positions, sep=' \n')
            self.assertTrue(any(
                (t[0] == Box(26,6, 3,7)
                 and
                 t[2] == Box(16,6, 1,3))
                for t in positions
            ))
            self.assertTrue(any(
                (t[0] == Box(12,7, 1,3)
                 and
                 t[2] == Box(16,6, 1,3))
                for t in positions
            ))
            self.assertTrue(any(
                (t[0] == Box(14,9, 1,3)
                 and
                 t[2] == Box(16,10, 1,3))
                for t in positions
            ))
            self.assertTrue(any(
                (t[0] == Box(24,14, 1,3)
                 and
                 t[2] == Box(24,2, 1,3))
                for t in positions
            ))

    def test_grid_vstu_week(self):
        gm = GrammarMatcher(grammar=self.vstu_grammar)

        for g in (
                self.grid_vstusched_week,
        ):
            # print('using grid:', g)
            matched_documents = gm.run_match(g)

            # month_days
            month_days_arr = gm.get_pattern_matches(gm.grammar['month_days'])
            pprint([
                (m.pattern.name, m.get_content())
                for m in month_days_arr])

            self.assertEqual(12, len(month_days_arr))

    def test_grid_vstu_fevt3(self):
        gm = GrammarMatcher(grammar=self.vstu_grammar)

        for g in (
                self.grid_vstu_fevt3,
        ):
            # print('using grid:', g)
            matched_documents = gm.run_match(g)

            # view lesson instances
            # for p in gm.grammar.patterns.values():
            p = gm.grammar['lesson']
            if p:
                matches = gm.get_pattern_matches(p)
                print('::', p.name, ':', len(matches), '::')
                pprint([m.get_content()
                    for m in matches])
                print()

            # pprint(matched_documents)
            # self.assertEqual(12, len(month_days_arr))


if __name__ == '__main__':
    # unittest.main()
    # GrammarMatchingTestCase._test_txt_debug(...)
    GrammarMatchingTestCase.setUpClass()
    GrammarMatchingTestCase.test_grid2_4(GrammarMatchingTestCase())
