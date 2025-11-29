# test_improved_patterns.py

"""
Скрипт для тестирования улучшенных паттернов групп и дисциплин на реальных данных.
Находит конфликты и несовпадающие строки.
"""

from collections import defaultdict
from dataclasses import dataclass
from typing import List, Tuple, Dict, Set

from tests_bootstrapper import init_testing_environment
init_testing_environment()

from string_matching import read_cell_types
from string_matching.CellClassifier import CellClassifier
from string_matching.StringMatch import StringMatch


@dataclass
class TestResult:
    """Результат тестирования одной строки"""
    text: str
    matched_types: List[Tuple[str, float]]  # (type_name, precision)
    file_source: str = ""
    is_conflict: bool = False
    is_unmatched: bool = False


def load_test_data():
    """Загружает тестовые данные из файлов materials"""
    filepaths = [
        ('../materials/ОН_ФАТ_1_курс - unique-values.txt', 'ОН_ФАТ_1'),
        ('../materials/ОН_ФЭВТ_1 курс - unique-values.txt', 'ОН_ФЭВТ_1'),
        ('../materials/ОН_ФЭВТ_3 курс - unique-values.txt', 'ОН_ФЭВТ_3'),
        ('../materials/ОН_Магистратура_2 курс ХТФ - unique-values.txt', 'Магистратура_ХТФ'),
        ('../materials/ОН_Магистратура_ 1 курс ФТКМ - unique-values.txt', 'Магистратура_ФТКМ'),
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


def load_reference_groups() -> Set[str]:
    """Загружает белый список групп из справочника"""
    try:
        with open('../materials/groupnames.txt', encoding='utf8') as f:
            groups = set(line.strip() for line in f if line.strip())
        return groups
    except FileNotFoundError:
        return set()


def analyze_real_data(
    min_precision: float = 0.50,
    focus_types: Tuple[str, ...] = ('group', 'discipline', 'room')
):
    """Анализирует реальные данные с улучшенными паттернами"""
    import os
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    config_path = os.path.join(project_root, 'cnf', 'cell_types.yml')
    
    cell_types = read_cell_types(config_file=config_path)
    classifier = CellClassifier(cell_types.values())
    values_by_file = load_test_data()
    reference_groups = load_reference_groups()
    
    print("=" * 80)
    print("ТЕСТИРОВАНИЕ УЛУЧШЕННЫХ ПАТТЕРНОВ")
    print("=" * 80)
    print()
    print(f"Загружено типов ячеек: {len(cell_types)}")
    print(f"Загружено файлов с данными: {len(values_by_file)}")
    print(f"Загружено групп из справочника: {len(reference_groups)}")
    print()
    
    all_results = []
    conflicts = []
    unmatched = []
    type_stats = defaultdict(int)
    
    for file_name, values in values_by_file.items():
        print(f"Анализ файла: {file_name} ({len(values)} значений)...")
        
        for text in values:
            text = text.strip().strip('"\'')
            if not text or len(text) < 2:
                continue
            
            # Классифицируем
            matches = classifier.match(text, limit=5)
            matched_types = [(m.pattern.content_class.name, m.precision) 
                           for m in matches if m.precision >= min_precision]
            
            is_conflict = len(matched_types) >= 2
            is_unmatched = len(matched_types) == 0
            
            result = TestResult(
                text=text,
                matched_types=matched_types,
                file_source=file_name,
                is_conflict=is_conflict,
                is_unmatched=is_unmatched
            )
            all_results.append(result)
            
            if is_conflict:
                conflicts.append(result)
            
            if is_unmatched:
                unmatched.append(result)
            
            if matched_types:
                top_type = matched_types[0][0]
                type_stats[top_type] += 1
    
    print()
    print("=" * 80)
    print("СТАТИСТИКА")
    print("=" * 80)
    print()
    print(f"Всего проанализировано: {len(all_results)}")
    print(f"Успешно распознано: {len(all_results) - len(unmatched)} ({100*(len(all_results)-len(unmatched))/len(all_results):.1f}%)")
    print(f"Конфликтов (2+ типа): {len(conflicts)} ({100*len(conflicts)/len(all_results):.1f}%)")
    print(f"Не распознано: {len(unmatched)} ({100*len(unmatched)/len(all_results):.1f}%)")
    print()
    print("Распределение по типам:")
    for type_name, count in sorted(type_stats.items(), key=lambda x: x[1], reverse=True):
        print(f"  {type_name:20s}: {count:4d} ({100*count/len(all_results):.1f}%)")
    print()
    
    # Анализ конфликтов
    if conflicts:
        print("=" * 80)
        print(f"КОНФЛИКТЫ ({len(conflicts)} случаев)")
        print("=" * 80)
        print()
        
        # Группируем по парам типов
        conflict_pairs = defaultdict(list)
        for conflict in conflicts:
            if len(conflict.matched_types) >= 2:
                types = tuple(sorted([t[0] for t in conflict.matched_types[:2]]))
                conflict_pairs[types].append(conflict)
        
        print("Конфликты по парам типов:")
        for (type1, type2), confs in sorted(conflict_pairs.items(), key=lambda x: len(x[1]), reverse=True):
            if type1 in focus_types or type2 in focus_types:
                print(f"  {type1} vs {type2}: {len(confs)} конфликтов")
                # Показываем первые 5 примеров
                for conf in confs[:5]:
                    precisions = ', '.join(f"{t[0]}({t[1]*100:.1f}%)" for t in conf.matched_types[:3])
                    print(f"    `{conf.text}` -> {precisions}")
                print()
        
        # Детальный анализ конфликтов с группами/дисциплинами
        print()
        print("Детальные конфликты (group/discipline/room):")
        focus_conflicts = [c for c in conflicts 
                          if any(t[0] in focus_types for t in c.matched_types)]
        focus_conflicts.sort(key=lambda c: max(t[1] for t in c.matched_types), reverse=True)
        
        for conf in focus_conflicts[:30]:
            precisions = ', '.join(f"{t[0]}({t[1]*100:.1f}%)" for t in conf.matched_types[:3])
            is_in_reference = conf.text in reference_groups
            ref_mark = " [В СПРАВОЧНИКЕ ГРУПП!]" if is_in_reference else ""
            print(f"  `{conf.text}` -> {precisions}{ref_mark}")
        print()
    
    # Анализ нераспознанных
    if unmatched:
        print("=" * 80)
        print(f"НЕРАСПОЗНАННЫЕ СТРОКИ ({len(unmatched)} случаев)")
        print("=" * 80)
        print()
        
        # Показываем примеры нераспознанных
        print("Примеры нераспознанных строк:")
        for un in unmatched[:50]:
            print(f"  `{un.text}`")
        
        if len(unmatched) > 50:
            print(f"  ... и ещё {len(unmatched) - 50} строк")
        print()
        
        # Анализ нераспознанных - возможно, это группы?
        unmatched_in_reference = [un for un in unmatched if un.text in reference_groups]
        if unmatched_in_reference:
            print(f"ВАЖНО: {len(unmatched_in_reference)} нераспознанных строк есть в справочнике групп!")
            print("Примеры:")
            for un in unmatched_in_reference[:20]:
                print(f"  `{un.text}`")
            print()
    
    # Анализ групп из справочника
    if reference_groups:
        print("=" * 80)
        print("АНАЛИЗ ГРУПП ИЗ СПРАВОЧНИКА")
        print("=" * 80)
        print()
        
        recognized_groups = []
        unrecognized_groups = []
        
        for group in sorted(reference_groups):
            matches = classifier.match(group, limit=3)
            if matches and matches[0].pattern.content_class.name == 'group':
                recognized_groups.append((group, matches[0].precision))
            else:
                unmatched_types = [(m.pattern.content_class.name, m.precision) 
                                 for m in matches[:2] if m.precision >= 0.5] if matches else []
                unrecognized_groups.append((group, unmatched_types))
        
        print(f"Распознано как группы: {len(recognized_groups)}/{len(reference_groups)} ({100*len(recognized_groups)/len(reference_groups):.1f}%)")
        print(f"НЕ распознано как группы: {len(unrecognized_groups)}/{len(reference_groups)} ({100*len(unrecognized_groups)/len(reference_groups):.1f}%)")
        print()
        
        if unrecognized_groups:
            print("Группы, которые НЕ распознаны как group:")
            for group, other_types in unrecognized_groups[:30]:
                types_str = ', '.join(f"{t[0]}({t[1]*100:.1f}%)" for t in other_types) if other_types else "не распознано"
                print(f"  `{group}` -> {types_str}")
            print()
    
    return all_results, conflicts, unmatched


if __name__ == '__main__':
    import sys
    
    output_file = 'test_improved_patterns_output.txt'
    
    with open(output_file, 'w', encoding='utf-8') as f:
        original_stdout = sys.stdout
        sys.stdout = f
        
        try:
            analyze_real_data(
                min_precision=0.50,
                focus_types=('group', 'discipline', 'room')
            )
        finally:
            sys.stdout = original_stdout
    
    print(f"Анализ завершён! Результаты сохранены в файл: {output_file}")

