import contextlib
import json
import re
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path

from adict import adict

from vstuxls.converters.xlsx import ExcelGrid
from vstuxls.grammar2d import Grammar, GrammarMatcher, read_grammar
from vstuxls.grammar2d.Match2d import Match2d
from vstuxls.grid import Grid
from vstuxls.services import DocumentParsingService
from vstuxls.services.debugging.wave_exporter import WaveDebugExporter
from vstuxls.utils import Checkpointer

CURRENT_ACADEMIC_YEAR = "2025-2026"
CURRENT_SEMESTER = "2"
CURRENT_SEMESTER_START_DATE = "09.02.2026"
CURRENT_SEMESTER_END_DATE = "30.06.2026"


def xls_to_json(xlsx_path: str):
    # with time_report('Whole process') as ch:
    ch = Checkpointer()

    grid = read_schedule_xls(xlsx_path)
    ch.hit('Excel grid loaded')

    vstu_grammar = read_grammar('../cnf/grammar_root.yml')
    ch.hit('VSTU grammar loaded')

    doc, _service = extract_schedule_data(grid, vstu_grammar, inspect=True)
    ch.hit('Schedule data extracted')

    if 0:
        # Сохраняем сырые данные для анализа
        save_raw_document_data(doc)
        ch.hit('Raw document data saved')

    export_schedule_document_as_json(doc, source_path=Path(xlsx_path))
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


def _parse_year_bounds(years_text: str | None) -> tuple[int, int]:
    m = re.search(r"(\d{4})\s*-\s*(\d{4})", years_text or "")
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.search(r"(\d{4})\s*[—–-]\s*(\d{4})", years_text or "")
    if m:
        return int(m.group(1)), int(m.group(2))
    # fallback на текущий учебный год
    left, right = CURRENT_ACADEMIC_YEAR.split("-", 1)
    return int(left), int(right)


def _normalize_faculty_spelling(text: str) -> str:
    s = text
    # Единообразно используем верхний регистр
    s = re.sub(r"(?i)фастив", "ФАСТИВ", s)
    return s


def _detect_faculty_shortname(text: str) -> str:
    if not text:
        return ""
    upper_text = _normalize_faculty_spelling(text).upper()
    aliases: list[tuple[str, str]] = [
        ("ФЭВТ", "ФЭВТ"),
        ("ХТФ", "ХТФ"),
        ("ХФ", "ХТФ"),
        ("ФЭУ", "ФЭУ"),
        ("ФТПП", "ФТПП"),
        ("ФАТ", "ФАТ"),
        ("ФАСТИВ", "ФАСТИВ"),
        ("ФТКМ", "ФТКМ"),
        ("ВМЦЭ", "ВМЦЭ"),
    ]
    for token, normalized in aliases:
        if token in upper_text:
            return normalized
    return ""


def _normalize_title(original_title: str, scope_word: str | None, current_semester = CURRENT_SEMESTER) -> str:
    title = (original_title or "").strip()
    if not title:
        return ""

    title = title.replace("магистров", "магистратура").replace("Магистров", "магистратура")
    title = _normalize_faculty_spelling(title)

    # Нормализуем диапазон учебного года в заголовке.
    title = re.sub(r"\b20\d{2}\s*[—–-]\s*20\d{2}\b", CURRENT_ACADEMIC_YEAR, title)
    # Встречается "1 семестр" в файлах 2-го семестра: аккуратно приводим к текущему.
    # Заменяем "1-й семестр", "2й семестр", "2 семестр" -> "<CURRENT> семестр"
    title = re.sub(r"\b\d\s*[-й]*\s*семестр\b", f"{current_semester} семестр", title, flags=re.IGNORECASE)

    scopes = ("бакалавриат", "магистратура", "аспирантура")
    normalized_scope = (scope_word or "").strip()
    lower_title = title.lower()

    if normalized_scope and any(s in lower_title for s in scopes):
        if "бакалавриат" in lower_title and "магистратура" in lower_title and normalized_scope.lower() in ("бакалавриат", "магистратура"):
            # Если в заголовке смешаны scope, оставляем только целевой.
            cleaned = title
            for s in scopes:
                cleaned = re.sub(rf"\b{s}\b", "", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" ,;")
            title = f"{cleaned} {normalized_scope}".strip()
        elif normalized_scope.lower() not in lower_title:
            title = f"{title} {normalized_scope}".strip()
    elif normalized_scope and normalized_scope.lower() not in lower_title:
        title = f"{title} {normalized_scope}".strip()

    return re.sub(r"\s{2,}", " ", title).strip()


