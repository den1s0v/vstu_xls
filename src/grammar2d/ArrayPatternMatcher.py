from collections import defaultdict
from dataclasses import dataclass

from loguru import logger

from geom2d import Box, Direction, RIGHT, DOWN, RangedBox, open_range
from grammar2d import ArrayPattern
from grammar2d.PatternMatcher import PatternMatcher
from grammar2d.Match2d import Match2d
from grid import Region


@dataclass
class ArrayPatternMatcher(PatternMatcher):
    pattern: ArrayPattern

    _region: Box | RangedBox = None

    def find_all(self, region: Box | RangedBox = None, match_limit: open_range = None) -> list[Match2d]:
        """ Find all matches within whole document.
        If a region is given, find all matches within the region.
        Note: `match_limit` relates to count of matches returned (not number of items in a match).
        """
        # Dev WARN: setting this param as instance property may be thread-unsafe
        #  (if one matcher instance is used to match different regions at once).
        self._region = region

        item_occurrences = self._find_element_candidates()

        if not item_occurrences:
            return []

        # check expected number of items
        n = len(item_occurrences)
        if n < (self.pattern.item_count.start or 0):
            # Not enough elements even for one match.
            return []

        matches = []

        if len(item_occurrences) == 1:
            # There is only one occurrence, no need to analyze its placement.
            item_match = item_occurrences[0]

            satisfies = self.pattern.check_constraints_for_bbox(item_match.box)

            if satisfies:
                # make a Match duplicating the only occurrence.
                m = Match2d(self.pattern,
                            precision=item_match.precision,
                            box=item_match.box,
                            component2match={0: item_match})
                matches.append(m)
            return matches

        # найти ряды элементов, одинаково выровненных вдоль заданного направления
        matches = self._find_clusters(item_occurrences, match_limit=match_limit)

        return matches

    def _find_element_candidates(self):
        item = self.pattern.subpattern
        gm = self.grammar_matcher

        item_occurrences = gm.get_pattern_matches(item, self._region)
        return item_occurrences or []

    def _remove_extra_matches(self, matches: list[Match2d], limit: int) -> list[Match2d]:
        """ Логика того, как удалить лишние элементы из кластера,
            если превышено количество элементов в кластере.
            (Здесь реализация тривиальная, см. подклассы.)
             """
        return matches[:limit]

    def _find_clusters(self,
                       occurrences: list[Match2d],
                       pattern_direction: str = None,
                       match_limit: open_range = None,
                       ) -> list[Match2d]:
        if not pattern_direction:
            if self.pattern.direction == 'auto':
                # Ряд в любом направлении,
                # т.е. автоматический выбор из 'row' или 'column', — что оптимальнее (даёт меньше разрывных областей).
                matches_as_rows = self._find_clusters(occurrences, 'row')
                matches_as_columns = self._find_clusters(occurrences, 'column')
                # exclude any empty variant
                variants: list[list[Match2d]] = list(filter(None, [matches_as_rows, matches_as_columns]))
                # get the variant having less clusters
                return min(variants, key=len, default=[])

            pattern_direction = self.pattern.direction

        # Подготовка областей
        all_boxes = [m.box for m in occurrences]

        if self.pattern.direction == 'fill':
            clusters = self._find_fill_groups(all_boxes)
        else:
            # Направление просмотра
            direction = {
                'row': RIGHT,
                'column': DOWN,
            }[pattern_direction]
            clusters = self._find_groups_along_lines(all_boxes, direction)

        def matches_from_boxes(boxes) -> list[Match2d]:
            """ "Backward" mapping keeping order """
            matches = []
            for b in boxes:
                for m in occurrences:
                    if m.box == b:
                        matches.append(m)
                        break
            return matches

        item_count = self.pattern.item_count
        matches = []

        for cluster in clusters:
            if not cluster or len(cluster) not in item_count:
                # Size of the cluster is not satisfiable for the pattern.
                if item_count.stop is not None and len(cluster) > item_count.stop:
                    # Handle the case of "TOO MANY"
                    logger.warning(f'GRAMMAR WARN: pattern `{self.pattern.name}` expects up to {
                    item_count.stop} items, so sequence of {len(cluster)} elements has been cropped.')
                    # Get first N elements, drop the remaining.
                    matches_subset = self._remove_extra_matches(matches_from_boxes(cluster), item_count.stop)
                    cluster = [m.box for m in matches_subset]
                else:
                    # The case of "TOO FEW": no match
                    continue

            bbox = Box.union(*cluster)  # bounding box: union of group's boxes

            satisfies = self.pattern.check_constraints_for_bbox(bbox)

            if satisfies:
                # Make a Match for the cluster.
                sub_matches = matches_from_boxes(cluster)
                assert sub_matches, f"Failed to get back matches for boxes: {cluster}"
                mean_precision = sum(m.precision for m in sub_matches) / len(sub_matches)

                m = Match2d(self.pattern,
                            precision=mean_precision,
                            box=bbox,
                            component2match=dict(enumerate(sub_matches)))
                matches.append(m)
        return matches

    def _find_fill_groups(self, boxes: list[Box]) -> list[list[Box]]:
        """ Find connected clusters of arbitrary form without restriction on direction
        (a cluster may look like an oval or a snake, for instance).
        Pattern's `gap` determines a valid manhattan's distance between cluster's members.
        Note that current implementation does not check if the members are aligned with each other or not;
            the gap (distance) is the only criteria.
        """

        all_boxes = boxes[:]  # Обновляемый перечень (элементы уходят по мере формирования кластеров)
        gap = self.pattern.gap
        clusters = []

        while all_boxes:
            # init cluster
            current_cluster = [all_boxes.pop(0)]

            # Find more items for this cluster (complete search) ...
            while all_boxes:
                added_anything = False
                # For each of candidates (remaining unused boxes)
                for candidate in all_boxes[:]:
                    # For each of current cluster members
                    for member in reversed(current_cluster):
                        # If candidate is close enough to a member
                        if member.manhattan_distance_to_touch(candidate) in gap:
                            current_cluster.append(candidate)
                            all_boxes.remove(candidate)
                            added_anything = True
                            break

                if not added_anything:
                    break

            clusters.append(current_cluster)

        return clusters

    def _find_groups_along_lines(self, boxes: list[Box], direction: Direction) -> list[list[Box]]:
        """ Find clusters within lines along `direction`"""

        sides_primary = [direction - 90, direction + 90]
        sides_secondary = [direction - 180, direction]

        # Sort directions so that coordinates of associated sides are ordered (always `<=`).
        sides_primary.sort(key=lambda d: d.coordinate_sign)
        sides_secondary.sort(key=lambda d: d.coordinate_sign)

        # groups of aligned boxes
        boxes_on_lines: dict[tuple[int, int], list[Box]] = defaultdict(list)

        # Группировка совпадений по линиям
        for box in boxes:
            coords = tuple(box.get_side_dy_direction(d) for d in sides_primary)

            boxes_on_lines[coords].append(box)

        # sort each line
        secondary_side = sides_secondary[0]
        for line in boxes_on_lines.values():
            line.sort(key=lambda box: box.get_side_dy_direction(secondary_side))

        gap = self.pattern.gap
        groups: list[list[Box]] = []

        for line in boxes_on_lines.values():
            if len(line) == 1:
                groups.append(line)
            else:
                current_group = [line[0]]
                for box1, box2 in zip(line[:-1], line[1:]):
                    distance = box1.manhattan_distance_to_touch(box2)
                    if distance in gap:
                        current_group.append(box2)
                    else:
                        groups.append(current_group)
                        current_group = [box2]

                # Add the last group, as well.
                groups.append(current_group)

        return groups
