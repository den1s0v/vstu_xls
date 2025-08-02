from collections import defaultdict, Counter
from dataclasses import dataclass
from itertools import product

from loguru import logger

from clash import find_combinations_of_compatible_elements, trivial_components_getter
from geom2d import Box, Direction, RIGHT, DOWN, RangedBox, open_range, Point, VariBox
from grammar2d import ArrayPattern
from grammar2d.PatternMatcher import PatternMatcher
from grammar2d.Match2d import Match2d


@dataclass
class ArrayPatternMatcher(PatternMatcher):
    pattern: ArrayPattern

    _region: Box | RangedBox = None
    _neighbours: dict[Box, set[Box]] = None
    _not_neighbours: dict[Box, set[Box]] = None

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

        # item_count = self.pattern.item_count  # ???
        matches = []

        for cluster in clusters:
            subclusters = self.try_breakdown_cluster2(cluster)
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

    def are_neighbours(self, box1: Box, box2: Box) -> bool:
        if self._neighbours is None:
            self._neighbours = defaultdict(set)
            self._not_neighbours = defaultdict(set)

        if box1 in self._neighbours:
            if box2 in self._neighbours[box1]:
                return True

        if box1 in self._not_neighbours:
            if box2 in self._not_neighbours[box1]:
                return False

        distance = self.calc_distance(box1, box2)
        if distance in self.pattern.gap:
            self._neighbours[box1].add(box2)
            self._neighbours[box2].add(box1)
            return True
        else:
            self._not_neighbours[box1].add(box2)
            self._not_neighbours[box2].add(box1)
            return False

    def _find_fill_groups(self, boxes: list[Box] | set[Box]) -> list[list[Box]]:
        """ Find connected clusters of arbitrary form without restriction on direction
        (a cluster may look like an oval or a snake, for instance).
        Pattern's `gap` determines a valid manhattan's distance between cluster's members.
        Note that current implementation does not check if the members are aligned with each other or not;
            the gap (distance) is the only criteria.
        """

        all_boxes = list(boxes)  # Обновляемый перечень (элементы уходят по мере формирования кластеров)
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
                        if self.are_neighbours(member, candidate):
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
                    if self.are_neighbours(box1, box2):
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
        too_many = False

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
            too_many = True

        sc = self.pattern.get_size_constraint()
        width_range, height_range = sc.size_range_tuple if sc else (open_range.parse('1+'),) * 2

        if not too_many and bbox.w in width_range:
            # Диапазон c одним (текущим) значением
            width_range = open_range(bbox.w, bbox.w)
        else:
            # Ограничим ожидаемые диапазоны максимумом — размерами данного кластера
            width_range = width_range.intersect(open_range(1, bbox.w))
            if width_range is None:
                # Ширина кластера слишком мала, делить нечего.
                return []
            need_breakdown = True

        if not too_many and bbox.h in height_range:
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

        # упорядочим по площади,
        # возрастанию разности координат (более квадратные -- в начале)
        #  и убыванию общего размера
        grid_cell_size_list.sort(
            key=(lambda t: (
                -(t[0] * t[1]),  # ↓ площадь
                abs(t[0] - t[1]),  # ↓ вытянутость
                -(t[0] + t[1]),  # ↓ размер
            )))

        # 2.2) Перебор вариантов сетки.

        x0 = bbox.x
        y0 = bbox.y

        def point_quadrant(point: Point) -> tuple[int, int]:
            x = point.x - dx
            y = point.y - dy
            return (x - x0) // gw, (y - y0) // gh

        def box_quadrant(box: Box) -> tuple[int, int] | None:
            corner1, corner2 = box.iterate_corners('diagonal')
            # Сдвинуть правый нижний угол внутрь области
            # (иначе она попадёт на следующий квадрант)
            corner2 = Point(corner2.x - 1, corner2.y - 1, )
            corner1_q = point_quadrant(corner1)
            if corner1 == corner2:
                return corner1_q  # Если размер box: 1х1 (раннее завершение)

            corner2_q = point_quadrant(corner2)
            if corner1_q == corner2_q:
                return corner1_q
            else:
                # Крайние точки попадают в разные квадранты, попадания нет.
                return None

        q2boxes: dict[tuple[int, int, int, int], set[Box]] = defaultdict(set)

        for gw, gh in grid_cell_size_list:
            for dx, dy in product(range(0, -gw, -1), range(0, -gh, -1)):
                # Перебираем все компоненты, отслеживая, в какой квадрант сетки он попадает
                not_suited = 0
                counter = Counter(())

                for box in cluster:
                    q = box_quadrant(box)
                    if q is None:
                        not_suited += 1
                        continue

                    # Подошёл, записываем в нужный квадрант
                    k = (*q, gw, gh)  # уникальный набор для каждой комбинации размеров
                    q2boxes[k].add(box)
                    counter.update((k,))

                # Проверить численность добавленных в квадранты под-кластеров
                # (далее она меняться уже не будет)
                # Отсеять те кластеры-проекции, что не попадают теперь по количеству элементов.
                for k, n in counter.items():
                    if n not in count_range:
                        not_suited += 1
                        del q2boxes[k]

                if not_suited == 0:
                    # удалось уложить все элементы кластера
                    break
            else:
                continue
            break

        # Отсеять те, что не попадают теперь по количеству элементов
        for k in list(q2boxes.keys()):
            delete = False

            new_cluster = q2boxes[k]

            # count = len(new_cluster)
            # if count not in count_range:
            #     delete = True

            new_bbox = Box.union(*new_cluster)  # bounding box: union of group's boxes
            satisfies = self.pattern.check_constraints_for_bbox(new_bbox)
            if not satisfies:
                delete = True

            if delete:
                del q2boxes[k]

        # 3.1) Все допустимые совпадения собрать в одно множество, и выполнить для них разрешение накладок.
        #  Берём именно уникальные наборы, т.к. в разные квадранты разного размера
        #  могли попасть одинаковые наборы элементов.

        subcluster_set = {
            tuple(sorted(boxes))
            for boxes in q2boxes.values()
        }

        arrangements: list[list[list[Box]]] = find_combinations_of_compatible_elements(
            subcluster_set,
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

    def try_breakdown_cluster2(self, cluster: list[Box]) -> list[list[Box]]:
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
           UPD: Это подмножество может также быть несвязным и делиться на под-кластеры.
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
        too_many = False
        too_large = False

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
            too_many = True

        sc = self.pattern.get_size_constraint()
        width_range, height_range = sc.size_range_tuple if sc else (open_range.parse('1+'),) * 2

        fits_width = bbox.h in height_range
        if not too_many and fits_width:
            # Диапазон c одним (текущим) значением
            width_range = open_range(bbox.w, bbox.w)
        else:
            # Ограничим ожидаемые диапазоны максимумом — размерами данного кластера
            width_range = width_range.intersect(open_range(1, bbox.w))
            if width_range is None:
                # Ширина кластера слишком мала, делить нечего.
                return []
            need_breakdown = True
            if not fits_width:
                too_large = True

        fits_height = bbox.h in height_range
        if not too_many and fits_height:
            # Диапазон c одним (текущим) значением
            height_range = open_range(bbox.h, bbox.h)
        else:
            # Ограничим ожидаемые диапазоны максимумом — размерами данного кластера
            height_range = height_range.intersect(open_range(1, bbox.h))
            if height_range is None:
                # Ширина кластера слишком мала, делить нечего.
                return []
            need_breakdown = True
            if not fits_height:
                too_large = True

        # satisfies = self.pattern.check_constraints_for_bbox(bbox)
        # if not satisfies:
        #     need_breakdown = True

        if not need_breakdown:
            # The cluster is OK.
            return [cluster]

        if not self.pattern.allow_breakdown:
            # Cannot accept & cannot split.
            return []

        # 2.0) Если нет ограничений по размерам, то другой алгоритм.
        if not too_large:
            return self._split_to_subclusters_of_desired_count(cluster, count_range)

        # 2.1) Инициализация сетки, накладываемой на область кластера.

        # все комбинации размеров ячеек сетки (начиная с максимума)
        grid_cell_size_list = list(product(
            reversed(list(width_range)),
            reversed(list(height_range)),
        ))
        if grid_cell_size_list[0] == bbox.size:
            # отбросим первую комбинацию, которая равняется размерам кластера
            del grid_cell_size_list[0]

        # упорядочим по площади,
        # возрастанию разности координат (более квадратные -- в начале)
        #  и убыванию общего размера
        grid_cell_size_list.sort(
            key=(lambda t: (
                -(t[0] * t[1]),  # ↓ площадь
                abs(t[0] - t[1]),  # ↓ вытянутость
                -(t[0] + t[1]),  # ↓ размер
            )))

        # 2.2) Перебор вариантов сетки.

        x0 = bbox.x
        y0 = bbox.y

        def point_quadrant(point: Point) -> tuple[int, int]:
            x = point.x - dx
            y = point.y - dy
            return (x - x0) // gw, (y - y0) // gh

        def box_quadrant(box: Box) -> tuple[int, int] | None:
            corner1, corner2 = box.iterate_corners('diagonal')
            # Сдвинуть правый нижний угол внутрь области
            # (иначе она попадёт на следующий квадрант)
            corner2 = Point(corner2.x - 1, corner2.y - 1, )
            corner1_q = point_quadrant(corner1)
            if corner1 == corner2:
                return corner1_q  # Если размер box: 1х1 (раннее завершение)

            corner2_q = point_quadrant(corner2)
            if corner1_q == corner2_q:
                return corner1_q
            else:
                # Крайние точки попадают в разные квадранты, попадания нет.
                return None

        q2boxes: dict[tuple, set[Box]] = defaultdict(set)
        extra_i = 1

        for gw, gh in grid_cell_size_list:
            for dx, dy in product(range(0, -gw, -1), range(0, -gh, -1)):
                # Перебираем все компоненты, отслеживая, в какой квадрант сетки он попадает
                not_suited = 0
                # counter = Counter(())
                local_q2boxes: dict[tuple, set[Box]] = defaultdict(set)

                for box in cluster:
                    q = box_quadrant(box)
                    if q is None:
                        not_suited += 1
                        continue

                    # Подошёл, записываем в нужный квадрант
                    k = (*q, gw, gh, 0)  # уникальный набор для каждой комбинации размеров
                    local_q2boxes[k].add(box)
                    # counter.update((k,))

                # Проверить численность добавленных в квадранты под-кластеров
                # (далее она меняться уже не будет)
                # Отсеять те кластеры-проекции, что не попадают теперь по количеству элементов.
                i = 1
                for k in list(local_q2boxes.keys()):
                    boxes = local_q2boxes[k]
                    if len(boxes) < count_range:
                        # в квадранте слишком мало элементов.
                        not_suited += 1
                        del local_q2boxes[k]

                    # Попытаться разделить кластеры, т.к. они могли оказаться несвязанными
                    box_groups = self._find_fill_groups(boxes)
                    if len(box_groups) > 1:
                        # Квадрант содержит более одного кластера; целиком не берём.
                        del local_q2boxes[k]
                        # Добавим подгруппы как отдельные кластеры, ниже проверим их численность вместе со всеми.
                        for box_group in box_groups:
                            k2 = (extra_i,)
                            extra_i += 1
                            local_q2boxes[k2] = box_group

                for k in list(local_q2boxes.keys()):
                    if len(local_q2boxes[k]) not in count_range:
                        # в кластере слишком много или мало элементов.
                        not_suited += 1
                        del local_q2boxes[k]

                # Добавим к основным
                q2boxes |= local_q2boxes

                if not_suited == 0:
                    # удалось уложить все элементы кластера
                    break
            else:
                continue
            break

        # Отсеять те, что не попадают теперь по количеству элементов
        for k in list(q2boxes.keys()):
            delete = False

            new_cluster = q2boxes[k]

            # count = len(new_cluster)
            # if count not in count_range:  # см. проверки выше
            #     delete = True

            new_bbox = Box.union(*new_cluster)  # bounding box: union of group's boxes
            satisfies = self.pattern.check_constraints_for_bbox(new_bbox)
            if not satisfies:
                delete = True

            if delete:
                del q2boxes[k]

        # 3.1) Все допустимые совпадения собрать в одно множество, и выполнить для них разрешение накладок.
        #  Берём именно уникальные наборы, т.к. в разные квадранты разного размера
        #  могли попасть одинаковые наборы элементов.

        subcluster_set = {
            tuple(sorted(boxes))
            for boxes in q2boxes.values()
        }

        arrangements: list[list[list[Box]]] = find_combinations_of_compatible_elements(
            subcluster_set,
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

    def _split_to_subclusters_of_desired_count(
            self,
            connected_cluster: list[Box] | set[Box],
            item_count: open_range | None = None) -> list[list[Box]]:
        """ Find connected sub-clusters of desired count but without restriction on size
        """
        if item_count is None:
            item_count = self.pattern.item_count

        n = len(connected_cluster)

        if n in item_count:
            return [connected_cluster]

        if n < item_count:
            return []

        # [<<<<<][=====][>>>>>]
        #    x      +      ?

        min_count = item_count.start
        if min_count is None:
            min_count = 1
        max_count = item_count.stop
        # if max_count is None:
        #     max_count = n

        # Определяем размер максимально полного наложения
        # по минимальному остатку и максимальному размеру части
        _rem, basic_count = max((
            (
                # нераспределённый остаток, с понижением рейтинга при максимальном размере части и ненулевом остатке
                # (n // i — это "штраф", превышающий возможную добавку при использовании части меньшего размера):
                -(n % i + (n // i if i == max_count and n % i > 0 else 0)),
                i,  # размер части
            )
            for i in range(min_count, max_count + 1)
        ))
        remaining = -_rem
        parts = n // basic_count

        # Кол-во элементов в находимых далее областях
        desired_counts = [
            min(max_count, basic_count + (1 if i < remaining else 0))
            for i in range(parts)
        ]

        # Ищем части, состоящие из заданного количества элементов.
        # В каждую часть (под-кластер) добавляем всех ближайших соседей.

        subclusters: list[list[Box]] = []
        unused_boxes = set(connected_cluster)

        for desired_count in desired_counts:
            left_top = min(unused_boxes, key=lambda box: sum(box.position))
            spot = {left_top}
            bbox = VariBox.from_box(left_top)

            while len(spot) < desired_count:
                outer_neighbours = ({
                    neighbour
                    for member in spot
                    for neighbour in self._neighbours[member]
                } - spot) & unused_boxes

                if not outer_neighbours:
                    # Данные о соседях могли не записаться (ранее)
                    outer_neighbours = ({
                        box
                        for member in spot
                        for box in unused_boxes
                        if self.are_neighbours(member, box)
                    } - spot)

                # ... ????

                if not outer_neighbours:
                    break
                closest_neighbour = min(outer_neighbours, key=lambda b: self.calc_distance(b, bbox))

                spot.add(closest_neighbour)
                bbox.grow_to_cover(closest_neighbour)

            unused_boxes -= spot
            if len(spot) >= min_count:
                subclusters.append(list(sorted(spot)))
            # else:
            #     ...
        return subclusters
