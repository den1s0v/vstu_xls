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
			"week_days": LOOKUP.WEEK_DAYS,
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
    # weeks = out.table['datetime'].weeks
    out.table['datetime'].weeks = _extract_weeks(matched_document['table']['datetime'])

    out.table['grid'] = _extract_lessons(matched_document)

    # save to disk
    with open(dst_path, 'w', encoding='utf8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"Export success! \n File: {dst_path}")




LOOKUP = adict()

LOOKUP.WEEK_DAYS = [
				"ПОНЕДЕЛЬНИК",
				"ВТОРНИК",
				"СРЕДА",
				"ЧЕТВЕРГ",
				"ПЯТНИЦА",
				"СУББОТА"
			]
LOOKUP.name_of_week = {
        1: "first_week",
        2: "second_week",
    }.get

def index_of_weekday(name: str) -> int:
        assert name in LOOKUP.WEEK_DAYS, f"{name} not in {LOOKUP.WEEK_DAYS}"
        return LOOKUP.WEEK_DAYS.index(name)
LOOKUP.index_of_weekday = index_of_weekday

def _extract_weeks(datatime_match: Match2d) -> list[dict]:

    month_names: list[str] = datatime_match["month_names"].get_content()
    def index_of_month(name: str) -> int:
        assert name in month_names, f"{name} not in {month_names}"
        return month_names.index(name)


    def make_calendar_for_weekday(month_days_match: Match2d) -> list[dict]:
        out_calendar = []
        def add(month: str, day_number: str):
            month_index = index_of_month(month)
            for calendar_month_info in out_calendar:
                if calendar_month_info['month_index'] == month_index:
                    # дописываем в список дней месяца
                    calendar_month_info['month_days'].append(day_number)
                    break
            else:
                out_calendar.append({
                    'month_index': month_index,
                    'month_days': [day_number],  # init list
                })
            return out_calendar

        for month_days in month_days_match["month_days"].get_children():  ### .get_content():
            for month_day in month_days.get_children():
                add(
                    plain(month_day["month_name"].get_text()),
                    plain(month_day["month_day"].get_text())
                )
        return out_calendar

    out_weeks = []
    for week in datatime_match["weeks"].get_children():
        out_weeks.append({
            LOOKUP.name_of_week(week.get_content()["@index_in_array"]): [
                # days in week
                {
                    "week_day_index": LOOKUP.index_of_weekday(plain(day["week_day"].get_text())),

                    # month days for this weekday
                    "calendar": make_calendar_for_weekday(day),
                }
                for day in week["days"].get_children()
            ]
        })

    return out_weeks

def _extract_lessons(matched_document: Match2d) -> list[dict]:

    group_names: list[str] = matched_document["table"]["groups"].get_content()["groups"]
    def resolve_groups(discipline_info: dict) -> list[str]:
        if 'group' in discipline_info:
            name = discipline_info['group']['group']
            return [name]
        if 'first_group' in discipline_info and 'last_group' in discipline_info:
            i = group_names.index(discipline_info['first_group']['group'])
            j = group_names.index(discipline_info['last_group']['group'])
            return group_names[i : j+1]  # range
        else:
            raise ValueError(f"Сannot extract groups: unknown discipline format {discipline_info!r}")

    def resolve_hours(lesson_info: dict) -> list[str]:
        if 'hour_1' in lesson_info:
            hour_1 = lesson_info['hour_1']['hour_range']
            return [hour_1]
        if 'hour_begin' in lesson_info and 'hour_end' in lesson_info:
            return [
                lesson["hour_begin"]["hour_range"],
                lesson["hour_end"]["hour_range"],
            ]
        else:
            raise ValueError(f"Cannot extract hours: unknown lesson format {lesson_info!r}")

    out_lessons = []

    lesson: dict
    for lesson in matched_document['table']['grid'].get_content():
        out_lessons.append({
            "subject": plain(lesson['discipline']['discipline']),
            "kind": "лекция",  # TODO
            "participants": {
                "teachers": [
                    lesson['teacher']  # пока только один
                ],
                "student_groups": resolve_groups(lesson['discipline'])  # инфа о группах лежит у дисциплины.
            },
            "places": [
                lesson['room']  # пока только один
            ],
            "hours": resolve_hours(lesson),
            "week_day_index": LOOKUP.index_of_weekday(lesson['week_day']),
            "week": LOOKUP.name_of_week(lesson['week']["@index_in_array"]),
            "holds_on_date": [
                # "09.11.2024"  # TODO
            ]
        })

    return out_lessons
