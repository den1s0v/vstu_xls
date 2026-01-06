# Тест паттернов типа "teacher", особенно паттерна с confidence 0.80

import os
import sys

# Добавляем путь к src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from tests_bootstrapper import init_testing_environment

init_testing_environment()

from vstuxls.string_matching import read_cell_types


def test_teacher_patterns():
    """Тестирование паттернов типа 'teacher'"""

    # Загружаем типы ячеек
    cell_types = read_cell_types(config_file='../cnf/cell_types.yml')
    teacher_type = cell_types.get('teacher')

    if not teacher_type:
        print("ERROR: Тип 'teacher' не найден в cell_types.yml!")
        return

    print("=" * 80)
    print("ТЕСТИРОВАНИЕ ПАТТЕРНОВ ТИПА 'teacher'")
    print("=" * 80)
    print(f"\nОписание: {teacher_type.description}")
    print(f"Количество паттернов: {len(teacher_type.patterns)}")
    print("\nПаттерны (по убыванию confidence):")
    for i, p in enumerate(teacher_type.patterns, 1):
        print(f"  {i}. confidence={p.confidence:.2f}, pattern='{p.pattern}', syntax='{p.pattern_syntax}'")

    # Тестовые примеры, особенно для паттерна с confidence 0.80
    test_cases = [
        # Примеры из комментариев в YAML
        "Рыжова(1)",
        "Чечет(нем)",

        # Простые фамилии
        "Рыжова",
        "Иванов",
        "Петрова",
        "Смирнов",

        # Фамилии с дефисом
        "Иванов-Петров",
        "Смирнова-Иванова",

        # Фамилии с номером в скобках
        "Рыжова(1)",
        "Иванов(2)",
        "Петрова(3)",

        # Фамилии с языком в скобках
        "Чечет(нем)",
        "Иванов(англ)",
        "Петрова(фр)",
        "Смирнов(франц)",
        "Иванов(франц.)",

        # Фамилии с запятой в конце
        "Рыжова,",
        "Иванов,",
        "Петрова,",

        # Фамилии с запятой и номером
        "Рыжова(1),",
        "Чечет(нем),",

        # Сложные случаи
        "Иванов-Петров(1)",
        "Смирнова-Иванова(англ)",
        "Рыжова-Иванова(нем),",

        # Буква 'Х' (вакансия)
        "Х",

        # Должны НЕ матчиться как teacher
        "ИВТ-360",  # группа
        "А 610",    # аудитория
        "МАТЕМАТИКА",  # дисциплина
        "доц. Грачёва Н.В.",  # должно матчиться паттерном с confidence 1.00
    ]

    print("\n" + "=" * 80)
    print("РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ")
    print("=" * 80)

    results_by_pattern = {}

    for test_str in test_cases:
        match = teacher_type.match(test_str)

        if match:
            pattern_idx = teacher_type.patterns.index(match.pattern)
            pattern_key = f"pattern_{pattern_idx}_conf_{match.pattern.confidence:.2f}"

            if pattern_key not in results_by_pattern:
                results_by_pattern[pattern_key] = {
                    'pattern': match.pattern,
                    'matches': []
                }

            results_by_pattern[pattern_key]['matches'].append({
                'input': test_str,
                'matched': match.re_match[0] if match.re_match else test_str,
                'precision': match.precision
            })
        else:
            if 'no_match' not in results_by_pattern:
                results_by_pattern['no_match'] = {'matches': []}
            results_by_pattern['no_match']['matches'].append({
                'input': test_str
            })

    # Выводим результаты по каждому паттерну
    for pattern_key, data in sorted(results_by_pattern.items()):
        if pattern_key == 'no_match':
            print(f"\n{'=' * 80}")
            print("НЕ СОВПАЛО (no match):")
            print(f"{'=' * 80}")
            for item in data['matches']:
                print(f"  ✗ '{item['input']}'")
        else:
            pattern = data['pattern']
            print(f"\n{'=' * 80}")
            print(f"ПАТТЕРН: confidence={pattern.confidence:.2f}")
            print(f"  pattern: '{pattern.pattern}'")
            print(f"  syntax: '{pattern.pattern_syntax}'")
            print(f"{'=' * 80}")
            for item in sorted(data['matches'], key=lambda x: x['input']):
                matched_text = item['matched']
                precision = item['precision']
                marker = "✓" if precision >= 0.5 else "?"
                print(f"  {marker} '{item['input']}' → matched: '{matched_text}' (precision: {precision:.2f})")

    # Специальный фокус на паттерне с confidence 0.80
    print(f"\n{'=' * 80}")
    print("ФОКУС НА ПАТТЕРНЕ С CONFIDENCE 0.80")
    print(f"{'=' * 80}")

    target_pattern = None
    for p in teacher_type.patterns:
        if abs(p.confidence - 0.80) < 0.01:
            target_pattern = p
            break

    if target_pattern:
        print(f"\nПаттерн: '{target_pattern.pattern}'")
        print(f"Синтаксис: '{target_pattern.pattern_syntax}'")
        print("\nТестирование отдельных примеров:")

        focus_cases = [
            "Рыжова",
            "Рыжова(1)",
            "Чечет(нем)",
            "Иванов(англ)",
            "Петрова(фр)",
            "Рыжова,",
            "Рыжова(1),",
            "Иванов-Петров",
            "Иванов-Петров(1)",
        ]

        for case in focus_cases:
            match = target_pattern.match(case)
            if match:
                matched = match.re_match.group(0) if match.re_match else case
                print(f"  ✓ '{case}' → matched: '{matched}'")
                if match.re_match:
                    print(f"    groups: {match.re_match.groups()}")
                    print(f"    groupdict: {match.re_match.groupdict()}")
            else:
                print(f"  ✗ '{case}' → НЕ СОВПАЛО")
    else:
        print("\nПаттерн с confidence 0.80 не найден!")

    print(f"\n{'=' * 80}\n")


if __name__ == '__main__':
    test_teacher_patterns()

