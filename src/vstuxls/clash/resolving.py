from collections import deque
from loguru import logger

from clash.clashing_element import *
from utils import sorted_list

# Максимальная глубина рекурсии
MAX_RECURSION_DEPTH = 25
# Максимальный размер для полного перебора (при превышении используется жадная стратегия)
MAX_SIZE_FOR_FULL_SEARCH = 50


def fill_clashing_elements(universe: 'ClashingElementSet'):
    """ Add sets elem.data.* for each `elem` in universe:
    - globally_clashing
    - globally_independent
    - neighbours: independent elements sharing common clashing elements.
    """

    for elem in universe:
        elem.data.globally_clashing = elem.all_clashing_among(universe)
        elem.data.globally_independent = elem.all_independent_among(universe)

    for elem in universe:
        clashing = elem.data.globally_clashing
        if not clashing:
            elem.data.neighbours = set()

        independent = elem.data.globally_independent
        # clashing twice, filtered by (limited to) independent
        elem.data.neighbours = ClashingElementSet(universe.get_all_clashing() & independent)
        # elem.data.neighbours.remove(elem)  # not a neighbour of itself.

    return universe


def find_spot_arrangements_optimized(basis: 'ClashingElementSet',
                                     universe: 'ClashingElementSet',
                                     element_limit=None,
                                     max_iterations=100) -> set[Arrangement]:
    """Оптимизированная версия find_spot_arrangements с ограничением итераций и альтернатив"""
    
    arrangement = Arrangement(basis)
    arrangements: set[Arrangement] = {arrangement}
    iterations = 0
    
    # Обход в ширину с ограничением
    while iterations < max_iterations:
        neighbour_sets = arrangement.closest_neighbour_sets_from(universe)
        if not neighbour_sets:
            break
        
        iterations += 1
        
        # Кластеризация соседей
        neighbours, *rest = [*neighbour_sets]
        
        # Ограничиваем количество альтернативных вариантов (только первые 3)
        for alt_neighbours in rest[:3]:
            if not alt_neighbours:
                continue
            
            partial_arrangement = ClashingElementSet(arrangement | alt_neighbours)
            
            if element_limit is not None and len(partial_arrangement) >= element_limit:
                arrangements.add(Arrangement(partial_arrangement))
            else:
                # Упрощенный подход: создаем arrangement и проверяем, можно ли добавить соседей
                extended = Arrangement(partial_arrangement)
                extended_neighbours = extended.closest_neighbour_sets_from(universe)
                if extended_neighbours:
                    # Добавляем только первый вариант для упрощения
                    first_neighbours = next(iter(extended_neighbours), None)
                    if first_neighbours:
                        ok, _ = extended.try_add_all(first_neighbours)
                        if ok:
                            arrangements.add(extended)
                else:
                    arrangements.add(extended)
        
        if not neighbours:
            break
        
        ok, bad = arrangement.try_add_all(neighbours)
        assert ok, bad
        
        if element_limit is not None and len(arrangement) >= element_limit:
            break
    
    # Фильтруем только самые длинные
    arrangements = retain_longest_only(arrangements)
    
    return arrangements


def resolve_clashes5_greedy(clashing_set: 'ClashingElementSet',
                            element_limit=None,
                            accumulated_free: 'ClashingElementSet' = None) -> set['ClashingElementSet']:
    """Жадная версия для больших наборов данных (>50 элементов)"""
    if accumulated_free is None:
        accumulated_free = ClashingElementSet()
    
    arrangements = set()
    
    # Сортируем по количеству конфликтов (убывание)
    sorted_elements = sorted(
        clashing_set,
        key=lambda e: len(e.data.globally_clashing) if e.data.globally_clashing else 0,
        reverse=True
    )
    
    # Жадный выбор: пытаемся добавить как можно больше элементов в одно arrangement
    current_arrangement = Arrangement(accumulated_free)
    
    for elem in sorted_elements:
        if element_limit is not None and len(current_arrangement) >= element_limit:
            break
        
        if current_arrangement.try_add(elem):
            continue
        else:
            # Не можем добавить - начинаем новое arrangement
            if len(current_arrangement) > len(accumulated_free):
                arrangements.add(current_arrangement)
            current_arrangement = Arrangement(accumulated_free | {elem})
    
    # Добавляем последнее arrangement, если оно не пустое
    if len(current_arrangement) > len(accumulated_free):
        arrangements.add(current_arrangement)
    
    return arrangements if arrangements else {Arrangement(accumulated_free)}


