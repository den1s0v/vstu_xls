from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from loguru import logger

import vstuxls.grammar2d.Pattern2d as pt
from vstuxls.geom2d import Box, Point, RangedBox
from vstuxls.grammar2d import Grammar
from vstuxls.grammar2d.Match2d import Match2d
from vstuxls.grid import CellView, Grid, GridView
from vstuxls.string_matching import CellClassifier

if TYPE_CHECKING:
    from grammar2d.Pattern2d import Pattern2d


# Флаг для включения отладочной печати разрешённых накладок
DEBUG_OVERLAP_RESOLUTION = False


class _WaveObserver(Protocol):
    def notify_wave_started(self, wave_index: int, patterns: Iterable[str]) -> None:
        ...

    def notify_wave_completed(self, wave_index: int, matches: Iterable[Match2d]) -> None:
        ...


@dataclass
class GrammarMatcher:
    grammar: Grammar
    wave_observer: '_WaveObserver | None' = None

    # projection of processed grid
    _grid_view: GridView = None

    # matches starting at left top corner
    _matches_by_position: dict[Point, list[Match2d]] = None

    # matches related to pattern
    _matches_by_element: dict['Pattern2d', list[Match2d]] = None

    # scalar info about cells
    type_to_cells: dict[str, list[CellView]] = None

    # кэш отфильтрованных матчей по (pattern, region, match_limit, overlap_mode, criteria)
    _filtered_matches_cache: dict = None

    def get_pattern_matches(
            self,
            pattern: 'Pattern2d',
            region: Box | RangedBox = None,
            match_limit: int = None,
            overlap_resolution: 'pt.OverlapResolutionMode | None' = None) -> list[Match2d]:
        """ Get all currently known matches of given pattern.
        If region specified, return only matches that are within the region.

        Args:
            pattern: Pattern to get matches for
            region: Optional region to filter matches
            match_limit: Optional limit on number of matches
            overlap_resolution: Mode for resolving overlapping matches. If None, uses pattern's overlap_config
        """
        # Определяем режим разрешения накладок: из параметра или из паттерна
        if overlap_resolution is None:
            overlap_resolution = pattern.get_overlap_mode_enum()

        # Попытка использовать кэш только для простого случая:
        # независимый паттерн, нет region и match_limit.
        use_cache = (
            pattern.independently_matchable()
            and region is None
            and match_limit is None
        )

        cache_key = None
        if use_cache:
            criteria = pattern.get_overlap_criteria()
            criteria_sig = tuple((c.metric.value, c.order.value) for c in criteria)
            cache_key = (pattern, overlap_resolution, criteria_sig)
            if self._filtered_matches_cache is None:
                self._filtered_matches_cache = {}
            cached = self._filtered_matches_cache.get(cache_key)
            if cached is not None:
                return cached

        if pattern.independently_matchable():
            matches = self.matches_by_element[pattern] or []

            if region:
                # filter by region
                matches = list(filter(
                    lambda m: m.box in region,
                    matches))

            if match_limit is not None and len(matches) > match_limit:
                # Drop unexpected matches.
                matches = matches[:match_limit]

            result = self._apply_overlap_resolution(matches, overlap_resolution, pattern)
            if use_cache and cache_key is not None:
                self._filtered_matches_cache[cache_key] = result
            return result
        else:
            matches = self._find_matches_of_dependent_pattern(pattern, region, match_limit)
            # Для зависимых паттернов кэш пока не используем (поведение сложнее)
            return self._apply_overlap_resolution(matches, overlap_resolution, pattern)

    def _apply_overlap_resolution(
            self,
            matches: list[Match2d],
            overlap_resolution: 'pt.OverlapResolutionMode',
            pattern: 'Pattern2d') -> list[Match2d]:
        """Применяет фильтрацию перекрывающихся матчей в соответствии с режимом."""
        if overlap_resolution == pt.OverlapResolutionMode.NONE:
            return matches
        elif overlap_resolution == pt.OverlapResolutionMode.FULL:
            return self._filter_full_overlaps(matches, pattern)
        elif overlap_resolution == pt.OverlapResolutionMode.PARTIAL:
            return self._filter_partial_overlaps(matches, pattern)
        else:
            # Неожиданный режим - логируем и возвращаем без фильтрации
            logger.warning(
                f"Unexpected overlap_resolution mode: {overlap_resolution} for pattern {pattern.name}, "
                f"returning matches without filtering"
            )
            return matches

    @staticmethod
    def _get_match_precision(match: Match2d) -> float:
        """Получить точность матча, вычисляя её если необходимо."""
        if match.precision is not None:
            return match.precision
        return match.calc_precision()

    @staticmethod
    def _compare_matches_by_criteria(
            match1: Match2d,
            match2: Match2d,
            criteria: list['pt.OverlapCriterion']) -> int:
        """Сравнить два матча по списку критериев с приоритетами.
        
        Args:
            match1: Первый матч для сравнения
            match2: Второй матч для сравнения
            criteria: Список критериев с приоритетами (метрика + max/min)
        
        Returns:
            -1 если match1 < match2 (проигрывает по критериям)
            0 если match1 == match2 (равны по всем критериям)
            1 если match1 > match2 (выигрывает по критериям)
        """
        for criterion in criteria:
            metric = criterion.metric
            mode = criterion.order

            # Получаем значения для сравнения
            value1 = GrammarMatcher._get_match_metric_value(match1, metric)
            value2 = GrammarMatcher._get_match_metric_value(match2, metric)

            if value1 is None or value2 is None:
                continue  # Пропускаем, если метрику нельзя вычислить

            # Сравниваем в зависимости от режима
            if mode == pt.OverlapOrderEnum.MAX:
                # Больше лучше
                if value1 < value2:
                    return -1
                elif value1 > value2:
                    return 1
            elif mode == pt.OverlapOrderEnum.MIN:
                # Меньше лучше
                if value1 > value2:
                    return -1
                elif value1 < value2:
                    return 1

        # Если все критерии равны
        return 0

    @staticmethod
    def _get_match_metric_value(match: Match2d, metric: 'pt.OverlapMetricEnum') -> float | None:
        """Получить значение метрики для матча.
        
        Args:
            match: Матч
            metric: Название метрики: 'area', 'width', 'height', 'precision'
        
        Returns:
            Значение метрики или None, если нельзя вычислить
        """
        if not match.box:
            # Если нет box, можем вернуть только precision
            if metric == pt.OverlapMetricEnum.PRECISION:
                return GrammarMatcher._get_match_precision(match)
            return None

        if metric == pt.OverlapMetricEnum.AREA:
            return float(match.box.w * match.box.h)
        elif metric == pt.OverlapMetricEnum.WIDTH:
            return float(match.box.w)
        elif metric == pt.OverlapMetricEnum.HEIGHT:
            return float(match.box.h)
        elif metric == pt.OverlapMetricEnum.PRECISION:
            return GrammarMatcher._get_match_precision(match)

        return None

    @staticmethod
    def _filter_full_overlaps(matches: list[Match2d], pattern: 'Pattern2d') -> list[Match2d]:
        """Фильтрует полные наложения матчей, оставляя лучшие по критериям из конфигурации паттерна.
        
        Если один Box полностью содержит другой, оставляется лучший матч
        согласно критериям из pattern.get_overlap_resolution().
        """
        if not matches:
            return matches

        # Получаем критерии из конфигурации паттерна
        criteria = pattern.get_overlap_criteria()
        criteria_str = ', '.join(f'{c.metric.value}-{c.order.value}' for c in criteria)

        # Создаём список индексов для отслеживания, какие матчи нужно удалить
        to_remove = set()
        resolved_overlaps = []  # Для отладочной печати

        for i in range(len(matches)):
            if i in to_remove:
                continue

            match1 = matches[i]
            if not match1.box:
                continue

            for j in range(i + 1, len(matches)):
                if j in to_remove:
                    continue

                match2 = matches[j]
                if not match2.box:
                    continue

                # Проверяем соответствие позиций
                if match1.box.position != match2.box.position:
                    continue

                # Проверяем полное наложение
                if match1.box in match2.box or match2.box in match1.box:
                    # Сравниваем матчи по критериям из конфигурации
                    comparison = GrammarMatcher._compare_matches_by_criteria(match1, match2, criteria)

                    if comparison < 0:
                        # match1 проигрывает, удаляем его
                        to_remove.add(i)
                        if DEBUG_OVERLAP_RESOLUTION:
                            resolved_overlaps.append({
                                'mode': 'FULL',
                                'pattern': pattern.name,
                                'removed': {
                                    'name': match1.pattern.name,
                                    'box': f"({match1.box.left},{match1.box.top}) {match1.box.w}x{match1.box.h}",
                                    'precision': GrammarMatcher._get_match_precision(match1)
                                },
                                'kept': {
                                    'name': match2.pattern.name,
                                    'box': f"({match2.box.left},{match2.box.top}) {match2.box.w}x{match2.box.h}",
                                    'precision': GrammarMatcher._get_match_precision(match2)
                                },
                                'criteria': criteria_str
                            })
                        break  # Переходим к следующему match1
                    elif comparison > 0:
                        # match2 проигрывает, удаляем его
                        to_remove.add(j)
                        if DEBUG_OVERLAP_RESOLUTION:
                            resolved_overlaps.append({
                                'mode': 'FULL',
                                'pattern': pattern.name,
                                'removed': {
                                    'name': match2.pattern.name,
                                    'box': f"({match2.box.left},{match2.box.top}) {match2.box.w}x{match2.box.h}",
                                    'precision': GrammarMatcher._get_match_precision(match2)
                                },
                                'kept': {
                                    'name': match1.pattern.name,
                                    'box': f"({match1.box.left},{match1.box.top}) {match1.box.w}x{match1.box.h}",
                                    'precision': GrammarMatcher._get_match_precision(match1)
                                },
                                'criteria': criteria_str
                            })
                    # Если равны, оставляем оба (не добавляем в to_remove)

        # Отладочная печать разрешённых накладок
        if DEBUG_OVERLAP_RESOLUTION and resolved_overlaps:
            logger.debug(f"Resolved {len(resolved_overlaps)} FULL overlap(s) for pattern '{pattern.name}':")
            for overlap in resolved_overlaps:
                logger.debug(
                    f"  [{overlap['mode']}] Removed: {overlap['removed']['name']} "
                    f"at {overlap['removed']['box']} (precision={overlap['removed']['precision']:.3f}), "
                    f"kept: {overlap['kept']['name']} at {overlap['kept']['box']} "
                    f"(precision={overlap['kept']['precision']:.3f}), "
                    f"criteria: {overlap['criteria']}"
                )

        # Возвращаем матчи, которые не были помечены для удаления
        return [match for idx, match in enumerate(matches) if idx not in to_remove]

    @staticmethod
    def _filter_partial_overlaps(matches: list[Match2d], pattern: 'Pattern2d') -> list[Match2d]:
        """Фильтрует частичные наложения матчей, оставляя лучшие по критериям из конфигурации паттерна.
        
        Сначала исчерпывающе разрешаются все полные перекрытия, затем обрабатываются
        оставшиеся частичные перекрытия.
        """
        if not matches:
            return matches

        # Шаг 1: Сначала исчерпывающе разрешаем все полные перекрытия
        matches = GrammarMatcher._filter_full_overlaps(matches, pattern)

        if not matches:
            return matches

        # Шаг 2: Теперь обрабатываем частичные перекрытия среди оставшихся матчей
        # Получаем критерии из конфигурации паттерна
        criteria = pattern.get_overlap_criteria()
        criteria_str = ', '.join(f'{c.metric.value}-{c.order.value}' for c in criteria) if DEBUG_OVERLAP_RESOLUTION else None

        # Создаём список индексов для отслеживания, какие матчи нужно удалить
        to_remove = set()
        resolved_overlaps = [] if DEBUG_OVERLAP_RESOLUTION else None  # Для отладочной печати

        for i in range(len(matches)):
            if i in to_remove:
                continue

            match1 = matches[i]
            if not match1.box:
                continue

            for j in range(i + 1, len(matches)):
                if j in to_remove:
                    continue

                match2 = matches[j]
                if not match2.box:
                    continue

                # Проверяем частичное перекрытие (но не полное, так как полные уже обработаны)
                if match1.box.manhattan_distance_to_overlap(match2.box) == 0:
                    # Убеждаемся, что это именно частичное, а не полное наложение
                    if match1.box in match2.box or match2.box in match1.box:
                        continue  # Полные наложения уже обработаны на шаге 1

                    # Сравниваем матчи по критериям из конфигурации
                    comparison = GrammarMatcher._compare_matches_by_criteria(match1, match2, criteria)

                    if comparison < 0:
                        # match1 проигрывает, удаляем его
                        to_remove.add(i)
                        if DEBUG_OVERLAP_RESOLUTION:
                            resolved_overlaps.append({
                                'mode': 'PARTIAL',
                                'pattern': pattern.name,
                                'removed': {
                                    'name': match1.pattern.name,
                                    'box': f"({match1.box.left},{match1.box.top}) {match1.box.w}x{match1.box.h}",
                                    'precision': GrammarMatcher._get_match_precision(match1)
                                },
                                'kept': {
                                    'name': match2.pattern.name,
                                    'box': f"({match2.box.left},{match2.box.top}) {match2.box.w}x{match2.box.h}",
                                    'precision': GrammarMatcher._get_match_precision(match2)
                                },
                                'criteria': criteria_str
                            })
                        break  # Переходим к следующему match1
                    elif comparison > 0:
                        # match2 проигрывает, удаляем его
                        to_remove.add(j)
                        if DEBUG_OVERLAP_RESOLUTION:
                            resolved_overlaps.append({
                                'mode': 'PARTIAL',
                                'pattern': pattern.name,
                                'removed': {
                                    'name': match2.pattern.name,
                                    'box': f"({match2.box.left},{match2.box.top}) {match2.box.w}x{match2.box.h}",
                                    'precision': GrammarMatcher._get_match_precision(match2)
                                },
                                'kept': {
                                    'name': match1.pattern.name,
                                    'box': f"({match1.box.left},{match1.box.top}) {match1.box.w}x{match1.box.h}",
                                    'precision': GrammarMatcher._get_match_precision(match1)
                                },
                                'criteria': criteria_str
                            })
                    # Если равны, оставляем оба (не добавляем в to_remove)

        # Отладочная печать разрешённых частичных накладок
        if DEBUG_OVERLAP_RESOLUTION and resolved_overlaps:
            logger.debug(f"Resolved {len(resolved_overlaps)} PARTIAL overlap(s) for pattern '{pattern.name}':")
            for overlap in resolved_overlaps:
                logger.debug(
                    f"  [{overlap['mode']}] Removed: {overlap['removed']['name']} "
                    f"at {overlap['removed']['box']} (precision={overlap['removed']['precision']:.3f}), "
                    f"kept: {overlap['kept']['name']} at {overlap['kept']['box']} "
                    f"(precision={overlap['kept']['precision']:.3f}), "
                    f"criteria: {overlap['criteria']}"
                )

        # Возвращаем матчи, которые не были помечены для удаления
        return [match for idx, match in enumerate(matches) if idx not in to_remove]

    def run_match(self, grid: Grid) -> list[Match2d]:
        """
        Run matching of all patterns in the grammar on the given grid.
        Returns list of matches for the root pattern.
        "Центральный метод" всего парсера.
        :param grid: Grid to match on
        :return: List of matches for the root pattern
        """
        self.matches_by_element.clear()
        # сбрасываем кэш отфильтрованных матчей
        self._filtered_matches_cache = {}
        self._grid_view = grid.get_view()
        self._recognise_all_cells_content()
        self._roll_matching_waves()

        root = self.grammar.root
        # assert root in self._matches_by_element, set(self._matches_by_element.keys())
        root_matches = self._matches_by_element.get(root) or []
        return root_matches

    @property
    def matches_by_position(self) -> dict[Point, list[Match2d]]:
        if not self._matches_by_position:
            self._matches_by_position = defaultdict(list)
        return self._matches_by_position

    @property
    def matches_by_element(self) -> dict['Pattern2d', list[Match2d]]:
        if not self._matches_by_element:
            self._matches_by_element = defaultdict(list)
        return self._matches_by_element

    def _resolve_patterns(self, patterns: 'str | Pattern2d | list[str] | list[Pattern2d]') -> list['Pattern2d']:
        """Преобразует идентификаторы паттернов в объекты `Pattern2d` текущей грамматики."""
        if not patterns:
            raise ValueError('Pattern name or list of pattern names must be provided.')

        if not isinstance(patterns, (list, tuple, set)):
            patterns = [patterns]

        resolved: list[Pattern2d] = []
        for item in patterns:
            if isinstance(item, pt.Pattern2d):
                resolved.append(item)
            elif isinstance(item, str):
                try:
                    resolved.append(self.grammar[item])
                except KeyError as exc:
                    raise KeyError(f'Pattern `{item}` not found in grammar.') from exc
            else:
                raise TypeError(f'Unsupported pattern identifier type: {type(item)!r}')

        return resolved

    def register_match(self, match: Match2d, as_pattern: 'str|Pattern2d' = None, _seen_patterns: set = None):
        self.matches_by_position[match.box.position].append(match)
        self.matches_by_element[match.pattern].append(match)

        # add patterns extended by this too!
        # for base_pattern in self.grammar.extension_map.get(match.pattern) or ():
        for base_pattern in match.pattern.extends_patterns(recursive=True):
            self.matches_by_element[base_pattern].append(match)
            # ## print(f' + Registered match for {base_pattern} extended by {match.pattern}')

    def _recognise_all_cells_content(self, max_hypotheses_per_cell=5):

        ccl = CellClassifier(self.grammar.get_effective_cell_types().values())
        self.type_to_cells = defaultdict(list)

        for cw in self._grid_view.iterate_cells():
            match_list = ccl.match(cw.cell.content, max_hypotheses_per_cell)
            if match_list:
                for m in match_list:
                    # save to local cache
                    ct_name = m.pattern.content_class.name
                    self.type_to_cells[ct_name].append(cw)

            # save to cell_view's data
            data = cw.data  # reference to updatable dict
            # if 'cell_matches' not in data:
            #     data['cell_matches'] = dict()
            data['cell_matches'] = {
                m.pattern.content_class.name: m
                for m in match_list
            }

    def _roll_matching_waves(self, verbose=True):
        """ Find matches of all grammar elements per all matching waves defined by grammar,
            from terminals to the root. """
        for wave_index, wave in enumerate(self.grammar.dependency_waves()):
            pattern_names = [p.name for p in wave]
            self._notify_wave_started(wave_index, pattern_names)

            if verbose:
                logger.debug('WAVE:')
                logger.debug(pattern_names)

            processed_patterns: list[Pattern2d] = []

            if self.grammar.target_mode == 'root' and self.grammar.root in wave:
                self._find_matches_of_pattern(self.grammar.root)
                processed_patterns.append(self.grammar.root)
            else:
                for ptt in wave:
                    if ptt.independently_matchable():
                        self._find_matches_of_pattern(ptt)
                        processed_patterns.append(ptt)
            ...
            self._notify_wave_completed(wave_index, processed_patterns)

    def _find_matches_of_pattern(self, pattern: 'Pattern2d'):
        """Try finding matches of element on all grid space"""
        matcher = pattern.get_matcher(self)
        matches = matcher.find_all(match_limit=pattern.count_in_document.stop)

        # Check the quantity of matches
        if len(matches) not in pattern.count_in_document:
            logger.warning(f'Found {len(matches)} match(es) of pattern `{pattern.name
                }` but expected {pattern.count_in_document}.')

            if pattern.count_in_document.stop is not None and len(matches) > pattern.count_in_document.stop:
                limit = pattern.count_in_document.stop
                # Drop unexpected matches.
                matches = matches[:limit]
                logger.warning(f' ... limited result to {limit} match(es) of this pattern.')

        for m in matches or ():
            # register Match globally
            self.register_match(m)

        ###
        logger.debug('')
        logger.info(f':: {len(matches)} matches of pattern `{pattern.name}`')
        # for m in matches:
        #     logger.debug([m.box, m.get_content(), m.get_children()])
        # ...
        # return?

    def _find_matches_of_dependent_pattern(
            self,
            pattern: 'Pattern2d',
            region: Box | RangedBox = None,
            match_limit: int = None) -> list[Match2d]:
        """Try finding matches of element within the specified grid region"""
        if (match_limit is None
                or (pattern.count_in_document.stop is not None
                and match_limit > pattern.count_in_document.stop)):
            match_limit = pattern.count_in_document.stop

        # Проверить наличие в кэше
        matches = []
        cache_key = 'matched_within_regions'
        occurrences = self.matches_by_element[pattern] or ()
        for m in occurrences:
            # Проверить, что этот матч вообще попадает в желаемую область.
            if region and m.box not in region:
                continue

            # We can use a match only if we known that we'll get complete set of matches.
            # Мы можем взять матч, только если точно знаем,
            # что после этого перебора получим исчерпывающий набор совпадений, —
            # для этого матч должен происходить из совместимой с нами области:
            # тогда мы переберём все матчи этой области.
            if cache_key in m.data:
                matched_within_regions: set[Box] = m.data[cache_key]
                if not region or region in matched_within_regions:
                    # cache hit.
                    matches.append(m)
                else:
                    # still try to find indirect matches
                    for ch_m in matched_within_regions:
                        if ch_m and region in ch_m:
                            # Желаемый регион внутри ранее найденного.
                            # Прямая выборка из него в общем случае может быть неоптимальной
                            # (при сдвиге начала по "чётности", например).
                            matches.append(m)
                            break

        if matches:
            # Нашли в кэше.
            # Так как этот набор матчей может быть неоптимальным, но и найти его заново недолго,
            # то не сохраняем (вторично) в кэше.
            return matches

        # Обычный процесс поиска ...

        matcher = pattern.get_matcher(self)
        matches = matcher.find_all(
            region=region,
            match_limit=match_limit,
        )

        # Check the quantity of matches ...
        # Do not check the count over all document.

        if match_limit is not None and len(matches) > match_limit:
            # Drop unexpected matches.
            matches = matches[:match_limit]
            logger.warning(f' ... limited result to {match_limit} match(es) of this pattern.')

        for m in matches:
            # 1)
            # Set metadata about the region requested...
            if cache_key not in m.data:
                matched_within_regions = m.data[cache_key] = set()
            else:
                matched_within_regions = m.data[cache_key]
            # Add to cache.
            matched_within_regions.add(region)

            # 2)
            # register Match globally
            self.register_match(m)
        ###
        # logger.debug('')
        # logger.debug(f':: {len(matches)} matches of DEPENDENT pattern `{pattern.name}` ↓')
        # for m in matches:
        #     logger.debug([m.box, m.get_content()])
        ###
        return matches

    def find_unused_pattern_matches(
            self,
            document_match: Match2d,
            patterns: 'str | Pattern2d | list[str] | list[Pattern2d]',
    ) -> list[Match2d]:
        """Возвращает список совпадений паттернов, не использованных в документе."""
        if not document_match:
            raise ValueError('Document match must be provided.')

        resolved_patterns = self._resolve_patterns(patterns)
        if not resolved_patterns:
            return []

        used_ids = self._collect_match_ids(document_match)
        unused_matches: list[Match2d] = []
        seen_match_ids: set[int] = set()

        for pattern in resolved_patterns:
            for match in self.get_pattern_matches(pattern) or ():
                match_id = id(match)
                if match_id in used_ids:
                    continue
                if match_id in seen_match_ids:
                    continue
                seen_match_ids.add(match_id)
                unused_matches.append(match)

        return unused_matches

    @staticmethod
    def _collect_match_ids(root_match: Match2d) -> set[int]:
        """Обходит дерево матчей и возвращает множество их идентификаторов (`id`)."""
        stack = [root_match]
        visited: set[int] = set()

        while stack:
            current = stack.pop()
            match_id = id(current)
            if match_id in visited:
                continue

            visited.add(match_id)

            if current.component2match:
                stack.extend(current.component2match.values())

        return visited

    def _notify_wave_started(self, wave_index: int, pattern_names: Iterable[str]) -> None:
        if self.wave_observer:
            self.wave_observer.notify_wave_started(wave_index, pattern_names)

    def _notify_wave_completed(self, wave_index: int, patterns: Iterable['Pattern2d']) -> None:
        if not self.wave_observer:
            return

        matches: list[Match2d] = []
        for pattern in patterns:
            matches.extend(self.matches_by_element.get(pattern) or [])

        self.wave_observer.notify_wave_completed(wave_index, matches)