def _normalize_single_date(raw_value: str, years_hint: str) -> list[str]:
    raw = (raw_value or "").strip()
    if not raw:
        return []

    left_year, right_year = _parse_year_bounds(years_hint)

    def resolve_year(month: int) -> int:
        return left_year if month > 6 else right_year

    # Склейка вида 16.04.17.05 -> 16.04, 17.05
    m_glued = re.fullmatch(r"(\d{1,2}\.\d{1,2})\.(\d{1,2}\.\d{1,2})", raw)
    if m_glued:
        return _normalize_single_date(m_glued.group(1), years_hint) + _normalize_single_date(m_glued.group(2), years_hint)

    # Формат вида dd.yyyy.mm -> dd.mm.yyyy
    m_dym = re.fullmatch(r"(\d{1,2})\.(\d{4})\.(\d{1,2})", raw)
    if m_dym:
        day, year, month = m_dym.groups()
        raw = f"{day}.{month}.{year}"

    m_full = re.fullmatch(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", raw)
    if m_full:
        day_i = int(m_full.group(1))
        month_i = int(m_full.group(2))
        year_i = int(m_full.group(3))
        if 1 <= day_i <= 31 and 1 <= month_i <= 12:
            return [f"{day_i:02d}.{month_i:02d}.{year_i:04d}"]
        # Частая инверсия month/day: 12.15.2025 -> 15.12.2025
        if 1 <= day_i <= 12 and 13 <= month_i <= 31:
            return [f"{month_i:02d}.{day_i:02d}.{year_i:04d}"]
        return []

    m_partial = re.fullmatch(r"(\d{1,2})\.(\d{1,2})", raw.rstrip("."))
    if m_partial:
        day_i = int(m_partial.group(1))
        month_i = int(m_partial.group(2))
        if 1 <= day_i <= 31 and 1 <= month_i <= 12:
            return [f"{day_i:02d}.{month_i:02d}.{resolve_year(month_i):04d}"]
        return []

    return []


def _normalize_dates_list(values: list[str], years_hint: str) -> list[str]:
    out: list[str] = []
    for value in values:
        for token in re.split(r"[;,]|\.\.+|\s+", value or ""):
            token = token.strip()
            if not token:
                continue
            out.extend(_normalize_single_date(token, years_hint))

    # preserve order + deduplicate
    seen: set[str] = set()
    result: list[str] = []
    for d in out:
        if d not in seen:
            seen.add(d)
            result.append(d)
    return result


def _cleanup_teacher_name(name: str) -> str:
    cleaned = (name or "").strip()
    cleaned = re.sub(r"\.{2,}", ".", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    return cleaned.strip(" ;,")


def _extract_dates_from_place(value: str, years_hint: str) -> tuple[list[str], str]:
    text = (value or "").strip()
    if not text:
        return [], ""
    # Ищем явные фрагменты дат и убираем их из places.
    date_like = re.findall(r"\d{1,2}\.\d{1,2}(?:\.\d{4})?", text)
    dates = _normalize_dates_list(date_like, years_hint) if date_like else []
    if dates:
        cleaned = re.sub(r"\d{1,2}\.\d{1,2}(?:\.\d{4})?", " ", text)
        cleaned = re.sub(r"[;,.]{2,}", " ", cleaned)
        cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" ,;")
        if re.fullmatch(r"\d+", cleaned or ""):
            cleaned = ""
        return dates, cleaned
    return [], text


def apply_post_fixes(out: adict, metadata: dict | None = None) -> adict:
    years_hint = (metadata or {}).get("years") or CURRENT_ACADEMIC_YEAR
    scope_word = (metadata or {}).get("scope") if metadata else None

    # Нормализуем title
    out["title"] = _normalize_title(str(out.get("title", "")), scope_word)

    # Нормализуем lessons
    grid = out.get("table", {}).get("grid", [])
    for lesson in grid:
        participants = lesson.get("participants", {})
        teachers = participants.get("teachers", [])
        participants["teachers"] = [_cleanup_teacher_name(t) for t in teachers if str(t).strip()]
        lesson["participants"] = participants

        holds = lesson.get("holds_on_date", []) or []
        if isinstance(holds, list):
            holds_norm = _normalize_dates_list([str(x) for x in holds], years_hint)
        else:
            holds_norm = _normalize_dates_list([str(holds)], years_hint)

        new_places: list[str] = []
        extra_dates: list[str] = []
        for place in lesson.get("places", []) or []:
            found_dates, cleaned_place = _extract_dates_from_place(str(place), years_hint)
            extra_dates.extend(found_dates)
            if cleaned_place:
                new_places.append(cleaned_place)
        lesson["places"] = new_places
        lesson["holds_on_date"] = _normalize_dates_list(holds_norm + extra_dates, years_hint)

    return out


def build_schedule_metadata(source_path: Path | None, original_title: str | None) -> dict:
    """Формирует объект метаданных расписания для поля `title` в JSON.

    Формат соответствует `materials/schedule_reference_import.json`:
        {
            "course": "4",
            "schedule_template_metadata_faculty_shortname": "ФЭВТ",
            "semester": "1",
            "years": "2025-2026",
            "start_date": "01.09.2025",
            "end_date": "01.02.2026",
            "scope": "бакалавриат" | "магистратура",
            "department_shortname": "ФЭВТ"
        }
    """
    # из констант в начале файла
    years = CURRENT_ACADEMIC_YEAR
    semester = CURRENT_SEMESTER
    start_date = CURRENT_SEMESTER_START_DATE
    end_date = CURRENT_SEMESTER_END_DATE

    # Безопасно нормализуем путь
    path = source_path.resolve() if isinstance(source_path, Path) else None

    # 1) Определяем scope по частям пути и/или по тексту заголовка
    scope = "бакалавриат"
    if path:
        parts_lower = [p.lower() for p in path.parts]
        for part in parts_lower:
            if "магистратура" in part:
                scope = "магистратура"
                break
            if "аспирантура" in part:
                scope = "Аспирантура"
                break

    if original_title:
        t = original_title.lower()
        if "магистратура" in t:
            scope = "магистратура"
        elif "аспирантура" in t:
            scope = "Аспирантура"

    # 2) Определяем факультет по имени файла
    faculty = None
    filename = ""
    if path:
        filename = path.name
    elif original_title:
        filename = original_title

    faculty = _detect_faculty_shortname(filename)

    # Если не нашли, можно попытаться взять из title или оставить пустым
    if not faculty and original_title:
        faculty = _detect_faculty_shortname(original_title)

    if faculty is None:
        faculty = ""

    # 3) Курс — первая цифра в имени файла
    course = "1"
    for ch in filename:
        if ch.isdigit():
            course = ch
            break

    return {
        "course": course,
        "schedule_template_metadata_faculty_shortname": faculty,
        "semester": semester,
        "years": years,
        "start_date": start_date,
        "end_date": end_date,
        "scope": scope,
        "department_shortname": faculty,
        "original_title": original_title or "",
    }

def plain(s: str | list[str]) -> str:
    """ Ensure value is plain string """
    if isinstance(s, str):
        return s
    elif isinstance(s, list):
        # Безопасно конкатенируем элементы, приводя не-строки к строке
        parts: list[str] = []
        for item in s:
            if isinstance(item, str):
                parts.append(item)
            else:
                parts.append(str(item))
        return ''.join(parts)
    else:
        return str(s)


def export_schedule_document_as_json(
    matched_document: Match2d,
    dst_path: str = '../data/import.json',
    source_path: Path | None = None,  # оставляем для совместимости и возможного использования
) -> None:
    """
    The doc must be matched with grammar_root grammar.
    Output is adopted for VSTU-Schedule / api.utilities.ImportAPI.import_data.
    """
    out = adict()

    # Для EventImporter ожидается строковый title
    original_title = plain(matched_document['title'].get_text())
    metadata = None
    if source_path is not None:
        try:
            metadata = build_schedule_metadata(source_path, original_title)
        except Exception:
            metadata = None

    out.title = _normalize_title(original_title, (metadata or {}).get("scope"))

    # Подготовка структуры таблицы
    out.table = adict({
        'grid': [],
        'datetime': adict({
            "weeks": {},          # заполним ниже
            "week_days": LOOKUP.WEEK_DAYS,
            "months": [],         # заполним ниже
        }),
    })

    # Извлекаем weeks и список имён месяцев из datetime-раздела документа
    weeks, months = _extract_weeks(matched_document['table']['datetime'])
    out.table['datetime'].weeks = weeks
    out.table['datetime'].months = months

    out.table['grid'] = _extract_lessons(matched_document, years=(metadata or {}).get("years", CURRENT_ACADEMIC_YEAR))
    out = apply_post_fixes(out, metadata=metadata)

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

def _extract_weeks(datatime_match: Match2d) -> tuple[dict, list[str]]:
    """Формирует структуру `weeks` и список месяцев в формате, ожидаемом ImportAPI.

    Возвращает:
        weeks: dict вида {"first_week": [...], "second_week": [...]}
        months: список названий месяцев в порядке их появления
    """
    # Список имён месяцев, распознанных грамматикой
    month_names: list[str] = datatime_match["month_names"].get_content()

    def index_of_month(name: str) -> int:
        assert name in month_names, f"{name} not in {month_names}"
        return month_names.index(name)

    def make_calendar_for_weekday(month_days_match: Match2d) -> list[dict]:
        out_calendar: list[dict] = []

        def add(month: str, day_number: str):
            month_index = index_of_month(month)
            for calendar_month_info in out_calendar:
                if calendar_month_info['month_index'] == month_index:
                    calendar_month_info['month_days'].append(day_number)
                    break
            else:
                out_calendar.append({
                    'month_index': month_index,
                    'month_days': [day_number],
                })
            return out_calendar

        for month_days in month_days_match["month_days"].get_children():
            for month_day in month_days.get_children():
                add(
                    plain(month_day["month_name"].get_text()),
                    plain(month_day["month_day"].get_text()),
                )
        return out_calendar

    # Целевая структура:
    # "weeks": {
    #   "first_week": [ {week_day_index, calendar}, ... ],
    #   "second_week": [ ... ]
    # }
    out_weeks: dict[str, list[dict]] = {}

    for week in datatime_match["weeks"].get_children():
        content = week.get_content()
        week_index = content.get("@index_in_array")
        week_name = LOOKUP.name_of_week(week_index)
        if not week_name:
            continue

        days_info = [
            {
                "week_day_index": LOOKUP.index_of_weekday(plain(day["week_day"].get_text())),
                "calendar": make_calendar_for_weekday(day),
            }
            for day in week["_days"].get_children()
        ]

        # Накопим все дни для каждой недели в один список
        out_weeks.setdefault(week_name, []).extend(days_info)

    return out_weeks, month_names

def _extract_lessons(matched_document: Match2d, years: str | None = None) -> list[dict]:
    """Извлекает занятия из разобранного документа.

    Работает с новой структурой, где занятия представлены как frame_based_lesson.
    """
    group_names: list[str] = matched_document["table"]["groups"].get_content()["groups"]

    def resolve_groups(discipline_match: Match2d) -> list[str]:
        """Извлекает список групп из discipline_with_groups."""
        discipline_content = discipline_match.get_content()

        def _append_group_value(raw_value, into: list[str]) -> None:
            if isinstance(raw_value, str):
                if raw_value.strip():
                    into.append(raw_value.strip())
            elif isinstance(raw_value, dict) and "group" in raw_value:
                _append_group_value(raw_value["group"], into)

        def _collect_groups_from_content(content, into: list[str]) -> None:
            if isinstance(content, dict):
                if "group" in content:
                    _append_group_value(content["group"], into)
                if "groups" in content and isinstance(content["groups"], list):
                    for g in content["groups"]:
                        _append_group_value(g, into)
                if "first_group" in content and "last_group" in content:
                    first = content["first_group"]
                    last = content["last_group"]
                    if isinstance(first, dict) and isinstance(last, dict) and "group" in first and "group" in last:
                        try:
                            i = group_names.index(first["group"])
                            j = group_names.index(last["group"])
                            into.extend(group_names[i: j + 1])
                        except ValueError:
                            pass
                # fallback: разворачиваем словари вида m1/m2/...
                for key, value in content.items():
                    if re.fullmatch(r"m\d+", str(key)):
                        _collect_groups_from_content(value, into)
            elif isinstance(content, list):
                for item in content:
                    _collect_groups_from_content(item, into)

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
            collected: list[str] = []
            _collect_groups_from_content(discipline_content, collected)
            if collected:
                # preserve order + deduplicate
                seen: set[str] = set()
                out: list[str] = []
                for g in collected:
                    if g not in seen:
                        seen.add(g)
                        out.append(g)
                return out

        raise ValueError(f"Cannot extract groups: unknown discipline format {discipline_content!r}")

    def extract_teachers(lesson_match: Match2d) -> list[str]:
        """Извлекает список преподавателей из урока."""
        teachers = []
        if 'teacher' in lesson_match:
            teacher_match = lesson_match['teacher']
            teacher_content = teacher_match.get_content()

            # teacher_burst может быть массивом строк
            if isinstance(teacher_content, list):
                for item in teacher_content:
                    if isinstance(item, str):
                        # Фильтруем пустые строки
                        if item.strip():
                            teachers.append(item.strip())
                    elif isinstance(item, dict) and 'teacher' in item:
                        teachers.append(plain(item['teacher']))
            elif isinstance(teacher_content, dict):
                if 'teacher' in teacher_content:
                    teachers.append(plain(teacher_content['teacher']))
                # Может быть массивом через teacher_burst
                if 'teachers' in teacher_content:
                    for t in teacher_content['teachers']:
                        if isinstance(t, str) and t.strip():
                            teachers.append(t.strip())
                        else:
                            teachers.append(plain(t))
            elif isinstance(teacher_content, str) and teacher_content.strip():
                teachers.append(teacher_content.strip())

        # Также проверяем frame.teacher (может быть строка)
        if not teachers and 'frame' in lesson_match:
            frame_match = lesson_match['frame']
            frame_content = frame_match.get_content()
            if isinstance(frame_content, dict) and 'teacher' in frame_content:
                teacher_str = frame_content['teacher']
                if isinstance(teacher_str, str) and teacher_str.strip():
                    teachers.append(teacher_str.strip())

        return teachers if teachers else []

    def extract_rooms(lesson_match: Match2d) -> list[str]:
        """Извлекает список аудиторий из урока."""
        rooms = []
        if 'room' in lesson_match:
            room_match = lesson_match['room']
            room_content = room_match.get_content()

            # room_burst может быть массивом строк
            if isinstance(room_content, list):
                for item in room_content:
                    if isinstance(item, str):
                        # Фильтруем пустые строки
                        if item.strip():
                            rooms.append(item.strip())
                    elif isinstance(item, dict) and 'room' in item:
                        rooms.append(plain(item['room']))
            elif isinstance(room_content, dict):
                if 'room' in room_content:
                    rooms.append(plain(room_content['room']))
                # Может быть массивом через room_burst
                if 'rooms' in room_content:
                    for r in room_content['rooms']:
                        if isinstance(r, str) and r.strip():
                            rooms.append(r.strip())
                        else:
                            rooms.append(plain(r))
            elif isinstance(room_content, str) and room_content.strip():
                rooms.append(room_content.strip())

        # Также проверяем frame.room (может быть строка)
        if not rooms and 'frame' in lesson_match:
            frame_match = lesson_match['frame']
            frame_content = frame_match.get_content()
            if isinstance(frame_content, dict) and 'room' in frame_content:
                room_str = frame_content['room']
                if isinstance(room_str, str) and room_str.strip():
                    rooms.append(room_str.strip())

        # Лёгкая нормализация: устраняем «разрывы» вида `Б--514` → `Б-514`
        def _normalize_room(r: str) -> str:
            s = r.strip()
            # схлопываем повторяющиеся дефисы
            while "--" in s:
                s = s.replace("--", "-")
            return s

        rooms = [_normalize_room(r) for r in rooms] if rooms else []
        return rooms

    def extract_kind(lesson_match: Match2d, hours: list[str]) -> str:
        """Определяет тип занятия (лекция / практика / лабораторная).

        Источники (в порядке приоритета):
        - frame._explicit_lesson_kind (lesson_kind_* из грамматики)
        - lesson_match.lesson_kind / lesson_match._explicit_lesson_kind (если появятся в будущих версиях)

        Если распознать тип не удалось, по умолчанию возвращаем «лекция».
        """

        def _raw_kind_text() -> str | None:
            # 1) Явный тип внутри frame: _explicit_lesson_kind
            if 'frame' in lesson_match:
                frame_match = lesson_match['frame']
                if isinstance(frame_match, Match2d) and '_explicit_lesson_kind' in frame_match:
                    return plain(frame_match['_explicit_lesson_kind'].get_text())

            # 2) Возможные прямые поля на верхнем уровне урока
            for key in ('lesson_kind', '_explicit_lesson_kind'):
                if key in lesson_match:
                    km = lesson_match[key]
                    if isinstance(km, Match2d):
                        return plain(km.get_text())

            return None

        text = _raw_kind_text()
        if text:
            t = text.lower()
            # Нормализуем по ключевым подстрокам
            if 'лаб' in t:
                return 'лабораторная работа'
            if 'пр.' in t or 'практ' in t:
                return 'практика'
            if 'лек' in t:
                return 'лекция'

        # Если явный текст не дал результата — пробуем вывести тип из структуры
        box = lesson_match.box
        height = box.h if box else None
        hour_ranges = len(hours or [])

        # 4 академических часа: обычно 2 hour_range и около 6 строк высоты
        if hour_ranges >= 2 and height is not None and height >= 6:
            return 'лабораторная работа'

        # 2 академических часа: один hour_range и ~3 строки высоты
        if hour_ranges == 1 and height is not None and 3 <= height <= 4:
            return 'лекция'

        # По умолчанию считаем, что это лекция
        return 'лекция'

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
                # Проверяем hour_begin в frame (может быть один час или начало диапазона)
                if 'hour_begin' in frame_content:
                    hour_begin = frame_content['hour_begin']
                    if isinstance(hour_begin, dict) and 'hour_range' in hour_begin:
                        hours.append(plain(hour_begin['hour_range']))
                    elif isinstance(hour_begin, str):
                        hours.append(hour_begin)

                # Проверяем hour_end (для занятий длиной в несколько пар)
                if 'hour_end' in frame_content:
                    hour_end = frame_content['hour_end']
                    if isinstance(hour_end, dict) and 'hour_range' in hour_end:
                        hours.append(plain(hour_end['hour_range']))
                    elif isinstance(hour_end, str):
                        hours.append(hour_end)

                # Проверяем hour_1 (для занятий длиной в 1 пару) - альтернативный вариант
                if not hours and 'hour_1' in frame_content:
                    hour_1_content = frame_content['hour_1']
                    if isinstance(hour_1_content, dict) and 'hour_range' in hour_1_content:
                        hours.append(plain(hour_1_content['hour_range']))
                    elif isinstance(hour_1_content, str):
                        hours.append(hour_1_content)

                # Также проверяем в frame.discipline.hour_begin
                if not hours and 'discipline' in frame_content:
                    discipline_content = frame_content['discipline']
                    if isinstance(discipline_content, dict) and 'hour_begin' in discipline_content:
                        hour_begin = discipline_content['hour_begin']
                        if isinstance(hour_begin, dict) and 'hour_range' in hour_begin:
                            hours.append(plain(hour_begin['hour_range']))
                        elif isinstance(hour_begin, str):
                            hours.append(hour_begin)

        if not hours:
            raise ValueError("Cannot extract hours: unknown lesson format")

        return hours

    def normalize_hour_ranges(hours: list[str]) -> list[str]:
        """Нормализует список описаний часов в список alt_name-диапазонов пар (`1-2`, `3-4`, ...).

        Поддерживаем варианты:
        - уже нормальные alt_name: `1-2`, `3 - 4`
        - текстовые диапазоны: `5 - 8 час.`, `5-8`, `5 - 8 час`
        Логика:
        - если в строке два числа (start, end) и end == start + 1 → одна пара: `start-end`
        - если end > start и (end - start + 1) чётно → разбиваем на пары:
          5-8 → `5-6`, `7-8`; 1-4 → `1-2`, `3-4`
        """
        result: list[str] = []

        for raw in hours:
            if not raw:
                continue

            s = raw.strip()

            # Уже alt_name без лишних суффиксов
            if re.fullmatch(r"\d{1,2}\s*-\s*\d{1,2}", s):
                # Нормализуем пробелы
                a, b = [p.strip() for p in s.split("-", 1)]
                result.append(f"{int(a)}-{int(b)}")
                continue

            # Выделяем все числа
            nums = [int(n) for n in re.findall(r"\d+", s)]
            if len(nums) == 2:
                start, end = nums
                if end <= start:
                    result.append(f"{start}-{end}")
                    continue

                length = end - start + 1
                # Одиночная пара
                if length == 2:
                    result.append(f"{start}-{end}")
                    continue

                # Разбиваем на пары, если количество чётное
                if length % 2 == 0:
                    cur = start
                    while cur < end:
                        pair_end = cur + 1
                        result.append(f"{cur}-{pair_end}")
                        cur += 2
                    continue

                # Нечётная длина — оставляем как есть
                result.append(f"{start}-{end}")
                continue

            # Если ничего не распознали — оставляем исходное, пусть парсер решает
            result.append(s)

        return result

    def extract_discipline(lesson_match: Match2d) -> tuple[str, list[str]]:
        """Извлекает название дисциплины и группы из frame->discipline."""
        if 'frame' not in lesson_match:
            raise ValueError("Lesson frame not found")

        frame_match = lesson_match['frame']
        if 'discipline' not in frame_match:
            raise ValueError("Discipline not found in frame")

        discipline_match = frame_match['discipline']
        discipline_content = discipline_match.get_content()

        def _extract_discipline_parts(value) -> list[str]:
            parts: list[str] = []

            if isinstance(value, str):
                s = value.strip()
                if s:
                    parts.append(s)
                return parts

            if isinstance(value, list):
                for item in value:
                    parts.extend(_extract_discipline_parts(item))
                return parts

            if isinstance(value, dict):
                if "discipline" in value:
                    parts.extend(_extract_discipline_parts(value["discipline"]))
                elif "discipline_name" in value:
                    parts.extend(_extract_discipline_parts(value["discipline_name"]))
                else:
                    # fallback для структур вида {"m1": {...}, "m2": {...}}
                    m_keys = [k for k in value if re.fullmatch(r"m\d+", str(k))]
                    if m_keys:
                        m_keys_sorted = sorted(m_keys, key=lambda k: int(str(k)[1:]))
                        for k in m_keys_sorted:
                            # recurse into m*
                            parts.extend(_extract_discipline_parts(value[k]))
                return parts

            return parts

        # Извлекаем название дисциплины
        subject = ""
        if isinstance(discipline_content, dict):
            # Проверяем вложенную структуру discipline.discipline.*
            if 'discipline' in discipline_content:
                disc = discipline_content['discipline']
                # Случай: список вложенных структур с полем 'discipline'
                if isinstance(disc, list):
                    parts: list[str] = []
                    for item in disc:
                        if isinstance(item, dict):
                            if 'discipline' in item:
                                parts.append(plain(item['discipline']))
                            else:
                                # Структурированный объект, который мы не умеем разворачивать —
                                # лучше явно упасть, чем превратить его в строку.
                                raise ValueError(f"Unexpected discipline item structure: {item!r}")
                        elif isinstance(item, str):
                            parts.append(item)
                        else:
                            raise ValueError(f"Unexpected discipline item type: {type(item)!r} in {disc!r}")
                    subject = ' '.join(p.strip() for p in parts if p.strip())
                elif isinstance(disc, dict):
                    if 'discipline' in disc:
                        subject = plain(disc['discipline'])
                    else:
                        # Неизвестная структура словаря дисциплины
                        raise ValueError(f"Unexpected discipline dict structure: {disc!r}")
                elif isinstance(disc, str):
                    subject = disc
                else:
                    # Для прочих простых типов (числа и т.п.) допустимо привести к строке
                    subject = plain(disc)
            elif 'discipline_name' in discipline_content:
                subject = plain(discipline_content['discipline_name'])
            else:
                parts = _extract_discipline_parts(discipline_content)
                if parts:
                    subject = " ".join(p.strip() for p in parts if p.strip())
                else:
                    raise ValueError(f"Unknown discipline content structure: {discipline_content!r}")
        elif isinstance(discipline_content, list):
            parts = _extract_discipline_parts(discipline_content)
            subject = " ".join(p.strip() for p in parts if p.strip())
        elif isinstance(discipline_content, str):
            subject = discipline_content.strip()

        if not subject:
            raise ValueError(f"Cannot extract discipline subject from: {discipline_content!r}")

        # Извлекаем группы
        groups = resolve_groups(discipline_match)

        return subject, groups

    def extract_week_info(lesson_match: Match2d, grid_match: Match2d, datetime_match: Match2d) -> tuple[int, str]:
        """Извлекает информацию о неделе и дне недели.

        День недели извлекается из frame.hour_begin.week_day или frame.discipline.hour_begin.week_day.
        Неделя определяется по позиции урока в grid относительно структуры datetime.
        """
        week_day_index = 0
        week = "first_week"

        # Извлекаем день недели из frame.hour_begin.week_day или frame.discipline.hour_begin.week_day
        if 'frame' in lesson_match:
            frame_match = lesson_match['frame']
            frame_content = frame_match.get_content()

            if isinstance(frame_content, dict):
                # Проверяем frame.hour_begin.week_day
                if 'hour_begin' in frame_content:
                    hour_begin = frame_content['hour_begin']
                    if isinstance(hour_begin, dict) and 'week_day' in hour_begin:
                        week_day_str = plain(hour_begin['week_day'])
                        with contextlib.suppress(ValueError, AssertionError):
                            week_day_index = LOOKUP.index_of_weekday(week_day_str)

                # Также проверяем frame.discipline.hour_begin.week_day
                if week_day_index == 0 and 'discipline' in frame_content:
                    discipline_content = frame_content['discipline']
                    if isinstance(discipline_content, dict) and 'hour_begin' in discipline_content:
                        hour_begin = discipline_content['hour_begin']
                        if isinstance(hour_begin, dict) and 'week_day' in hour_begin:
                            week_day_str = plain(hour_begin['week_day'])
                            with contextlib.suppress(ValueError, AssertionError):
                                week_day_index = LOOKUP.index_of_weekday(week_day_str)

        # Определяем неделю по позиции урока относительно структуры datetime
        if datetime_match and lesson_match.box:
            # Получаем структуру weeks из datetime
            if 'weeks' in datetime_match:
                weeks_match = datetime_match['weeks']
                week_children = weeks_match.get_children()

                if len(week_children) >= 2:
                    # Сравниваем позицию урока с позициями недель
                    lesson_top = lesson_match.box.top
                    week1_match = week_children[0]
                    week2_match = week_children[1] if len(week_children) > 1 else None

                    if week1_match.box and week2_match and week2_match.box:
                        # Определяем, к какой неделе относится урок по вертикальной позиции
                        week1_bottom = week1_match.box.bottom
                        if lesson_top < week1_bottom:
                            # Урок в первой неделе
                            week_content = week1_match.get_content()
                            if isinstance(week_content, dict) and '@index_in_array' in week_content:
                                week_index = week_content['@index_in_array']
                                week = LOOKUP.name_of_week(week_index) or "first_week"
                        else:
                            # Урок во второй неделе
                            week_content = week2_match.get_content()
                            if isinstance(week_content, dict) and '@index_in_array' in week_content:
                                week_index = week_content['@index_in_array']
                                week = LOOKUP.name_of_week(week_index) or "second_week"
                    elif week1_match.box:
                        # Только одна неделя
                        week_content = week1_match.get_content()
                        if isinstance(week_content, dict) and '@index_in_array' in week_content:
                            week_index = week_content['@index_in_array']
                            week = LOOKUP.name_of_week(week_index) or "first_week"

        return week_day_index, week

    def extract_explicit_dates(lesson_match: Match2d) -> list[str]:
        """Извлекает переопределённые даты из explicit_dates (как есть в документе)."""
        dates = []
        if 'explicit_dates' in lesson_match:
            explicit_dates_match = lesson_match['explicit_dates']
            explicit_dates_content = explicit_dates_match.get_content()

            if isinstance(explicit_dates_content, list):
                for item in explicit_dates_content:
                    if isinstance(item, str):
                        # Может быть строка с датами, разделёнными запятыми или переносами строк
                        if item.strip():
                            # Разбиваем по переносам строк и запятым
                            for date_part in item.replace('\\n', '\n').split('\n'):
                                for date in date_part.split(','):
                                    date_clean = date.strip()
                                    if date_clean:
                                        dates.append(date_clean)
                    elif isinstance(item, dict) and 'date' in item:
                        dates.append(plain(item['date']))
            elif isinstance(explicit_dates_content, dict):
                if 'dates' in explicit_dates_content:
                    for d in explicit_dates_content['dates']:
                        dates.append(plain(d))
                elif 'date' in explicit_dates_content:
                    dates.append(plain(explicit_dates_content['date']))
            elif isinstance(explicit_dates_content, str):
                # Может быть строка с датами
                if explicit_dates_content.strip():
                    for date_part in explicit_dates_content.replace('\\n', '\n').split('\n'):
                        for date in date_part.split(','):
                            date_clean = date.strip()
                            if date_clean:
                                dates.append(date_clean)

        return dates

    def normalize_explicit_dates(dates: list[str], years_hint: str | None) -> list[str]:
        """Нормализует переопределённые даты в формат `%d.%m.%Y`.

        Ожидаемые входы: `18.09.`, `18.9`, `18.09.2025`, `18.09`.
        Если в записи нет года, он выводится из диапазона лет вида `2025-2026`:
        - месяцы > 6 (июль–декабрь) → левый год (2025)
        - месяцы <= 6 (январь–июнь) → правый год (2026)
        """
        if not dates:
            return []

        # Значения по умолчанию на случай, если ничего не получится определить из years_hint
        current_left, current_right = _parse_year_bounds(CURRENT_ACADEMIC_YEAR)
        DEFAULT_LEFT_YEAR = current_left
        DEFAULT_RIGHT_YEAR = current_right

        left_year = right_year = None
        if years_hint:
            # Пытаемся вытащить "2025-2026" или хотя бы два года из строки
            m = re.search(r"(\d{4})\s*-\s*(\d{4})", years_hint)
            if m:
                left_year = int(m.group(1))
                right_year = int(m.group(2))
            else:
                nums = re.findall(r"\d{4}", years_hint)
                if len(nums) >= 2:
                    left_year = int(nums[0])
                    right_year = int(nums[1])

        # Если так и не смогли определить годы — используем дефолтный диапазон
        if left_year is None or right_year is None:
            left_year = DEFAULT_LEFT_YEAR
            right_year = DEFAULT_RIGHT_YEAR

        def resolve_year(month: int) -> int | None:
            if left_year is None or right_year is None:
                return None
            # как в make_calendar: месяцы > 6 относятся к левому году
            return left_year if month > 6 else right_year

        # проверить ситуацию с форматом одной точки в качестве разделителя (16.04.17.05 -> 16.04, 17.05)
        re_four_parts = r'^(\d{1,2}.\d{2}).(\d{1,2}.\d{2})$'
        # цикл с разбиением отдельных элементов
        # (пронумеруем элементы и переберём их в обратном порядке; итерируемся по копии списка)
        for i, raw in reversed(list(enumerate(dates))):
            if m := re.match(re_four_parts, raw):
                date1, date2 = m[1], m[2]
                print(f"[normalize_explicit_dates] Split terse dates: {raw!r} -> {[date1, date2]!r} (years_hint={years_hint!r})")
                # вставляем пару вместо одного
                dates[i: i+1] = [date1, date2]


        normalized: list[str] = []
        for raw in dates:
            # В одной строке могут быть несколько дат, разделённых `,`, `;` или `..`
            # Примеры: "24.09;22.10;", "03.09..01.10"
            for token in re.split(r"[;,]|\.\.+", raw or ""):
                s = token.strip().rstrip(".")
                if not s:
                    continue

                # Уже полный формат?
                m_full = re.fullmatch(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", s)
                if m_full:
                    d, m_, y = m_full.groups()
                    normalized.append(f"{int(d):02d}.{int(m_):02d}.{int(y):04d}")
                    continue

                # Форматы без года: d.m , d.m. , dd.mm
                m_partial = re.fullmatch(r"(\d{1,2})\.(\d{1,2})", s)
                if m_partial:
                    d, m_ = m_partial.groups()
                    month = int(m_)
                    year = resolve_year(month)
                    if year is not None:
                        normalized.append(f"{int(d):02d}.{month:02d}.{year:04d}")
                    else:
                        # fallback: без информации о годе оставляем как есть
                        normalized.append(f"{int(d):02d}.{month:02d}.0000")
                    continue

                # Если не распознали — оставляем исходное значение и печатаем отладку
                print(f"[normalize_explicit_dates] Unrecognized date format: {raw!r} -> {s!r} (years_hint={years_hint!r})")
                normalized.append(s)

        return normalized

    out_lessons = []
    grid_match = matched_document['table']['grid']
    datetime_match = matched_document['table']['datetime']

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
            hours_raw = extract_hours(lesson_match)
            hours = normalize_hour_ranges(hours_raw)

            # Извлекаем информацию о неделе и дне недели
            week_day_index, week = extract_week_info(lesson_match, grid_match, datetime_match)

            # Извлекаем переопределённые даты
            explicit_dates_raw = extract_explicit_dates(lesson_match)
            explicit_dates = normalize_explicit_dates(explicit_dates_raw, years_hint=years)

            out_lessons.append({
                "subject": subject,
                "kind": extract_kind(lesson_match, hours),
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
