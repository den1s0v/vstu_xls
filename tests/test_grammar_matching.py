import unittest

from tests_bootstrapper import init_testing_environment

init_testing_environment()

from pathlib import Path

from converters.text import TxtGrid
from grammar2d import read_grammar, GrammarMatcher


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


if __name__ == '__main__':
    # unittest.main()
    GrammarMatchingTestCase.test_txt(...)
