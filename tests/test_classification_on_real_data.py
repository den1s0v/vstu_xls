# test_classification_on_real_data.py

"""
Скрипт для тестирования классификации типов ячеек на реальных данных.
Находит конфликты, несовпадающие строки и статистику по типам.
"""

from collections import defaultdict, Counter
from dataclasses import dataclass
from typing import List, Tuple, Dict, Set
import os

from tests_bootstrapper import init_testing_environment
init_testing_environment()

from string_matching import read_cell_types
from string_matching.CellClassifier import CellClassifier


@dataclass
class ClassificationResult:
    """Результат классификации одной строки"""
    text: str
    matched_types: List[Tuple[str, float]]  # (type_name, precision)
    file_source: str = ""
    is_conflict: bool = False
    is_unmatched: bool = False


def load_test_data():
    """Загружает тестовые данные из файлов materials"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    materials_dir = os.path.join(project_root, 'materials')
    
    filepaths = [
        (os.path.join(materials_dir, 'ОН_ФАТ_1_курс - unique-values.txt'), 'ОН_ФАТ_1'),
        (os.path.join(materials_dir, 'ОН_ФЭВТ_1 курс - unique-values.txt'), 'ОН_ФЭВТ_1'),
        (os.path.join(materials_dir, 'ОН_ФЭВТ_3 курс - unique-values.txt'), 'ОН_ФЭВТ_3'),
        (os.path.join(materials_dir, 'ОН_Магистратура_2 курс ХТФ - unique-values.txt'), 'Магистратура_ХТФ'),
        (os.path.join(materials_dir, 'ОН_Магистратура_ 1 курс ФТКМ - unique-values.txt'), 'Магистратура_ФТКМ'),
        (os.path.join(materials_dir, 'groupnames.txt'), 'groupnames'),
        (os.path.join(materials_dir, 'vstu-discipline-shortnames.txt'), 'discipline_shortnames'),
        (os.path.join(materials_dir, 'Сборник_1 - unique-values.txt'), 'Сборник_1'),
    ]
    
    values_by_file = {}
    for filepath, short_name in filepaths:
        try:
            with open(filepath, encoding='utf8') as f:
                text = f.read()
            values = set(filter(None, text.strip().split('\n')))
            # Очищаем кавычки и пробелы
            values = {v.strip().strip('"\'') for v in values if v.strip()}
            values_by_file[short_name] = values
        except FileNotFoundError:
            print(f"Warning: file not found: {filepath}")
            continue
    
    return values_by_file


def classify_text(text: str, classifier: CellClassifier, min_precision: float = 0.50) -> ClassificationResult:
    """Классифицирует одну строку"""
    matches = classifier.match(text, limit=10)
    
    # Фильтруем только значимые совпадения
    significant_matches = [
        (m.pattern.content_class.name, m.precision)
        for m in matches
        if m.precision >= min_precision
    ]
    
    is_conflict = len(significant_matches) >= 2
    is_unmatched = len(significant_matches) == 0
    
    return ClassificationResult(
        text=text,
        matched_types=significant_matches,
        is_conflict=is_conflict,
        is_unmatched=is_unmatched
    )


def analyze_classification_results(
    results: List[ClassificationResult],
    target_types: Set[str] = None
) -> Dict:
    """Анализирует результаты классификации"""
    if target_types is None:
        target_types = {'room', 'group', 'discipline'}
    
    stats = {
        'total': len(results),
        'conflicts': [],
        'unmatched': [],
        'type_counts': defaultdict(int),
        'precision_stats': defaultdict(list),
        'conflicts_by_pair': defaultdict(list),
    }
    
    for result in results:
        if result.is_unmatched:
            stats['unmatched'].append(result)
        
        if result.is_conflict:
            stats['conflicts'].append(result)
            # Группируем конфликты по парам типов
            for i, (type1, _) in enumerate(result.matched_types):
                if type1 in target_types:
                    for j, (type2, _) in enumerate(result.matched_types):
                        if i < j and type2 in target_types:
                            pair = tuple(sorted([type1, type2]))
                            stats['conflicts_by_pair'][pair].append(result)
        
        # Статистика по типам
        for type_name, precision in result.matched_types:
            stats['type_counts'][type_name] += 1
            stats['precision_stats'][type_name].append(precision)
    
    return stats


def generate_report(
    results_by_file: Dict[str, List[ClassificationResult]],
    output_file: str = 'classification_report.txt'
):
    """Генерирует подробный отчёт о классификации"""
    
    # Загружаем белый список групп для проверки
    known_groups = set()
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    groupnames_path = os.path.join(project_root, 'materials', 'groupnames.txt')
    try:
        with open(groupnames_path, encoding='utf8') as f:
            known_groups = {line.strip() for line in f if line.strip()}
    except:
        pass
    
    target_types = {'room', 'group', 'discipline'}
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("ОТЧЁТ О КЛАССИФИКАЦИИ НА РЕАЛЬНЫХ ДАННЫХ\n")
        f.write("=" * 80 + "\n\n")
        
        all_results = []
        all_conflicts = []
        all_unmatched = []
        
        # Собираем все результаты
        for file_name, results in results_by_file.items():
            all_results.extend(results)
            all_conflicts.extend([r for r in results if r.is_conflict])
            all_unmatched.extend([r for r in results if r.is_unmatched])
        
        # Общая статистика
        f.write("ОБЩАЯ СТАТИСТИКА:\n")
        f.write("-" * 80 + "\n")
        f.write(f"Всего проанализировано строк: {len(all_results)}\n")
        f.write(f"Найдено конфликтов: {len(all_conflicts)}\n")
        f.write(f"Не совпало строк: {len(all_unmatched)}\n")
        f.write(f"Процент конфликтов: {len(all_conflicts)/len(all_results)*100:.1f}%\n")
        f.write(f"Процент несовпадений: {len(all_unmatched)/len(all_results)*100:.1f}%\n\n")
        
        # Статистика по файлам
        f.write("СТАТИСТИКА ПО ФАЙЛАМ:\n")
        f.write("-" * 80 + "\n")
        for file_name, results in results_by_file.items():
            conflicts = [r for r in results if r.is_conflict]
            unmatched = [r for r in results if r.is_unmatched]
            f.write(f"{file_name:30s}: всего={len(results):4d}, конфликты={len(conflicts):4d}, несовпадения={len(unmatched):4d}\n")
        f.write("\n")
        
        # Анализ конфликтов
        stats = analyze_classification_results(all_results, target_types)
        
        f.write("КОНФЛИКТЫ ПО ПАРАМ ТИПОВ (room, group, discipline):\n")
        f.write("-" * 80 + "\n")
        sorted_pairs = sorted(stats['conflicts_by_pair'].items(), key=lambda x: len(x[1]), reverse=True)
        for (type1, type2), conflicts in sorted_pairs:
            f.write(f"{type1:15s} vs {type2:15s}: {len(conflicts):4d} конфликтов\n")
        f.write("\n")
        
        # Топ конфликтов
        f.write("ТОП-30 КОНФЛИКТОВ (по максимальной precision):\n")
        f.write("-" * 80 + "\n")
        conflicts_sorted = sorted(
            all_conflicts,
            key=lambda r: max(p for _, p in r.matched_types),
            reverse=True
        )
        for idx, result in enumerate(conflicts_sorted[:30], 1):
            f.write(f"#{idx:2d}. `{result.text}` (источник: {result.file_source})\n")
            for type_name, precision in sorted(result.matched_types, key=lambda x: x[1], reverse=True):
                f.write(f"      -> {type_name:15s}: precision={precision*100:5.1f}%\n")
            
            # Проверяем, есть ли в белом списке групп
            if result.text in known_groups:
                f.write(f"      [В БЕЛОМ СПИСКЕ ГРУПП]\n")
            f.write("\n")
        
        # Несовпадающие строки
        f.write("=" * 80 + "\n")
        f.write(f"НЕСОВПАВШИЕ СТРОКИ ({len(all_unmatched)}):\n")
        f.write("=" * 80 + "\n\n")
        
        # Группируем по файлам
        unmatched_by_file = defaultdict(list)
        for result in all_unmatched:
            unmatched_by_file[result.file_source].append(result)
        
        for file_name in sorted(unmatched_by_file.keys()):
            unmatched = unmatched_by_file[file_name]
            f.write(f"{file_name} ({len(unmatched)} строк):\n")
            f.write("-" * 80 + "\n")
            # Показываем первые 50 из каждого файла
            for result in unmatched[:50]:
                f.write(f"  `{result.text}`\n")
            if len(unmatched) > 50:
                f.write(f"  ... и ещё {len(unmatched) - 50} строк\n")
            f.write("\n")
        
        # Анализ проблемных случаев групп и дисциплин
        f.write("=" * 80 + "\n")
        f.write("АНАЛИЗ ПРОБЛЕМНЫХ СЛУЧАЕВ (группы и дисциплины):\n")
        f.write("=" * 80 + "\n\n")
        
        # Строки, которые должны быть группами, но не распознаны
        potential_groups = []
        for result in all_results:
            if result.text in known_groups:
                matched_group = any(name == 'group' for name, _ in result.matched_types)
                if not matched_group:
                    potential_groups.append(result)
        
        if potential_groups:
            f.write(f"СТРОКИ ИЗ БЕЛОГО СПИСКА ГРУПП, НЕ РАСПОЗНАННЫЕ КАК ГРУППЫ ({len(potential_groups)}):\n")
            f.write("-" * 80 + "\n")
            for result in potential_groups[:30]:
                f.write(f"  `{result.text}`")
                if result.matched_types:
                    types_str = ', '.join(f"{name}({p*100:.0f}%)" for name, p in result.matched_types)
                    f.write(f" -> {types_str}")
                else:
                    f.write(" -> НЕ РАСПОЗНАНА")
                f.write("\n")
            f.write("\n")
        
        # Строки, которые выглядят как группы, но распознаны как дисциплины
        groups_as_disciplines = []
        for result in all_conflicts:
            has_group = any(name == 'group' for name, _ in result.matched_types)
            has_discipline = any(name == 'discipline' for name, _ in result.matched_types)
            # Проверяем формат группы (буквы + дефис/пробел + цифры)
            import re
            looks_like_group = bool(re.search(r'[А-ЯЁA-Zа-яё]{1,}[-\s]+\d', result.text))
            
            if has_discipline and looks_like_group and not has_group:
                groups_as_disciplines.append(result)
        
        if groups_as_disciplines:
            f.write(f"СТРОКИ, ВЫГЛЯДЯЩИЕ КАК ГРУППЫ, НО РАСПОЗНАННЫЕ КАК ДИСЦИПЛИНЫ ({len(groups_as_disciplines)}):\n")
            f.write("-" * 80 + "\n")
            for result in groups_as_disciplines[:30]:
                f.write(f"  `{result.text}`")
                types_str = ', '.join(f"{name}({p*100:.0f}%)" for name, p in sorted(result.matched_types, key=lambda x: x[1], reverse=True))
                f.write(f" -> {types_str}\n")
            f.write("\n")
        
        # Строки, которые выглядят как дисциплины, но распознаны как группы
        disciplines_as_groups = []
        for result in all_conflicts:
            has_group = any(name == 'group' for name, _ in result.matched_types)
            has_discipline = any(name == 'discipline' for name, _ in result.matched_types)
            # Проверяем формат дисциплины (только заглавные буквы, без дефисов)
            import re
            looks_like_discipline = bool(re.match(r'^[А-ЯЁA-Z]{2,20}$', result.text))
            
            if has_group and looks_like_discipline and not has_discipline:
                disciplines_as_groups.append(result)
        
        if disciplines_as_groups:
            f.write(f"СТРОКИ, ВЫГЛЯДЯЩИЕ КАК ДИСЦИПЛИНЫ, НО РАСПОЗНАННЫЕ КАК ГРУППЫ ({len(disciplines_as_groups)}):\n")
            f.write("-" * 80 + "\n")
            for result in disciplines_as_groups[:30]:
                f.write(f"  `{result.text}`")
                types_str = ', '.join(f"{name}({p*100:.0f}%)" for name, p in sorted(result.matched_types, key=lambda x: x[1], reverse=True))
                f.write(f" -> {types_str}\n")
            f.write("\n")
    
    print(f"Отчёт сохранён в файл: {output_file}")


def main():
    """Основная функция"""
    print("Загрузка типов ячеек...")
    
    # Указываем путь к конфигу
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    config_path = os.path.join(project_root, 'cnf', 'cell_types.yml')
    
    cell_types = read_cell_types(config_file=config_path)
    classifier = CellClassifier(cell_types.values())
    
    print("Загрузка тестовых данных...")
    values_by_file = load_test_data()
    
    print("Классификация данных...")
    results_by_file = {}
    
    for file_name, values in values_by_file.items():
        print(f"  Обработка {file_name} ({len(values)} значений)...")
        results = []
        for text in values:
            if not text or len(text.strip()) < 1:
                continue
            result = classify_text(text, classifier, min_precision=0.30)
            result.file_source = file_name
            results.append(result)
        results_by_file[file_name] = results
    
    print("\nГенерация отчёта...")
    generate_report(results_by_file)
    
    print("\nАнализ завершён!")


if __name__ == '__main__':
    main()

