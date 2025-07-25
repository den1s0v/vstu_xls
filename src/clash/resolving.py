from clash.clashing_element import *
from utils import sorted_list


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


@cache
def resolve_clashes5(clashing_set: 'ClashingElementSet',
                     element_limit=None) -> set['ClashingElementSet']:
    """ Нахождение всех локально оптимальных раскладок элементов, в которых они не пересекаются """
    # кластеризация накладок.

    if len(clashing_set) <= 1:
        # early exit: only one variant exists for the input of size 1 or 0.
        return {clashing_set, }

    always_free = clashing_set.free_subset()

    if len(clashing_set) == len(always_free):
        # Ничто ни с чем не конфликтуeт
        return {clashing_set, }

    # Далее рассматриваем только конфликтующие (заменили входную переменную!)
    clashing_set = clashing_set.with_removed(*always_free)

    # Все варианты раскладок неконфликтующих элементов.
    arrangements: set['Arrangement'] = set()

    # Отсортируем элементы для однозначного порядка обхода
    unused_elements = sorted(clashing_set)

    @cache
    def find_spot_arrangements(basis: 'ClashingElementSet') -> set[Arrangement]:

        arrangement = Arrangement(basis)
        arrangements = {arrangement}

        # обход в ширину: пока "пятно соседей" растёт
        while neighbour_sets := arrangement.closest_neighbour_sets_from(clashing_set):

            # кластеризация соседей на несовместимые между собой подгруппы
            neighbours, *rest = [*neighbour_sets]

            for alt_neighbours in rest:
                if not alt_neighbours:
                    continue  # empty
                # recursive call (fork of this process) !
                arrangements |= find_spot_arrangements(ClashingElementSet(arrangement | alt_neighbours))

            if not neighbours:
                break  # empty

            ok, bad = arrangement.try_add_all(neighbours)
            assert ok, bad

            if element_limit is not None and len(arrangement) >= element_limit:
                # Stop growing if unnecessary (but do not crop what was found)
                break

        # Готово: пятно построено.

        # ??? Работает хорошо, но и выигрыша не заметно. На 1-5% может уменьшить число итоговых комбинаций. ↓
        arrangements = retain_longest_only(arrangements)

        return arrangements

    while unused_elements:
        elem = unused_elements.pop(0)

        spot_arrangements = find_spot_arrangements(ClashingElementSet({elem}))

        for arrangement in spot_arrangements:

            ready = always_free | arrangement

            unresolved = arrangement.select_candidates_from(clashing_set)

            # Все несвободные группируются в новый кластер и подаются в рекурсивный вызов.
            # recursive call !
            sub_arrangements = resolve_clashes5(
                unresolved,
                element_limit=element_limit - len(ready) if element_limit is not None else element_limit)

            # Полученные под-раскладки комбинируются с текущими свободными.
            for sa in sub_arrangements:
                arrangements.add(Arrangement(ready | sa))

    return arrangements
