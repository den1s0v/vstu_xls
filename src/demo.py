from pathlib import Path
from pprint import pprint
import sys

from loguru import logger

from converters.xlsx import ExcelGrid
from grammar2d import read_grammar, GrammarMatcher


if __name__ == '__main__':
    # redefine logging level defaulting to DEBUG
    logger.remove()
    logger.add(sys.stderr, level='INFO')


    vstu_grammar = read_grammar('../cnf/grammar_root.yml')
    grid_vstu_fevt4 = ExcelGrid.read_xlsx(Path('../tests/test_data/ОН_ФЭВТ_4 курс 2023.xlsx'))

    gm = GrammarMatcher(grammar=vstu_grammar)

    # print('using grid:', grid_vstu_fevt4)
    matched_documents = gm.run_match(grid_vstu_fevt4)

    # view lesson instances
    ## for p in gm.grammar.patterns.values():
    p = gm.grammar['lesson']
    if p:
        matches = gm.get_pattern_matches(p)
        print('::', p.name, ':', len(matches), 'matches ::')
        pprint([m.get_content()
                for m in matches])
        print()

    print('End of the demo.')
