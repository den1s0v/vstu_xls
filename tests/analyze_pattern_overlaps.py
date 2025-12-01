# analyze_pattern_overlaps.py

"""
Скрипт для анализа пересечений между паттернами различных типов ячеек.
Находит случаи, где один текст совпадает с несколькими типами с высоким confidence.
"""

from collections import defaultdict, Counter
from dataclasses import dataclass
import re
from pprint import pprint
from typing import List, Tuple, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from string_matching.CellType import CellType

from tests_bootstrapper import init_testing_environment
init_testing_environment()

from string_matching import read_cell_types
from string_matching.StringMatch import StringMatch


@dataclass
class ConflictInfo:
    """Информация о конфликте паттернов для одной строки"""
    text: str
    matches: List[Tuple[str, float, float, str]]  # (type_name, confidence, precision, matched_part)
    file_source: str = ""


def load_test_data():
    """Загружает тестовые данные из файлов materials"""
    filepaths = [
        ('../materials/ОН_ФАТ_1_курс - unique-values.txt', 'ОН_ФАТ_1'),
        ('../materials/ОН_ФЭВТ_1 курс - unique-values.txt', 'ОН_ФЭВТ_1'),
        ('../materials/ОН_ФЭВТ_3 курс - unique-values.txt', 'ОН_ФЭВТ_3'),
        ('../materials/ОН_Магистратура_2 курс ХТФ - unique-values.txt', 'Магистратура_ХТФ'),
        ('../materials/ОН_Магистратура_ 1 курс ФТКМ - unique-values.txt', 'Магистратура_ФТКМ'),
        ('../materials/groupnames.txt', 'groupnames'),
        ('../materials/vstu-discipline-shortnames.txt', 'discipline_shortnames'),
        ('../materials/Сборник_1 - unique-values.txt', 'Сборник_1'),
    ]
    
    values_by_file = {}
    for filepath, short_name in filepaths:
        try:
            with open(filepath, encoding='utf8') as f:
                text = f.read()
            values = set(filter(None, text.strip().split('\n')))
            values_by_file[short_name] = values
        except FileNotFoundError:
            print(f"Warning: file not found: {filepath}")
            continue
    
    return values_by_file

def maskify_string(s: str) -> str:
    """
    Преобразует строку в шаблон, заменяя:
    - Цифры на '#'
    - Русские заглавные буквы на 'Я' (А-Я, Ё)
    - Русские строчные буквы на 'я' (а-я, ё)
    - Английские заглавные буквы на 'W' (A-Z)
    - Английские строчные буквы на 'w' (a-z)
    - Все остальные символы остаются без изменений
    """
    result = []
    for char in s:
        if char.isdigit():
            result.append('#')
        elif 'А' <= char <= 'Я' or char == 'Ё':
            result.append('Я')  # Русская заглавная
        elif 'а' <= char <= 'я' or char == 'ё':
            result.append('я')  # Русская строчная
        elif 'A' <= char <= 'Z':
            result.append('W')  # Английская заглавная
        elif 'a' <= char <= 'z':
            result.append('w')  # Английская строчная
        else:
            result.append(char)  # Остальные символы как есть
    return ''.join(result)

