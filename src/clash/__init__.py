"""
Подсистема для разрешения наложений / накладок при выборе лучшей комбинации совпадений паттернов.

На вход подаётся набор элементов, которые могут пересекаться между собой в произвольном соотношении.
На выходе формируется набор таких подмножеств данных элементов, что в каждом подмножестве:
    • ни один элемент не пересекается (не конфликтует) с другим, и 
    • нельзя добавить в него больше ни одного элемента, не нарушив предыдущее условие.
Набор подмножеств формируется таким образом, что каждый из входных элементов присутствует хотя бы в одном из подмножеств.
Гарантируется, что все нетривиально различные раскладки/группировки элементов представлены в результате).

Задача решается в абстрактных терминах, 
так что вызывающий код волен самостоятельно определять, 
что есть накладка между элементами.
Чтобы указать, что некоторая пара элементов конфликтует, нужно снабдить эти элементы одинаковыми компонентами.


"""

from typing import Iterable
# from collections import Or

from clash.clashing_element import *


def find_combinations_of_compatible_elements(
        elements: Iterable,
        pair_compatibility_checker=None,
        components_getter=None) -> list[list]:
    """ Главная функция.

    Returns
        One or more subsets of given elements, sorted for stability.
    """

    assert pair_compatibility_checker or components_getter, "Any of parameters: `pair_compatibility_checker` or `components_getter` should be set!"

    # # Вспомогательное для объединения и наполнения компонентов
    # hash2component: dict[int, ClashingComponent] = {}

    # def get_component(component_obj, container: ClashingContainer) -> ClashingComponent:
    #     """ Get or create component """
    #     h = hash(component_obj)
    #     comp = hash2component.get(h)
    #     if not comp:
    #         hash2component[h] = comp = ClashingComponent(component_obj)
    #     comp.belonds_to.add(container)
    #     return comp

    # # Подготовить объекты, упаковав их в наши обёртки
    # clashing_elements = []

    # for element in elements:
    #     if components_getter:
    #         el = ClashingContainer(
    #             obj=element, 
    #             components={
    #                 get_component(component, element)
    #                 for component in components_getter(element)
    #             }
    #         )
    #     else:
    #         el = ClashingElement(obj=element)

    #     clashing_elements.append(el)

    clashing_set = ClashingElementSet.make(
        elements,
        # pair_compatibility_checker,
        components_getter,
    )

    if pair_compatibility_checker:
        set_pair_compatibility_checker(pair_compatibility_checker)

    # return ClashResolver({
    #     hash(ce): ce
    #     for ce in clashing_set
    # }).resolve()
    clash_sets = resolve_clashes(clashing_set)
    # Extract objects back
    return sorted_list(
        # {clash_elem.obj for clash_elem in clash_set}
        clash_set.get_bare_objs()
        for clash_set in clash_sets
    )


def resolve_clashes(clashing_set: 'ClashingElementSet') -> set['ClashingElementSet']:
    """ Нахождение всех локально оптимальных раскладок элементов, где они не пересекаются.
    (Алгоритм для разреженного размещения элементов.)
     """
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

    # Все варианты неконфликтующих раскладок.
    arrangements: set['ClashingElementSet'] = set()


    # Внутри кластера перебираем все элементы по очереди:
    for elem in clashing_set:

        # Сделать текущий свободным (убрать все мешающие).
        directly_clashing = elem.all_clashing_among(clashing_set)

        if not directly_clashing:
            # Текущий ни с чем не конфликтует. Про остальные ничего не знаем.
            # Сюда мы не должны зайти, т.к. выше такие отсеяли
            continue

        # Все, кроме непосредственно конфликтующих с текущим.
        partially_free_set = clashing_set.with_removed(*directly_clashing)

        # Все освобождённые идут в раскладку сразу.
        released = partially_free_set.free_subset()

        unresolved = partially_free_set.with_removed(*released)

        # Все несвободные группируются в новый кластер и подаются в рекурсивный вызов.
        sub_arrangements = resolve_clashes(unresolved)  # recursive call !


        # Полученные под-раскладки комбинируются с текущими свободными.
        for sa in sub_arrangements:
            arrangements.add(ClashingElementSet(always_free | released | sa))

    # Выделение неконфликтующих раскладок.
    # Отделяем полностью свободные элементы от остальных.
    # Внутри кластера перебираем все элементы по очереди:
    # Сделать текущий свободным (убрать все мешающие).
    # Все освобождённые идут в текущую раскладку сразу.
    # Все несвободные группируются в новый кластер и подаются в рекурсивный вызов.
    # Полученные под-раскладки комбинируются со свободными и текущими освобождёнными на этой итерации.

    return arrangements


def fill_clashing_elements(clashing_set: 'ClashingElementSet'):
    """ Add sets elem.data.* for each `elem` in clashing_set:
    - globally_clashing
    - globally_independent
    - neighbours: independent elements sharing common clashing ones.
    """

    for elem in clashing_set:
        elem.data.globally_clashing = elem.all_clashing_among(clashing_set)
        elem.data.globally_independent = elem.all_independent_among(clashing_set)

    for elem in clashing_set:
        clashing = elem.data.globally_clashing
        if not clashing:
            elem.data.neighbours = set()

        independent = elem.data.globally_independent
        # clashing twice, filtered by (limited to) independent
        elem.data.neighbours = ClashingElementSet(clashing_set.get_all_clashing() & independent)
        # elem.data.neighbours.remove(elem)  # not a neighbour of itself.

    return clashing_set


def resolve_clashes2(clashing_set: 'ClashingElementSet') -> set['ClashingElementSet']:
    """ Нахождение всех локально оптимальных раскладок элементов, где они не пересекаются """
    # кластеризация накладок.

    if len(clashing_set) <= 1:
        # early exit: only one variant exists for the input of size 1 or 0.
        return {clashing_set, }

    """
    (Алгоритм для плотного размещения элементов.)

    Инициализируем и наполняем цепочки-кандидаты, из которых будут получены итоговые раскладки, максимально 2^N.

    Для каждого элемента-кандидита:
        Решить, в какие цепочки его следует добавить:
            Для каждой [активной] цепочки^
              - НЕ добавляем, делая копию последнего состовния цепочки
              - Добавляем сразу те, которые имеют общие несовместимые элементы.
              - создаём новую цепочку для этого, если в остальных он нигде не является полностью свободным (во всём set)
            Обрботать "задвоение" цепочек по принципу подмножеств -- удалить избыточные.

    """

    # always_free = clashing_set.free_subset()

    # if len(clashing_set) == len(always_free):
    #     # Ничто ни с чем не конфликтуeт
    #     return {clashing_set, }

    # # Далее рассматриваем только конфликтующие (заменили входную переменную!)
    # clashing_set = clashing_set.with_removed(*always_free)

    # # Все варианты неконфликтующих раскладок.
    # arrangements: set['ClashingElementSet'] = set()


    # return arrangements


def sorted_list(s: set | list | Iterable) -> list:
    """ Make sorted list from a set """
    arr = list(s)
    arr.sort()
    return arr
