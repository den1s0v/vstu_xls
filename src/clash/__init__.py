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

from functools import cache
from typing import Any, Hashable, Iterable, override
# from collections import Or

from dataclasses import Field, dataclass, asdict
from adict import adict

from clash.clashing_element import *
from utils import global_var


def find_combinations_of_compatible_elements(
        elements: Iterable,
        pair_compatibility_checker=None,
        components_getter=None) -> list[list]:
    """ Главная функция .
    """

    assert pair_compatibility_checker or components_getter, "Any of parameters: `pair_compatibility_checker` or `components_getter` should be set!"

    # # Вспомогательное для объедиенния и наполнения компонентов
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
    return [
        # {clash_elem.obj for clash_elem in clash_set}
        clash_set.get_bare_objs()
        for clash_set in clash_sets
    ]


# @dataclass()
# class ClashResolver:
#     hash2element: dict[int, 'ClashingElement']

#     def resolve(self):
#         ...


# def resolve_clashes(clashing_elements: list['ClashingElement']) -> list[set['ClashingElement']]:
def resolve_clashes(clashing_set: 'ClashingElementSet') -> list['ClashingElementSet']:
    """ Нахождение всех локально оптимальных раскладок элементов, где они не пересекаются """
    # кластеризация накладок.

    # Выделение неконфликтующих раскладок.
    arrangements: list['ClashingElementSet'] = []

    # Элементы, полностью освобождённые при формировании раскладок (для них уже рскладки формировать не нужно, иначе это будет просто дублирование)
    released_elements = set()  # was ever in an arrangement, to avoid trivial duplicates.

    # Внутри кластера перебираем все элементы по очереди:
    for elem in clashing_set:
        if elem in released_elements:
            continue

        released_elements.add(elem)  # Этот мы точно освободим

        # Сделать текущий свободным (убрать все мешающие).
        directly_clashing = elem.all_clashing_among(clashing_set)

        if not directly_clashing:
            # Ничего ни с чем и не конфликтовало
            arrangement = clashing_set.clone()
            arrangements.append(arrangement)
            break

        partially_free_set = clashing_set.with_removed(*directly_clashing)

        # Все освобождённые идут в раскладку сразу и исключаются из дальнейшего перебора по внешнему циклу.
        released = partially_free_set.free_subset()
        released_elements |= released

        unresolved = partially_free_set.with_removed(released)

        # Все несвободные группируются в новый кластер и подаются в рекурсивный вызов.
        sub_arrangements = resolve_clashes(unresolved)  # recursive call !

        # Полученные под-раскладки комбинируются с текущими свободными.
        for sa in sub_arrangements:
            arrangements.append(ClashingElementSet(released.clone() | sa))

    # Выделение неконфликтующих раскладок.
    # Внутри кластера перебираем все элементы по очереди:
    # Сделать текущий свободным (убрать все мешающие).
    # Все освобождённые идут в раскладку сразу и исключаются из дальнейшего перебора по внешнему циклу.
    # Все несвободные группируются в новый кластер и подаются в рекурсивный вызов.
    # Полученные под-раскладки комбинируются с текущими свободными.

    return arrangements
