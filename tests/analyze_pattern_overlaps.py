# analyze_pattern_overlaps.py

"""
Скрипт для анализа пересечений между паттернами различных типов ячеек.
Находит случаи, где один текст совпадает с несколькими типами с высоким confidence.
"""

from collections import defaultdict
from dataclasses import dataclass
from typing import List, Tuple, Dict

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
    
    # Сохраняем вывод в файл для избежания проблем с кодировкой консоли
    output_file = 'analyze_pattern_overlaps_output.txt'
    
    # Перенаправляем stdout в файл
    with open(output_file, 'w', encoding='utf-8') as f:
        original_stdout = sys.stdout
        sys.stdout = f
        
        try:
            analyze_all_data(
                min_confidence=0.75,  # Минимальный confidence для учёта
                min_precision=0.50,   # Минимальный precision для учёта
                show_top_n=30         # Сколько конфликтов показать детально
            )
        finally:
            sys.stdout = original_stdout
    
    print(f"Анализ завершён! Результаты сохранены в файл: {output_file}")
    print(f"Откройте файл для просмотра результатов.")

