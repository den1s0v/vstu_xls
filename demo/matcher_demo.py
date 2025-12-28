from importlib.resources import files
import sys
from pathlib import Path
from pprint import pprint

from loguru import logger

from vstuxls.converters.xlsx import ExcelGrid
from vstuxls.grammar2d import GrammarMatcher, read_grammar

if __name__ == '__main__':
    # redefine logging level defaulting to DEBUG
    logger.remove()
    logger.add(sys.stderr, level='INFO')

    lib_dir = files("vstuxls")
    grammar_path = Path(str(lib_dir)) / "cnf" / "grammar_root.yml"
    vstu_grammar = read_grammar(grammar_path)
    # grid_vstu_fevt4 = ExcelGrid.read_xlsx(Path('../tests/test_data/ОН_ФЭВТ_4 курс 2023.xlsx'))
    grid_vstu_feu3 = ExcelGrid.read_xlsx(Path('../tests/test_data/ОН_ФЭУ_3 курс.xlsx'))

    gm = GrammarMatcher(grammar=vstu_grammar)

    matched_documents = gm.run_match(grid_vstu_feu3)

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