def infer_patterns_from_real_data():
    """Анализирует шаблоны имён групп и дисциплин"""
    values_by_file = load_test_data()
    
    # Очищаем кавычки из имён дисциплин (как указал пользователь)
    discipline_names = {name.strip('"\'') for name in values_by_file.get('discipline_shortnames', set())}
    group_names = values_by_file.get('groupnames', set())
    
    print("=" * 80)
    print("АНАЛИЗ ШАБЛОНОВ ИМЁН")
    print("=" * 80)
    print()
    
    # Анализ групп
    if group_names:
        print(f"ИМЕНА ГРУПП: {len(group_names)} уникальных значений")
        print("-" * 80)
        group_patterns = Counter(map(maskify_string, group_names))
        
        print("\nТОП-30 шаблонов имён групп:")
        for pattern, count in group_patterns.most_common(30):
            # Найдём несколько примеров для каждого шаблона
            examples = [name for name in group_names if maskify_string(name) == pattern][:3]
            examples_str = ', '.join(f'`{ex}`' for ex in examples)
            print(f"  {pattern:30s} : {count:4d} раз  [примеры: {examples_str}]")
        print()
    
    # Анализ дисциплин
    if discipline_names:
        print(f"КОРОТКИЕ ИМЕНА ДИСЦИПЛИН: {len(discipline_names)} уникальных значений")
        print("-" * 80)
        discipline_patterns = Counter(map(maskify_string, discipline_names))
        
        print("\nТОП-30 шаблонов имён дисциплин:")
        for pattern, count in discipline_patterns.most_common(30):
            # Найдём несколько примеров для каждого шаблона
            examples = [name for name in discipline_names if maskify_string(name) == pattern][:3]
            examples_str = ', '.join(f'`{ex}`' for ex in examples)
            print(f"  {pattern:30s} : {count:4d} раз  [примеры: {examples_str}]")
        print()
    
    # Сравнение групп и дисциплин
    if group_names and discipline_names:
        print("=" * 80)
        print("СРАВНЕНИЕ ШАБЛОНОВ ГРУПП И ДИСЦИПЛИН")
        print("=" * 80)
        print()
        
        group_pattern_set = set(group_patterns.keys())
        discipline_pattern_set = set(discipline_patterns.keys())
        
        common_patterns = group_pattern_set & discipline_pattern_set
        only_group_patterns = group_pattern_set - discipline_pattern_set
        only_discipline_patterns = discipline_pattern_set - group_pattern_set
        
        print(f"Общих шаблонов: {len(common_patterns)}")
        print(f"Только для групп: {len(only_group_patterns)}")
        print(f"Только для дисциплин: {len(only_discipline_patterns)}")
        print()
        
        if common_patterns:
            print("ОБЩИЕ ШАБЛОНЫ (могут быть проблемными):")
            common_sorted = sorted(common_patterns, 
                                 key=lambda p: group_patterns[p] + discipline_patterns[p], 
                                 reverse=True)
            for pattern in common_sorted[:20]:
                g_count = group_patterns[pattern]
                d_count = discipline_patterns[pattern]
                print(f"  {pattern:30s} : группы={g_count:4d}, дисциплины={d_count:4d}")
            print()
        
        if only_group_patterns:
            print("ТОП-10 шаблонов ТОЛЬКО для групп (возможно, уникальные признаки групп):")
            group_only_sorted = sorted(only_group_patterns,
                                     key=lambda p: group_patterns[p],
                                     reverse=True)
            for pattern in group_only_sorted[:10]:
                count = group_patterns[pattern]
                examples = [name for name in group_names if maskify_string(name) == pattern][:2]
                examples_str = ', '.join(f'`{ex}`' for ex in examples)
                print(f"  {pattern:30s} : {count:4d} раз  [примеры: {examples_str}]")
            print()
        
        if only_discipline_patterns:
            print("ТОП-10 шаблонов ТОЛЬКО для дисциплин (возможно, уникальные признаки дисциплин):")
            disc_only_sorted = sorted(only_discipline_patterns,
                                    key=lambda p: discipline_patterns[p],
                                    reverse=True)
            for pattern in disc_only_sorted[:10]:
                count = discipline_patterns[pattern]
                examples = [name for name in discipline_names if maskify_string(name) == pattern][:2]
                examples_str = ', '.join(f'`{ex}`' for ex in examples)
                print(f"  {pattern:30s} : {count:4d} раз  [примеры: {examples_str}]")
            print()
    
    return {
        'group_patterns': group_patterns if group_names else Counter(),
        'discipline_patterns': discipline_patterns if discipline_names else Counter(),
        'group_names': group_names,
        'discipline_names': discipline_names
    }



