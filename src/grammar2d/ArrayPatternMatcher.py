from collections import defaultdict
from dataclasses import dataclass
from itertools import product

from loguru import logger

from clash import find_combinations_of_compatible_elements, trivial_components_getter
from geom2d import Box, Direction, RIGHT, DOWN, RangedBox, open_range, Point
from grammar2d import ArrayPattern
from grammar2d.PatternMatcher import PatternMatcher
from grammar2d.Match2d import Match2d


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

        def matches_from_boxes(boxes) -> list[Match2d]:
            """ "Backward" mapping keeping order """
            matches = []
            for b in boxes:
                for m in occurrences:
                    if m.box == b:
                        matches.append(m)
                        break
            return matches

        if self.pattern.direction == 'fill':
            clusters = self._find_fill_groups(all_boxes)
        else:
            # Направление просмотра
            direction = {
                'row': RIGHT,
                'column': DOWN,
            }[pattern_direction]
            clusters = self._find_groups_along_lines(all_boxes, direction)

        item_count = self.pattern.item_count  # ???
        matches = []

        for cluster in clusters:
            subclusters = self.try_breakdown_cluster(cluster)
            for subcluster in subclusters:
                item_matches = matches_from_boxes(subcluster)
                m = Match2d(self.pattern,
                            component2match=dict(enumerate(item_matches)))
                # recalc precision
                m.calc_precision(force=True)
                matches.append(m)

        # for cluster in clusters:
        #     if not cluster or len(cluster) not in item_count:
        #         # Size of the cluster is not satisfiable for the pattern.
        #         if item_count.stop is not None and len(cluster) > item_count.stop:
        #             # Handle the case of "TOO MANY"
        #             # Too large cluster to be accepted as-is.
        #             if not self.pattern.allow_breakdown:
        #                 # Cannot split & cannot accept.
        #                 continue
        #
        #             # TODO: try to split large the cluster.
        #
        #             logger.warning(f'GRAMMAR WARN: pattern `{self.pattern.name}` expects up to {
        #             item_count.stop} items, so sequence of {len(cluster)} elements has been cropped.')
        #             # Get first N elements, drop the remaining.
        #             matches_subset = self._remove_extra_matches(matches_from_boxes(cluster), item_count.stop)
        #             cluster = [m.box for m in matches_subset]
        #         else:
        #             # The case of "TOO FEW": no match
        #             continue
        #
        #     bbox = Box.union(*cluster)  # bounding box: union of group's boxes
        #
        #     satisfies = self.pattern.check_constraints_for_bbox(bbox)
        #
        #     if satisfies:
        #         # Make a Match for the cluster.
        #         sub_matches = matches_from_boxes(cluster)
        #         assert sub_matches, f"Failed to get back matches for boxes: {cluster}"
        #         # mean_precision = sum(m.precision for m in sub_matches) / len(sub_matches)
        #
        #         m = Match2d(self.pattern,
        #                     # precision=mean_precision,
        #                     # box=bbox,
        #                     component2match=dict(enumerate(sub_matches)))
        #         # recalc precision
        #         m.calc_precision(force=True)
        #         matches.append(m)

        return matches

    def calc_distance(self, box1: Box, box2: Box) -> int:
        if self.pattern.distance_kind == 'corner':
            return box1.manhattan_distance_to_touch(box2)
        if self.pattern.distance_kind == 'side':
            return box1.manhattan_distance_to_contact(box2)
        raise NotImplementedError(f'Unknown distance_kind: {self.pattern.distance_kind}')

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
                        if self.calc_distance(member, candidate) in gap:
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
        boxes_on_lines: dict[tuple[Direction, Direction], list[Box]] = defaultdict(list)

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
                    distance = self.calc_distance(box1, box2)
                    if distance in gap:
                        current_group.append(box2)
                    else:
                        groups.append(current_group)
                        current_group = [box2]

                # Add the last group, as well.
                groups.append(current_group)

        return groups

    def try_breakdown_cluster(self, cluster: list[Box]) -> list[list[Box]]:
        """ Разделить крупный кластер на составляющие,
            удовлетворяющие ограничениям численности и размера.

        План:
        1) Определить проблемы и цели:
            - превышение размера (размер ограничен)
            - превышение количества элементов (количество ограничено)
            - оба варианта
        2) Выполнить перебор вариантов разделить кластер прямоугольной сеткой на равные части,
            смещая сетку по координатам и поэтапно уменьшая размер ячейки сетки.
           Размер ячейки (квадранта) сетки должен всегда оставаться в пределах требуемого диапазона размера (size),
            но не меньше 1x1 и не больше размера собственно нашего крупного кластера.
           Каждая примерка ячейки сетки к кластеру даёт подмножество элементов,
            которое может быть пустым, подходить или не подходить по числу элементов.
           Если в какой-то момент (при определённом размере и положении ячеек)
            удалось уложить все элементы кластера в допустимые совпадения, то дальнейшее уменьшение размера сетки не
            производится.
        3) Все допустимые совпадения, обнаруженные до сих пор, собрать в одно множество,
             и выполнить для них разрешение накладок (resolve clashes).
        """
        # Параметры нашего кластера
        bbox = Box.union(*cluster)  # bounding box: union of group's boxes
        cluster_count = len(cluster)

        need_breakdown = False

        # Ограничения
        count_range = self.pattern.item_count

        # 1) Подготовка.
        if cluster_count in count_range:
            pass  # desired_count = cluster_count  # ???
        else:
            if cluster_count < count_range:
                # В кластере слишком мало элементов, делить нечего.
                return []
            elif not self.pattern.allow_breakdown:
                # Cannot split & cannot accept.
                return []
            need_breakdown = True

        sc = self.pattern.get_size_constraint()
        width_range, height_range = sc.size_range_tuple if sc else (open_range.parse('1+'),) * 2

        if bbox.w in width_range:
            # Диапазон c одним (текущим) значением
            width_range = open_range(bbox.w, bbox.w)
        else:
            # Ограничим ожидаемые диапазоны максимумом — размерами данного кластера
            width_range = width_range.intersect(open_range(1, bbox.w))
            if width_range is None:
                # Ширина кластера слишком мала, делить нечего.
                return []
            need_breakdown = True

        if bbox.h in height_range:
            # Диапазон c одним (текущим) значением
            height_range = open_range(bbox.h, bbox.h)
        else:
            # Ограничим ожидаемые диапазоны максимумом — размерами данного кластера
            height_range = height_range.intersect(open_range(1, bbox.h))
            if height_range is None:
                # Ширина кластера слишком мала, делить нечего.
                return []
            need_breakdown = True

        # satisfies = self.pattern.check_constraints_for_bbox(bbox)
        # if not satisfies:
        #     need_breakdown = True

        if not need_breakdown:
            # The cluster is OK.
            return [cluster]

        if not self.pattern.allow_breakdown:
            # Cannot accept & cannot split.
            return []

        # 2.1) Инициализация сетки, накладываемой на область кластера.

        # все комбинации размеров ячеек сетки (начиная с максимума)
        grid_cell_size_list = list(product(
            reversed(list(width_range)),
            reversed(list(height_range)),
        ))
        if grid_cell_size_list[0] == bbox.size:
            # отбросим первую комбинацию, которая равняется размерам кластера
            del grid_cell_size_list[0]

        # упорядочим по убыванию общего размера
        grid_cell_size_list.sort(key=sum, reverse=True)

        # 2.2) Перебор вариантов сетки.

        x0 = bbox.x
        y0 = bbox.y

        def point_quadrant(point: Point) -> tuple[int, int]:
            x = point.x - dx
            y = point.y - dy
            return (x - x0) // gw, (y - y0) // gh

        def box_quadrant(box: Box) -> tuple[int, int] | None:
            corner1_q, corner2_q = (
                point_quadrant(corner)
                for corner in box.iterate_corners('diagonal')
            )
            if corner1_q == corner2_q:
                return corner1_q
            else:
                # Крайние точки попадают в разные квадранты, попадания нет.
                return None

        q2boxes: dict[tuple[int, int], set[Box]] = defaultdict(set)

        for gw, gh in grid_cell_size_list:
            for dx, dy in product(range(0, -gw, -1), range(0, -gh, -1)):
                # for dx in range(0, -gw, -1):
                #     for dy in range(0, -gh, -1):
                # Перебираем все компоненты, отслеживая, в какой квадрант сетки он попадает
                not_suited = 0

                for box in cluster:
                    q = box_quadrant(box)
                    if q is None:
                        not_suited += 1
                        continue

                    # Подошёл, записываем в нужный квадрант
                    q2boxes[q].add(box)

                if not_suited == 0:
                    # удалось уложить все элементы кластера
                    break
            else:
                continue
            break

        # Отсеять те, что не попадают теперь по количеству элементов
        for k in list(q2boxes.keys()):
            delete = False

            count = len(q2boxes[k])
            if count not in count_range:
                delete = True

            bbox = Box.union(*cluster)  # bounding box: union of group's boxes
            satisfies = self.pattern.check_constraints_for_bbox(bbox)
            if not satisfies:
                delete = True

            if delete:
                del q2boxes[k]

        # 3.1) Все допустимые совпадения собрать в одно множество, и выполнить для них разрешение накладок.

        subclusters = [
            list(boxes)
            for boxes in q2boxes.values()
        ]

        arrangements: list[list[list[Box]]] = find_combinations_of_compatible_elements(
            subclusters,
            components_getter=trivial_components_getter,
            max_elements=count_range.stop
        )

        # 3.2) Проранжировать итоговые кластеры —
        # оставить максимальное покрытие и наиболее крупные (меньше по количеству самих кластеров)
        best_subclusters = max(
            arrangements,
            key=lambda subcluster: (
                sum(len(item) for item in subcluster),  # ↑ покрытие
                -len(subcluster),  # ↓ фрагментированность
            ),
            default=[])

        return best_subclusters
