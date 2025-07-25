"""
Подсистема для разрешения наложений / накладок при выборе лучшей комбинации совпадений паттернов.

На вход подаётся набор элементов, которые могут пересекаться между собой в произвольном соотношении.
На выходе формируется набор таких подмножеств данных элементов, что в каждом подмножестве:
    • ни один элемент не пересекается (не конфликтует) с другим, и 
    • нельзя добавить в него больше ни одного элемента, не нарушив предыдущее условие.

Формулировки идеальных требований к результатам работы подсистемы:
    1) Набор подмножеств формируется таким образом,
        что каждый из входных элементов присутствует хотя бы в одном из подмножеств.
    2) Гарантируется, что все нетривиально различные раскладки/группировки элементов представлены в результате).

На практике, однако, такой подход порой приводит к комбинаторному взрыву,
поэтому приходится отсекать часть вариантов, а именно те, которые покрывают меньше "площади"
    и меньше элементов в пользу раскладок с более полным покрытием.
В остальном алгоритм старается максимально придерживаться описанных требований.

Задача решается в абстрактных терминах, 
так что вызывающий код волен самостоятельно определять, 
что есть накладка между элементами.
Чтобы указать, что некоторая пара элементов конфликтует, нужно снабдить эти элементы одинаковыми компонентами.
"""

from clash.clashing_element import *
from clash.resolving import fill_clashing_elements, resolve_clashes5
from utils import sorted_list


def find_combinations_of_compatible_elements(
        elements: Iterable,
        pair_compatibility_checker=None,
        components_getter=None,
        max_elements: int = None
    ) -> list[list]:
    """ Главная функция.

    element_limit:

    Returns
        One or more subsets of given elements, sorted for stability.
    """

    assert pair_compatibility_checker or components_getter, "Any of parameters: `pair_compatibility_checker` or `components_getter` should be set!"

    # Оборачивание объектов во внутренние обёртки
    clashing_set = ClashingElementSet.make(
        elements,
        # pair_compatibility_checker,
        components_getter,
    )

    if pair_compatibility_checker:
        set_pair_compatibility_checker(pair_compatibility_checker)

    # Пред-вычисление взаимных накладок
    # (!!!) prepare for resolve_clashes*()
    fill_clashing_elements(clashing_set)

    clash_sets = resolve_clashes5(clashing_set,
                                  max_elements)  # latest and best implementation
    # Extract objects back
    return sorted_list(
        clash_set.get_bare_objs()
        for clash_set in clash_sets
    )