def resolve_clashes5_iterative(clashing_set: 'ClashingElementSet',
                               element_limit=None,
                               _max_depth=MAX_RECURSION_DEPTH) -> set['ClashingElementSet']:
    """Итеративная версия с использованием стека вместо рекурсии"""
    
    # Стек для хранения состояний: (clashing_set, always_free, element_limit)
    stack = deque([(clashing_set, ClashingElementSet(), element_limit)])
    final_arrangements = set()
    
    while stack:
        # Проверка глубины стека
        if len(stack) > _max_depth:
            logger.warning(f'resolve_clashes5_iterative: too high stack depth: {len(stack)}')
            # Обрабатываем текущий элемент жадной стратегией
            current_set, accumulated_free, current_limit = stack.popleft()
            if len(current_set) > 0:
                greedy_results = resolve_clashes5_greedy(current_set, current_limit, accumulated_free)
                final_arrangements.update(greedy_results)
            continue
        
        current_set, accumulated_free, current_limit = stack.popleft()
        
        # Early exits
        if len(current_set) <= 1:
            if current_set:
                final_arrangements.add(Arrangement(accumulated_free | current_set))
            elif accumulated_free:
                final_arrangements.add(Arrangement(accumulated_free))
            continue
        
        always_free = current_set.free_subset()
        
        if len(current_set) == len(always_free):
            final_arrangements.add(Arrangement(accumulated_free | always_free))
            continue
        
        # Убираем свободные элементы
        clashing_only = current_set.with_removed(*always_free)
        new_accumulated_free = accumulated_free | always_free
        
        # Если размер задачи слишком большой, используем жадный подход
        if len(clashing_only) > MAX_SIZE_FOR_FULL_SEARCH:
            greedy_results = resolve_clashes5_greedy(clashing_only, current_limit, new_accumulated_free)
            for arr in greedy_results:
                final_arrangements.add(Arrangement(new_accumulated_free | arr))
            continue
        
        # Оптимизация: сортируем элементы по количеству конфликтов (убывание)
        unused_elements = sorted(
            clashing_only,
            key=lambda e: len(e.data.globally_clashing) if e.data.globally_clashing else 0,
            reverse=True
        )
        
        # Обрабатываем первый элемент (остальные будут обработаны через unresolved в стеке)
        if unused_elements:
            elem = unused_elements[0]
            
            spot_arrangements = find_spot_arrangements_optimized(
                ClashingElementSet({elem}),
                clashing_only,
                current_limit
            )
            
            for arrangement in spot_arrangements:
                ready = new_accumulated_free | arrangement
                unresolved = arrangement.select_candidates_from(clashing_only)
                
                # Если unresolved пустое или маленькое, добавляем в результат
                if not unresolved or len(unresolved) <= 1:
                    if unresolved:
                        final_arrangements.add(Arrangement(ready | unresolved))
                    else:
                        final_arrangements.add(Arrangement(ready))
                else:
                    # Добавляем в стек для дальнейшей обработки
                    new_limit = current_limit - len(ready) if current_limit is not None else None
                    stack.append((unresolved, ready, new_limit))
    
    return final_arrangements


@cache
def resolve_clashes5(clashing_set: 'ClashingElementSet',
                     element_limit=None,
                     _depth=0) -> set['ClashingElementSet']:
    """ Нахождение всех локально оптимальных раскладок элементов, в которых они не пересекаются """
    # кластеризация накладок.

    # Проверка глубины рекурсии - переключаемся на итеративную версию
    if _depth > MAX_RECURSION_DEPTH:
        logger.warning(f'resolve_clashes5: max depth exceeded: {_depth}, switching to iterative/greedy')
        return resolve_clashes5_iterative(clashing_set, element_limit, _max_depth=MAX_RECURSION_DEPTH)

    if len(clashing_set) <= 1:
        # early exit: only one variant exists for the input of size 1 or 0.
        return {clashing_set, }

    always_free = clashing_set.free_subset()

    if len(clashing_set) == len(always_free):
        # Ничто ни с чем не конфликтуeт
        return {clashing_set, }

    # Для больших наборов используем итеративную версию
    if len(clashing_set) > MAX_SIZE_FOR_FULL_SEARCH:
        return resolve_clashes5_iterative(clashing_set, element_limit, _max_depth=MAX_RECURSION_DEPTH)

    # Далее рассматриваем только конфликтующие (заменили входную переменную!)
    clashing_set = clashing_set.with_removed(*always_free)

    # Все варианты раскладок неконфликтующих элементов.
    arrangements: set['Arrangement'] = set()

    # Оптимизация: сортируем элементы по количеству конфликтов (убывание)
    # Элементы с большим числом конфликтов обрабатываем первыми
    unused_elements = sorted(
        clashing_set,
        key=lambda e: len(e.data.globally_clashing) if e.data.globally_clashing else 0,
        reverse=True
    )

    @cache
    def find_spot_arrangements(basis: 'ClashingElementSet') -> set[Arrangement]:
        return find_spot_arrangements_optimized(basis, clashing_set, element_limit)

    while unused_elements:
        elem = unused_elements.pop(0)

        spot_arrangements = find_spot_arrangements(ClashingElementSet({elem}))

        for arrangement in spot_arrangements:

            ready = always_free | arrangement

            unresolved = arrangement.select_candidates_from(clashing_set)

            # Ранний выход для пустых подзадач
            if not unresolved:
                arrangements.add(Arrangement(ready))
                continue

            # Ранний выход для маленьких подзадач
            if len(unresolved) == 1:
                arrangements.add(Arrangement(ready | unresolved))
                continue

            # Все несвободные группируются в новый кластер и подаются в рекурсивный вызов.
            # Note: recursive call !
            sub_arrangements = resolve_clashes5(
                unresolved,
                element_limit=element_limit - len(ready) if element_limit is not None else element_limit,
                _depth=_depth + 1,
            )

            # Полученные под-раскладки комбинируются с текущими свободными.
            for sa in sub_arrangements:
                arrangements.add(Arrangement(ready | sa))

    return arrangements
