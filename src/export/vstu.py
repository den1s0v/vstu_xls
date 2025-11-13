import json
from pathlib import Path

from adict import adict

from converters.xlsx import ExcelGrid
from grammar2d import Grammar, GrammarMatcher, read_grammar
from grammar2d.Match2d import Match2d
from grid import Grid
from utils import Checkpointer, time_report


def xls_to_json(xlsx_path: str):
    # with time_report('Whole process') as ch:
    ch = Checkpointer()

    grid = read_schedule_xls(xlsx_path)
    ch.hit('Excel grid loaded')

    vstu_grammar = read_grammar('../cnf/grammar_root.yml')
    ch.hit('VSTU grammar loaded')

    doc = extract_schedule_data(grid, vstu_grammar, inspect=True)
    ch.hit('Schedule data extracted')

    export_schedule_document_as_json(doc)
    ch.hit('Schedule data exported')

    ch.since_start('... Whole process took')

def read_schedule_xls(xlsx_path: str) -> Grid:
    return ExcelGrid.read_xlsx(Path(xlsx_path))

def extract_schedule_data(grid: Grid, vstu_grammar: Grammar, inspect=False) -> Match2d:
    gm = GrammarMatcher(grammar=vstu_grammar)
    matched_documents = gm.run_match(grid)

    if inspect:
        _inspect_match_and_warn(matched_documents[0], gm)

    return matched_documents[0]

def _inspect_match_and_warn(doc: Match2d, gm: GrammarMatcher):
    from pprint import pprint

    for pattern_name in (
        # important intermediate stage of parsing
        'discipline_with_groups',
    ):
        p = gm.grammar[pattern_name]
        if p:
            matches = gm.find_unused_pattern_matches(doc, p)
            if not matches:
                continue
            print('!!! UNUSED ::', p.name, ':', len(matches), 'matches ::')
            for m in matches:
                print('UNUSED ::', pattern_name)
                pprint(m.get_content())
                print('  precision=', m.precision)
                print()
            print()
            print()


def plain(s: str | list[str]) -> str:
    """ Ensure value is plain string """
    if isinstance(s, str):
        return s
    elif isinstance(s, list):
        return ''.join(s)
    else:
        return str(s)

def export_schedule_document_as_json(matched_document: Match2d, dst_path: str = '../data/import.json'):
    """
    The doc must be matched with grammar_root grammar.
    Output is adopted for VSTU-Schedule / api.utilities.ImportAPI.import_data.
    """
    out = adict()

    out.title = plain(matched_document['title'].get_text())

    out.table = adict({
        'grid': [],
        'datetime': adict({
            "weeks": {},
			"week_days": [
				"ПОНЕДЕЛЬНИК",
				"ВТОРНИК",
				"СРЕДА",
				"ЧЕТВЕРГ",
				"ПЯТНИЦА",
				"СУББОТА"
			],
			"months": [
				# "февраль",
				# "март",
				# "апрель",
				# "май",
				# "июнь",
				"сентябрь",
				"октябрь",
				"ноябрь",
				"декабрь",
			],
        }),
    })

    #
    grid = out.table['grid']
    weeks = out.table['datetime'].weeks

    ...

    # save to disk
    with open(dst_path, 'w', encoding='utf8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"Export success! \n File: {dst_path}")