def analyze_conflicts(
    text: str,
    cell_types: Dict[str, 'CellType'],
    min_confidence: float = 0.75,
    min_precision: float = 0.50
) -> ConflictInfo | None:
    """
    Анализирует конфликты для одной строки.
    Возвращает ConflictInfo, если найдено >= 2 совпадения с high confidence/precision.
    """
    matches = []
    
    for type_name, ct in cell_types.items():
        match = ct.match(text)
        if match:
            confidence = match.pattern.confidence
            precision = match.precision
            matched_part = match.re_match.group(0) if hasattr(match.re_match, 'group') else str(match.re_match[0])
            
            # Фильтруем только высокие confidence/precision
            if confidence >= min_confidence and precision >= min_precision:
                matches.append((type_name, confidence, precision, matched_part))
    
    # Если найдено 2+ совпадения с высоким confidence - это конфликт
    if len(matches) >= 2:
        # Сортируем по precision (descending)
        matches.sort(key=lambda x: x[2], reverse=True)
        return ConflictInfo(text=text, matches=matches)
    
    return None


def analyze_all_data(
    min_confidence: float = 0.75,
    min_precision: float = 0.50,
    show_top_n: int = 20
):
    """Основная функция анализа"""
    print("=" * 80)
    print("АНАЛИЗ ПЕРЕСЕЧЕНИЙ ПАТТЕРНОВ")
    print("=" * 80)
    print()
    
    # Загружаем типы и данные
    # Указываем явный путь к конфигу относительно корня проекта
    import os
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    config_path = os.path.join(project_root, 'cnf', 'cell_types.yml')
    cell_types = read_cell_types(config_file=config_path)
    values_by_file = load_test_data()
    
    print(f"Загружено типов ячеек: {len(cell_types)}")
    print(f"Загружено файлов с данными: {len(values_by_file)}")
    total_values = sum(len(v) for v in values_by_file.values())
    print(f"Всего уникальных значений: {total_values}")
    print()
    
    # Анализируем конфликты
    all_conflicts = []
    conflicts_by_type_pair = defaultdict(list)
    
    for file_name, values in values_by_file.items():
        print(f"Анализ файла: {file_name} ({len(values)} значений)...")
        
        for text in values:
            text = text.strip().strip('"\'')
            if not text or len(text) < 2:
                continue
            
            conflict = analyze_conflicts(text, cell_types, min_confidence, min_precision)
            if conflict:
                conflict.file_source = file_name
                all_conflicts.append(conflict)
                
                # Группируем по парам типов
                for i, (type1, _, _, _) in enumerate(conflict.matches):
                    for j, (type2, _, _, _) in enumerate(conflict.matches):
                        if i < j:  # избегаем дублей
                            pair = tuple(sorted([type1, type2]))
                            conflicts_by_type_pair[pair].append(conflict)
    
    print()
    print("=" * 80)
    print(f"НАЙДЕНО КОНФЛИКТОВ: {len(all_conflicts)}")
    print("=" * 80)
    print()
    
    # Статистика по парам типов
    print("СТАТИСТИКА КОНФЛИКТОВ ПО ПАРАМ ТИПОВ:")
    print("-" * 80)
    sorted_pairs = sorted(conflicts_by_type_pair.items(), key=lambda x: len(x[1]), reverse=True)
    
    for (type1, type2), conflicts in sorted_pairs[:10]:
        print(f"  {type1} vs {type2}: {len(conflicts)} конфликтов")
    print()
    
    # Детальный вывод топ-N конфликтов
    print("=" * 80)
    print(f"ТОП-{show_top_n} КОНФЛИКТОВ (по максимальной precision):")
    print("=" * 80)
    print()
    
    # Сортируем по максимальной precision среди конфликтов
    all_conflicts_sorted = sorted(
        all_conflicts,
        key=lambda c: max(m[2] for m in c.matches),
        reverse=True
    )
    
    for idx, conflict in enumerate(all_conflicts_sorted[:show_top_n], 1):
        print(f"#{idx}. Источник: {conflict.file_source}")
        print(f"   Текст: `{conflict.text}`")
        print(f"   Совпадения:")
        
        for type_name, confidence, precision, matched_part in conflict.matches:
            confidence_pct = confidence * 100
            precision_pct = precision * 100
            matched_display = matched_part if matched_part != conflict.text else "(весь текст)"
            
            print(f"     • {type_name:15s} | confidence: {confidence_pct:5.1f}% | precision: {precision_pct:5.1f}% | захвачено: `{matched_display}`")
        
        print()
    
    # Анализ проблемных пар
    print("=" * 80)
    print("ДЕТАЛЬНЫЙ АНАЛИЗ ПРОБЛЕМНЫХ ПАР:")
    print("=" * 80)
    print()
    
    # Фокус на room, group, discipline
    target_types = {'room', 'group', 'discipline'}
    
    for (type1, type2), conflicts in sorted_pairs:
        if type1 not in target_types and type2 not in target_types:
            continue
        
        print(f"\n{type1.upper()} vs {type2.upper()}: {len(conflicts)} конфликтов")
        print("-" * 80)
        
        # Показываем первые 5 примеров
        for conflict in conflicts[:5]:
            print(f"  `{conflict.text}`")
            for type_name, confidence, precision, matched_part in conflict.matches:
                if type_name in (type1, type2):
                    precision_pct = precision * 100
                    matched_display = matched_part if matched_part != conflict.text else "(весь)"
                    print(f"    -> {type_name}: precision={precision_pct:.1f}%, часть=`{matched_display}`")
        print()
    
    # Анализ близких precision (где выбор неочевиден)
    print("=" * 80)
    print("КОНФЛИКТЫ С БЛИЗКИМИ PRECISION (проблема выбора):")
    print("=" * 80)
    print()
    
    close_conflicts = []
    for conflict in all_conflicts:
        if len(conflict.matches) >= 2:
            precisions = [m[2] for m in conflict.matches]
            max_prec = max(precisions)
            second_prec = sorted(precisions, reverse=True)[1]
            
            # Если разница меньше 10% - это проблемный случай
            if max_prec - second_prec < 0.10:
                close_conflicts.append((conflict, max_prec - second_prec))
    
    close_conflicts.sort(key=lambda x: x[1])  # по разнице (от меньшей к большей)
    
    for conflict, diff in close_conflicts[:15]:
        print(f"  `{conflict.text}` (разница precision: {diff*100:.1f}%)")
        for type_name, confidence, precision, matched_part in conflict.matches:
            precision_pct = precision * 100
            print(f"    • {type_name}: precision={precision_pct:.1f}%")
        print()
    
    return all_conflicts, conflicts_by_type_pair


