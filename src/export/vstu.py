import json
from datetime import datetime
from pathlib import Path
from typing import Mapping

from adict import adict

from converters.xlsx import ExcelGrid
from grammar2d import Grammar, GrammarMatcher, read_grammar
from grammar2d.Match2d import Match2d
from grid import Grid
from services import DocumentParsingService
from services.debugging.wave_exporter import WaveDebugExporter
from utils import Checkpointer, time_report


def xls_to_json(xlsx_path: str):
    # with time_report('Whole process') as ch:
    ch = Checkpointer()

    grid = read_schedule_xls(xlsx_path)
    ch.hit('Excel grid loaded')

    vstu_grammar = read_grammar('../cnf/grammar_root.yml')
    ch.hit('VSTU grammar loaded')

    doc, service = extract_schedule_data(grid, vstu_grammar, inspect=True)
    ch.hit('Schedule data extracted')

    # Сохраняем сырые данные для анализа
    save_raw_document_data(doc)
    ch.hit('Raw document data saved')

    export_schedule_document_as_json(doc)
    ch.hit('Schedule data exported')

    ch.since_start('... Whole process took')

def read_schedule_xls(xlsx_path: str) -> Grid:
    return ExcelGrid.read_xlsx(Path(xlsx_path))

def extract_schedule_data(grid: Grid, vstu_grammar: Grammar, inspect=False) -> tuple[Match2d, DocumentParsingService]:
    """Извлекает данные расписания используя DocumentParsingService.
    
    Returns:
        tuple[Match2d, DocumentParsingService]: Разобранный документ и сервис парсинга
    """
    service = DocumentParsingService(grammar=vstu_grammar)
    matched_documents = service.parse_document(grid)

    if inspect:
        _inspect_match_and_warn(matched_documents[0], service.matcher)

    return matched_documents[0], service

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


