from dataclasses import dataclass

from geom2d import Box, RangedBox
from grammar2d.ArrayPatternMatcher import ArrayPatternMatcher
from grammar2d.Match2d import Match2d


@dataclass
class ArrayInContextPatternMatcher(ArrayPatternMatcher):

    def _find_element_candidates(self):
        item_occurrences = super()._find_element_candidates()

        region = self._region

        if isinstance(region, RangedBox) and not region.is_deterministic():
            # Дополнить информацией о нахождении каждого элемента в однозначной или вероятной зоне родителя
            key1 = 'touches_probable_zone_map'
            max_box: RangedBox = None  # late init: see below
            min_box: RangedBox = None

            for m in item_occurrences:
                if key1 not in m.data:
                    touches_probable_zone_map = m.data[key1] = dict()
                else:
                    touches_probable_zone_map = m.data[key1]

                if region not in touches_probable_zone_map:
                    # not set yet.

                    if max_box is None or min_box is None:
                        # init vars to be used
                        max_box = region.maximal_box()
                        min_box = region.minimal_box()

                    is_in_probable_zone = max_box.covers(m.box) and not min_box.covers(m.box)

                    touches_probable_zone_map[region] = is_in_probable_zone

        return item_occurrences

    def _remove_extra_matches(self, matches: list[Match2d], limit: int) -> list[Match2d]:
        """ Логика того, как удалить лишние элементы из кластера,
            если превышено количество элементов в кластере.

            Здесь реализация исключает совпадения,
            попавшие на вероятностную границу допустимой области ("серую зону"),
            начиная с последних в списке, пока такие есть.
         """
        key1 = 'touches_probable_zone_map'
        region = self._region

        for m in reversed(matches):  ## [:] ??
            if len(matches) <= limit:
                break

            if key1 in m.data:
                touches_probable_zone_map = m.data[key1]
                if region in touches_probable_zone_map:
                    is_in_probable_zone = touches_probable_zone_map[region]
                    if is_in_probable_zone:
                        # Элемент в "серой зоне", его следует убрать в первую очередь.
                        matches.remove(m)

        if len(matches) > limit:
            # Всё ещё слишком много
            return super()._remove_extra_matches(matches, limit)

        return matches