if __name__ == '__main__':
    import sys
    import os
    
    # Анализ шаблонов имён
    print("Анализ шаблонов имён групп и дисциплин...")
    print()
    
    # Сохраняем вывод анализа шаблонов в файл
    patterns_output_file = 'analyze_name_patterns_output.txt'
    
    with open(patterns_output_file, 'w', encoding='utf-8') as f:
        original_stdout = sys.stdout
        sys.stdout = f
        
        try:
            patterns_data = infer_patterns_from_real_data()
        finally:
            sys.stdout = original_stdout
    
    print(f"Анализ шаблонов завершён! Результаты сохранены в файл: {patterns_output_file}")
    
    # Читаем и показываем краткую сводку в консоль
    with open(patterns_output_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        # Показываем первые 50 строк
        print("\n" + "=" * 80)
        print("КРАТКАЯ СВОДКА (первые строки):")
        print("=" * 80)
        for line in lines[:50]:
            print(line.rstrip())
        if len(lines) > 50:
            print(f"\n... (остальные {len(lines) - 50} строк см. в файле {patterns_output_file})")
    
    print("\n" + "=" * 80)
    print("Для полного анализа конфликтов паттернов раскомментируйте код ниже.")
    print("=" * 80)
    
    # Раскомментировать для анализа конфликтов:
    # 
    # # Сохраняем вывод в файл для избежания проблем с кодировкой консоли
    # output_file = 'analyze_pattern_overlaps_output.txt'
    # 
    # # Перенаправляем stdout в файл
    # with open(output_file, 'w', encoding='utf-8') as f:
    #     original_stdout = sys.stdout
    #     sys.stdout = f
    #     
    #     try:
    #         analyze_all_data(
    #             min_confidence=0.75,  # Минимальный confidence для учёта
    #             min_precision=0.50,   # Минимальный precision для учёта
    #             show_top_n=30         # Сколько конфликтов показать детально
    #         )
    #     finally:
    #         sys.stdout = original_stdout
    # 
    # print(f"Анализ конфликтов завершён! Результаты сохранены в файл: {output_file}")
    # print(f"Откройте файл для просмотра результатов.")