def save_raw_document_data(matched_document: Match2d, output_dir: Path = Path('../data')) -> Path:
    """Сохраняет сырые данные разобранного документа в JSON.
    
    Сохраняет два формата:
    - Полный формат: сериализация Match2d со всеми компонентами
    - Компактный формат: результат get_content() для корневого документа
    
    Args:
        matched_document: Разобранный документ (Match2d)
        output_dir: Директория для сохранения файлов
        
    Returns:
        Path: Путь к сохранённому файлу
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_path = output_dir / f'raw_document_{timestamp}.json'
    
    # Полный формат: рекурсивная сериализация Match2d
    def serialize_match_recursive(match: Match2d) -> dict:
        """Рекурсивно сериализует Match2d со всеми компонентами."""
        component_entries = []
        
        if match.component2match:
            for name, child in match.component2match.items():
                component_entries.append({
                    "name": str(name),
                    "pattern": child.pattern.name,
                    "box": _box_dict(child.box),
                    "match": serialize_match_recursive(child)  # Рекурсивно сериализуем дочерние элементы
                })
        
        precision = match.precision if match.precision is not None else match.calc_precision()
        text_items = match.get_text()
        text_content = WaveDebugExporter._normalize_text_content(text_items)
        
        return {
            "pattern": match.pattern.name,
            "precision": precision,
            "box": _box_dict(match.box),
            "text_content": text_content,
            "component_count": len(component_entries),
            "components": component_entries,
        }
    
    # Компактный формат: get_content()
    compact_content = matched_document.get_content(include_position=False)
    
    # Сохраняем оба формата
    data = {
        "timestamp": timestamp,
        "full_format": serialize_match_recursive(matched_document),
        "compact_format": compact_content,
    }
    
    with open(output_path, 'w', encoding='utf8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"Raw document data saved to: {output_path}")
    return output_path


def _box_dict(box) -> Mapping:
    """Преобразует Box в словарь."""
    if not box:
        return {}
    return {
        "left": box.left,
        "top": box.top,
        "right": box.right,
        "bottom": box.bottom,
        "width": box.w,
        "height": box.h,
    }


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
    """Извлекает занятия из разобранного документа.
    
    Работает с новой структурой, где занятия представлены как frame_based_lesson.
    """
    group_names: list[str] = matched_document["table"]["groups"].get_content()["groups"]
    
    def resolve_groups(discipline_match: Match2d) -> list[str]:
        """Извлекает список групп из discipline_with_groups."""
        discipline_content = discipline_match.get_content()
        
        if isinstance(discipline_content, dict):
            if 'group' in discipline_content:
                name = discipline_content['group']['group']
                return [name]
            if 'first_group' in discipline_content and 'last_group' in discipline_content:
                i = group_names.index(discipline_content['first_group']['group'])
                j = group_names.index(discipline_content['last_group']['group'])
                return group_names[i : j+1]  # range
            # Попытка извлечь группы из структуры discipline_with_groups
            if 'groups' in discipline_content:
                return discipline_content['groups']
        
        raise ValueError(f"Cannot extract groups: unknown discipline format {discipline_content!r}")

    def extract_teachers(lesson_match: Match2d) -> list[str]:
        """Извлекает список преподавателей из урока."""
        teachers = []
        if 'teacher' in lesson_match:
            teacher_match = lesson_match['teacher']
            teacher_content = teacher_match.get_content()
            
            # teacher_burst может быть массивом
            if isinstance(teacher_content, list):
                for item in teacher_content:
                    if isinstance(item, dict) and 'teacher' in item:
                        teachers.append(plain(item['teacher']))
                    elif isinstance(item, str):
                        teachers.append(item)
            elif isinstance(teacher_content, dict):
                if 'teacher' in teacher_content:
                    teachers.append(plain(teacher_content['teacher']))
                # Может быть массивом через teacher_burst
                if 'teachers' in teacher_content:
                    for t in teacher_content['teachers']:
                        teachers.append(plain(t))
            elif isinstance(teacher_content, str):
                teachers.append(teacher_content)
        
        return teachers if teachers else []

    def extract_rooms(lesson_match: Match2d) -> list[str]:
        """Извлекает список аудиторий из урока."""
        rooms = []
        if 'room' in lesson_match:
            room_match = lesson_match['room']
            room_content = room_match.get_content()
            
            # room_burst может быть массивом
            if isinstance(room_content, list):
                for item in room_content:
                    if isinstance(item, dict) and 'room' in item:
                        rooms.append(plain(item['room']))
                    elif isinstance(item, str):
                        rooms.append(item)
            elif isinstance(room_content, dict):
                if 'room' in room_content:
                    rooms.append(plain(room_content['room']))
                # Может быть массивом через room_burst
                if 'rooms' in room_content:
                    for r in room_content['rooms']:
                        rooms.append(plain(r))
            elif isinstance(room_content, str):
                rooms.append(room_content)
        
        return rooms if rooms else []

    def extract_hours(lesson_match: Match2d) -> list[str]:
        """Извлекает часы занятия."""
        hours = []
        
        # Проверяем explicit_hours (переопределённые часы)
        if 'explicit_hours' in lesson_match:
            explicit_hours_match = lesson_match['explicit_hours']
            explicit_hours_content = explicit_hours_match.get_content()
            if isinstance(explicit_hours_content, dict) and 'hour_range' in explicit_hours_content:
                hours.append(plain(explicit_hours_content['hour_range']))
            elif isinstance(explicit_hours_content, str):
                hours.append(explicit_hours_content)
        
        # Если explicit_hours нет, извлекаем из frame
        if not hours and 'frame' in lesson_match:
            frame_match = lesson_match['frame']
            frame_content = frame_match.get_content()
            
            if isinstance(frame_content, dict):
                # Проверяем hour_1 (для занятий длиной в 1 пару)
                if 'hour_1' in frame_content:
                    hour_1_content = frame_content['hour_1']
                    if isinstance(hour_1_content, dict) and 'hour_range' in hour_1_content:
                        hours.append(plain(hour_1_content['hour_range']))
                    elif isinstance(hour_1_content, str):
                        hours.append(hour_1_content)
                # Проверяем hour_begin и hour_end (для занятий длиной в несколько пар)
                elif 'hour_begin' in frame_content and 'hour_end' in frame_content:
                    hour_begin = frame_content['hour_begin']
                    hour_end = frame_content['hour_end']
                    if isinstance(hour_begin, dict) and 'hour_range' in hour_begin:
                        hours.append(plain(hour_begin['hour_range']))
                    elif isinstance(hour_begin, str):
                        hours.append(hour_begin)
                    if isinstance(hour_end, dict) and 'hour_range' in hour_end:
                        hours.append(plain(hour_end['hour_range']))
                    elif isinstance(hour_end, str):
                        hours.append(hour_end)
        
        if not hours:
            raise ValueError(f"Cannot extract hours: unknown lesson format")
        
        return hours

    def extract_discipline(lesson_match: Match2d) -> tuple[str, list[str]]:
        """Извлекает название дисциплины и группы из frame->discipline."""
        if 'frame' not in lesson_match:
            raise ValueError("Lesson frame not found")
        
        frame_match = lesson_match['frame']
        if 'discipline' not in frame_match:
            raise ValueError("Discipline not found in frame")
        
        discipline_match = frame_match['discipline']
        discipline_content = discipline_match.get_content()
        
        # Извлекаем название дисциплины
        subject = ""
        if isinstance(discipline_content, dict):
            if 'discipline' in discipline_content:
                subject = plain(discipline_content['discipline'])
            elif 'discipline_name' in discipline_content:
                subject = plain(discipline_content['discipline_name'])
        
        # Извлекаем группы
        groups = resolve_groups(discipline_match)
        
        return subject, groups

    def extract_week_info(lesson_match: Match2d, grid_match: Match2d) -> tuple[int, str]:
        """Извлекает информацию о неделе и дне недели из контекста grid.
        
        В новой структуре информация о неделе и дне недели может быть:
        1. В outer контексте урока (но в грамматике это закомментировано)
        2. В позиции урока в grid относительно структуры datetime (weeks_calendar)
        3. В структуре grid как метаданные
        
        TODO: Нужно проанализировать сохранённые сырые данные (raw_document_*.json)
        чтобы определить точную структуру и доработать эту функцию.
        """
        # Временная заглушка - нужно будет доработать после анализа сырых данных
        # Пока возвращаем значения по умолчанию
        week_day_index = 0
        week = "first_week"
        
        # Попытка извлечь из позиции урока в grid
        # Можно попробовать определить по box урока относительно datetime структуры
        # Но это требует анализа сырых данных для понимания точной структуры
        return week_day_index, week

    def extract_explicit_dates(lesson_match: Match2d) -> list[str]:
        """Извлекает переопределённые даты из explicit_dates."""
        dates = []
        if 'explicit_dates' in lesson_match:
            explicit_dates_match = lesson_match['explicit_dates']
            explicit_dates_content = explicit_dates_match.get_content()
            
            if isinstance(explicit_dates_content, list):
                for item in explicit_dates_content:
                    if isinstance(item, dict) and 'date' in item:
                        dates.append(plain(item['date']))
                    elif isinstance(item, str):
                        dates.append(item)
            elif isinstance(explicit_dates_content, dict):
                if 'dates' in explicit_dates_content:
                    for d in explicit_dates_content['dates']:
                        dates.append(plain(d))
                elif 'date' in explicit_dates_content:
                    dates.append(plain(explicit_dates_content['date']))
        
        return dates

    out_lessons = []
    grid_match = matched_document['table']['grid']
    
    # В новой структуре grid - это массив Match2d объектов (уроков)
    lesson_matches = grid_match.get_children()
    
    for lesson_match in lesson_matches:
        try:
            # Извлекаем дисциплину и группы
            subject, groups = extract_discipline(lesson_match)
            
            # Извлекаем преподавателей
            teachers = extract_teachers(lesson_match)
            
            # Извлекаем аудитории
            rooms = extract_rooms(lesson_match)
            
            # Извлекаем часы
            hours = extract_hours(lesson_match)
            
            # Извлекаем информацию о неделе и дне недели
            week_day_index, week = extract_week_info(lesson_match, grid_match)
            
            # Извлекаем переопределённые даты
            explicit_dates = extract_explicit_dates(lesson_match)
            
            out_lessons.append({
                "subject": subject,
                "kind": "лекция",  # TODO: определить тип занятия из frame
                "participants": {
                    "teachers": teachers,
                    "student_groups": groups,
                },
                "places": rooms,
                "hours": hours,
                "week_day_index": week_day_index,
                "week": week,
                "holds_on_date": explicit_dates,
            })
        except Exception as e:
            print(f"Error extracting lesson: {e}")
            print(f"Lesson match pattern: {lesson_match.pattern.name}")
            print(f"Lesson content: {lesson_match.get_content()}")
            # Пропускаем проблемный урок, но продолжаем обработку остальных
            continue

    return out_lessons
