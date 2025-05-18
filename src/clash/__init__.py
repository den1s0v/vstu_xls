"""
Подсистема для разрешения наложений / накладок при выборе лучшей комбинации совпадений паттернов.

На вход подаётся набор элементов, которые могут пересекаться между собой в произвольном соотношении.
На выходе формируется набор таких подмножеств данных элементов, что в каждом подмножестве:
    • ни один элемент с другим не пересекается (не конфликтует), и 
    • больше ни одного элемента в него добавить нельзя.
Набор подмножеств формируется таким образом, что каждый из входных элементов присутствует хотя бы в одном из подмножеств.
Гарантируется, что все нетривиально различные раскладки/группировки элементов представлены в результате).

Задача решается в абстрактных терминах, 
так что вызывающий код волен самостоятельно определять, 
что есть накладка между элементами.
Чтобы указать, что некоторая пара элементов конфликтует, нужно снабдить  эти элементы одинаковыми компонентами.


"""

from typing import Any, Hashable, Iterable
# from collections import Or

from dataclasses import Field, dataclass
from adict import adict


_pair_compatibity_checker: callable = None


def find_combinations_of_compatible_elements(
    elements: Iterable, 
    pair_compatibity_checker=None, 
    components_getter=None) -> list:
    """ Главная функция .
    """
    assert pair_compatibity_checker or components_getter, "Any of parameters: `pair_compatibity_checker` or `components_getter` should be set!"

    return []
    


class ClashResolver:
    def resolve(self):
        ...
        



@dataclass()
class ObjWithDataWrapper(Hashable):
    """ A generic wrapper for an arbitrary object, 
        optionally associated with some arbitrary data
    """
    obj: Hashable
    data: adict = Field(default_factory=adict)

    def __hash__(self):
        return self.obj.__hash__()



class ClashingElement(ObjWithDataWrapper):
    # clashes_with: set['ClashingElement']
    # cluster: None | int
    
    def clashes_with(self, other: 'ClashingElement'):
        assert _pair_compatibity_checker
        return not _pair_compatibity_checker(self, other)
    
    def kee(self):
        return not self.clashes_with

    

class ClashingContainer(ClashingElement):
    components: set['ClashingComponent']
    
    def clashes_with(self, other: 'ClashingContainer'):
        assert isinstance(other, ClashingContainer), type(other)
        return bool(self.components & other.components)
    
    def is_free(self):
        return all(
            self in i.belonds_to and len(i.belonds_to) == 1
            for i in self.components)


class ClashingComponent(ObjWithDataWrapper):
    belonds_to: set['ClashingContainer']
    
