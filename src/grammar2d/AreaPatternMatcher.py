from dataclasses import dataclass
from typing import Self

from loguru import logger
# # Профилирование ↓
# # pip install profilehooks
# from profilehooks import profile


from constraints_2d import SizeConstraint
# import grammar2d as pt
from geom2d import Box, Direction, RIGHT, DOWN, RangedBox, open_range
# from grammar2d import AreaPattern, PatternComponent
from grammar2d.AreaPattern import AreaPattern
from grammar2d.MatchRelation import MatchRelation
from grammar2d.PatternComponent import PatternComponent
from grammar2d.PatternMatcher import PatternMatcher
from grammar2d.Match2d import Match2d
import grammar2d.GrammarMatcher as ns
from grid import Region

from clash import find_combinations_of_compatible_elements
from utils import time_report


@dataclass(slots=True)
class MatchingPlan:
    component_matches_list: list[tuple[PatternComponent, list[Match2d]]]

    def get_position(self, component_i: int = 0):
        return PositionInMatchingPlan(self, component_i)

    def __getitem__(self, item):
        return self.component_matches_list[item]

    def __len__(self):
        return len(self.component_matches_list)


@dataclass(slots=True)
class PositionInMatchingPlan:
    plan: MatchingPlan
    component_i: int = 0

    # match_i: int = 0

    def clone(self) -> Self:
        return type(self)(self.plan, self.component_i)


@dataclass
class AreaPatternMatcher(PatternMatcher):
    pattern: AreaPattern
    grammar_matcher: 'ns.GrammarMatcher'
    _similar_component_pairs: list[tuple[PatternComponent, PatternComponent]] = None
    _component_relation_triples: list[tuple[PatternComponent, PatternComponent, MatchRelation]] = None
    _size_constraint: SizeConstraint = ...

    # @profile(stdout=False, filename='area-find.prof')
    def find_all(self, region: Box = None, match_limit=None) -> list[Match2d]:
        """ Find all matches within whole document.
        If a region is given, find all matches within the region.

        Все найденные совпадения существуют одновременно,
        т.е. они не пересекаются между собой и не мешают друг другу.
        """

        # Найти все матчи-кандидаты для всех паттернов-компонентов.
        with time_report('find_match_candidates_*') as ch:
            match_candidates = self.find_match_candidates_3(region)

        # Отсеять невозможные / конфликтующие варианты, при наличии.
        with time_report('filter_candidates', ch) as ch:
            matches = self.filter_candidates(match_candidates, match_limit)

        logger.debug('AreaPatternMatcher: %f s' % ch.since_start(f'AreaPatternMatcher({self.pattern.name}) completed'))

        return matches

    def _get_pattern_size_constraint(self) -> SizeConstraint | None:
        if self._size_constraint is ...:
            self._size_constraint = \
                (list(filter(lambda x: isinstance(x, SizeConstraint), self.pattern.global_constraints))
                 or
                 (None,))[0]
        return self._size_constraint

    def get_component_matches(
            self,
            component: PatternComponent,
            region: RangedBox = None,
            match_limit: int = None) -> list[Match2d]:
        """
        :param component: area's component.
        :param region: if set, limits location for matches.
        :param match_limit: -1 means to search for all matches required for this component
           in one match of parent area (usually 1).
        """
        if match_limit == -1 and component.count and component.count.stop is not None:
            match_limit = component.count.stop

        subpattern: Pattern2d = component.subpattern
        gm = self.grammar_matcher
        matches = gm.get_pattern_matches(subpattern, region, match_limit)

        # Убрать совпадения паттерна, слишком неточные для этого компонента
        matches = list(filter(
            lambda m: m.precision >= component.precision_threshold,
            matches))

        return matches

    def find_match_candidates_3(self, region: Box = None) -> list[Match2d]:
        """ Find all matches no matter if they do apply simultaneously or not.
         The patterns may be not applicable if they do overlap.

         Каждое найденное совпадение существует как бы независимо от остальных.

         Вариант с оптимизацией обхода кандидатов по близости к текущей области совпадения.
         Отсекаются далёкие варианты.
         Идея была брать x2 от минимального найденного расстояния,
          но за приемлемое время работает только с x1 (т.е. только лучшее расстояние + 1 единица длины на запас)
        """
        pattern = self.pattern

        # 1. Найти все матчи-кандидаты для всех паттернов-компонентов.
        # Включая потенциально пустые наборы матчей для опциональных компонентов.

        component_matches_list: list[tuple[PatternComponent, list[Match2d]]] = []

        for pattern_component in pattern.components:

            occurrences = self.get_component_matches(pattern_component, region=None)

            if (not occurrences
                    and not pattern_component.optional
                    and pattern_component.subpattern.independently_matchable()):
                logger.info(f'''NO MATCH: pattern `{self.pattern.name
                }` cannot have any matches since its required component `{pattern_component.name}` has no matches.''')
                return []

            component_matches_list.append((pattern_component, occurrences))

        # 2. Получить все "развёрнутые" области потенциального местонахождения родителя-area
        #    для последующего комбинирования.
        #   Записать в метаданные: match.data.parent_location[pattern]: RangedBox

        size_constraint = self._get_pattern_size_constraint()

        for pattern_component, match_list in component_matches_list:
            for component_match in match_list:
                # Получить область потенциального местонахождения родителя-area
                parent_location = pattern_component.get_ranged_box_for_parent_location(component_match)

                # Apply size constraint once here.
                if size_constraint:
                    parent_location = parent_location.restricted_by_size(*size_constraint)

                if component_match.data.parent_location is None:
                    # словарь не создан
                    component_match.data.parent_location = dict()
                # Записать в метаданные
                component_match.data.parent_location[(pattern.name, pattern_component.name)] = parent_location

        # 3. Найти комбинации из паттернов всех обязательных компонентов, дающие непустой матч для area.
        # 3.1. После обязательных, добавлять в каждый матч опциональные компоненты, попавшие в "зону влияния"
        # найденной области (он не может быть опущен, если лежит внутри области,
        # обозначенной обязательными компонентами).

        # TODO: пересмотреть описание ↓
        # Каждое действие добавления нового компонента в матч носит вероятностный и ветвящийся характер.
        #  Поэтому заводим стек для уровней/ветвей наращивания вглубь дерева принятия решений о добавлении компонентов.
        #  На листьях дерева (конец рекурсии) будут готовые, полностью заполненные матчи нашего паттерна.
        #  (?? На каждом уровне будем ограничивать ветвление лучшими вариантами, которые будут отбираться по принципу:
        #  дельта показателя к лучшему варианту добавить компонент умножается на 2 (коэффициент),
        #  это определяет порог отсечения.
        #  В случае нулевой дельты взять порог равным 1 лишней клетке. ??)
        #  По отобранным кандидатам углубляемся внутрь (рекурсия).

        # Сортировать: все опциональные в конце, сначала внутренние, по возрастанию числа матчей
        component_matches_list.sort(key=lambda t: (
            not t[0].optional,
            not t[0].inner,
            len(t[1]),  # ↑
        ))

        plan = MatchingPlan(component_matches_list)

        complete_matches: list[Match2d] = []

        # Будем считать, что компонентов ненулевое кол-во,
        # и (?) первый (после сортировки) будет обязательным (?)
        # Запросим варианты главного совпадения по всем элементам первого компонента;
        # по остальным уровням рекурсии задано максимум 1 результат.
        assert component_matches_list
        # assert not plan[0][0].optional, plan[0]
        first_comp_matches_count = len(plan[0][1])

        complete_matches = self._best_matches(
            plan.get_position(),
            None,
            first_comp_matches_count
        )

        # Получить окончательную область совпадения area для всех кандидатов (с учётом потенциальных выносов)
        for m in complete_matches:
            combined_ranged_box: RangedBox = m.data.ranged_box
            m.box = combined_ranged_box.minimal_box().to_box()
            # recalc precision
            m.calc_precision(force=True)

        return complete_matches

    def _best_matches(self,
                      plan_pos: PositionInMatchingPlan,
                      existing_match: Match2d | None = None,
                      max_results=1) -> (list)[Match2d]:
        """
        Рекурсивный поиск совпадений (матчей) базового паттерна.
        Эта функция подбирает следующий (переданный) компонент паттерна, на котором может построить матч.
        Сначала ранжируем все потенциально подходящие матчи компонента по принципу близости к текущей области совпадения
         (для равных — по точности и координате),
         и, начиная с ближайших, пробуем рекурсивно найти матч паттерна.
        Если для очередного варианта текущего компонента матч найден, то дальше не ищем и возвращаем его.

        Особенностью этой реализации является то, что existing_match может отсутствовать,
        как на начальном, так и на последующих этапах матчинга
        из-за опциональных компонентов (если они все такие).

        Returns list of 0 to `max_results` elements.
        """
        plan = plan_pos.plan
        component, match_list = plan[plan_pos.component_i]
        ### logger.debug(f'_best_matches: entered with component `{component.name}` at pos {plan_pos.component_i}, ' f'requested {max_results} max_results.')
        ###

        rb1 = existing_match.data.ranged_box if existing_match else None

        if not match_list and component.subpattern.independently_matchable():
            # Только сейчас стало возможно искать компонент,
            # когда часть компонентов уже известна и может подсказать расположение этого
            if existing_match:
                # Infer expectation for component
                region = component.get_ranged_box_for_component_location(rb1)
            else:
                region = None
            match_list = self.get_component_matches(
                component,
                region=region,
                match_limit=1,
            )

        # 1. ранжируем всех кандидатов по расположению относительно текущего матча
        # 1.1. Получить расстояние от текущей позиции
        # и записать её в каждый match компонента под ключом в виде box текущей позиции.
        # 1.2. Проранжироать и найти лучшую дельту.

        size_constraint = self._get_pattern_size_constraint()

        distance_rb_match_list: list[tuple[float, RangedBox, Match2d]] = []

        for component_match in match_list:

            # Скомбинировать области для проверки
            rb2 = component_match.data.parent_location[(self.pattern.name, component.name)]
            if not rb1:
                combined_rb = rb2
            else:
                combined_rb = rb1.combine(rb2)

                # наложить ограничения на размеры объединённой области
                if combined_rb and size_constraint:
                    combined_rb = combined_rb.restricted_by_size(*size_constraint)

                if not combined_rb:
                    continue

            if existing_match and not self._check_component_relations(existing_match, (component, component_match)):
                # не подошёл, дальше не рассматриваем
                continue

            # Расстояние до подходящего кандидата
            if existing_match:
                distance = component.calc_distance_of_match_to_box(component_match, existing_match.box)
            else:
                distance = 0  # constant, for sorting below

            distance_rb_match_list.append((distance, combined_rb, component_match))

        # Sort to have the best alternatives first.
        distance_rb_match_list.sort(key=lambda t: (
            t[0],  # distance, ↑
            -t[2].precision,  # match precision, ↓
            sum(t[2].box.position),  # coordinates sum, ↑
        ))

        # 2. вычисляем порог отсечки и фильтруем кандидатов по этой отсечке для расстояния
        min_distance = min((t[0] for t in distance_rb_match_list), default=0)

        # CUTOFF_COEF = 2.0
        CUTOFF_COEF = 1  # !!!!!!! Минимум ←
        CUTOFF_MIN_DIST = 1

        # Отсечка вдвое больше минимальной, но не меньше 1 (в случае, если минимальная равна нулю)
        cutoff_distance = max(min_distance * CUTOFF_COEF, CUTOFF_MIN_DIST)

        # Перебираем варианты и спускаем их на уровень ниже по рекурсии.

        next_level = plan_pos.component_i + 1
        next_pos = plan.get_position(next_level)
        can_recurse = next_level < len(plan)

        complete_matches: list[Match2d] = []

        for distance, combined_rb, component_match in distance_rb_match_list:

            if distance > cutoff_distance:
                # отсекаем далёкие варианты (в отсортированном списке)
                break

            # попытаться найти полный матч из текущего частичного матча
            if existing_match:
                m2 = existing_match.clone()
            else:
                m2 = Match2d(self.pattern,
                             box=None,
                             precision=0,
                             component2match={}
                             )
            m2.component2match[component.name] = component_match
            m2.recalc_box()
            # m2.precision += component_match.precision * component.weight
            m2.data.ranged_box = combined_rb

            if can_recurse:
                sub_results = self._best_matches(next_pos, m2, 1)  # TODO: 1 ??  max_max_results ??
                complete_matches.extend(sub_results)
            else:
                # Последний компонент добавлен
                complete_matches.append(m2)

            if len(complete_matches) >= max_results:
                break

        if not complete_matches and component.optional:
            # компонент опциональный, здесь его не будет
            # (он не попал в нашу область),
            # но матч остаётся.

            if not existing_match:
                existing_match = Match2d(self.pattern,
                                         box=None,
                                         precision=0,
                                         component2match={}
                                         )
            if can_recurse:
                m2 = existing_match
                sub_results = self._best_matches(next_pos, m2, 1)  # TODO: 1 ??  max_max_results ??
                complete_matches.extend(sub_results)
            else:
                # Последний компонент добавлен
                complete_matches.append(existing_match)

        ### logger.debug(f'_best_matches: ← leaving with {len(complete_matches)} results.')
        ###
        # limit & return
        return complete_matches[:max_results]

    @staticmethod
    def filter_candidates(match_candidates: list[Match2d], match_limit=None) -> list[Match2d]:
        """ Filter given matches so all returned matches do not overlap and the combination seems to be the best.

        Наилучшая раскладка выбирается из соображений количества совместимых совпадений
        и качества каждого вошедшего совпадения (фактически, максимизируется сумма precision всех совпадений).
        """

        ###
        logger.info(f'filtering candidates: {len(match_candidates)}')
        # logger.info(f'match_candidates: {(match_candidates)}')

        arrangements = find_combinations_of_compatible_elements(
            match_candidates,
            components_getter=Match2d.get_occupied_points,
            max_elements=match_limit
        )

        # Рассчитать точность (precision) для каждой комбинации-варианта,
        # получив значения точности для каждого элемента в отдельности.

        rating_length_arrangement_list = []

        # Найти наилучшую раскладку:
        #   макс. суммарная точность, затем
        #   макс. кол-во, затем
        #   лево-верхнее расположение.
        for arrangement in arrangements:
            if not arrangement:
                # empty
                continue

            rating_length_arrangement_list.append((
                arrangement,  # [0]
                sum(m.precision for m in arrangement),
                len(arrangement),
                # DESC: минимальная сумма координат:
                -min((sum(m.box.position) for m in arrangement), default=0),
            ))

        best = max(
            rating_length_arrangement_list, key=lambda t: t[1:],
            default=([],))

        return best[0]

    def _check_similar_component_pairs(self, partial_match: Match2d,
                                       new_member: tuple[PatternComponent, Match2d] = None) -> bool:
        """ Cut off matches having excessive variant of match-to-component mapping. """
        if self._similar_component_pairs is None:
            self._similar_component_pairs = self.pattern.get_similar_component_pairs()

        for k1, k2 in self._similar_component_pairs:
            if new_member:
                # Проверяем только данный компонент, ещё не записанный в матч
                if new_member[0] is k2:
                    m2 = new_member[1]
                else:
                    # пропускаем эту пару, она не про нового кандидата
                    continue
            else:
                # Просто проверяем всё содержимое матча
                m2 = partial_match.component2match.get(k2.name)

            m1 = partial_match.component2match.get(k1.name)

            if m1 and m2:
                if not (m1.box.position < m2.box.position):
                    # inappropriate ordering detected
                    return False
        # no problems found
        return True

    def _check_component_relations(
            self,
            partial_match: Match2d,
            new_member: tuple[PatternComponent, Match2d] = None) -> bool:
        """ Return False for matches having excessive variant of match-to-component mapping,
             i.e. a similar but better variant exists for this pattern. """
        if self._component_relation_triples is None:
            self._component_relation_triples = self.pattern.get_component_matches_relations()

        for k1, k2, rel in self._component_relation_triples:
            if new_member:
                # Проверяем только данный компонент, ещё не записанный в матч
                if new_member[0] is k1:
                    m1 = new_member[1]
                    m2 = partial_match.component2match.get(k2.name)
                elif new_member[0] is k2:
                    m1 = partial_match.component2match.get(k1.name)
                    m2 = new_member[1]
                else:
                    # пропускаем эту пару, она не про нового кандидата
                    continue
            else:
                # Просто проверяем всё содержимое матча
                m1 = partial_match.component2match.get(k1.name)
                m2 = partial_match.component2match.get(k2.name)

            if m1 and m2:
                # Both matches are known.
                if not rel.check(m1, m2):
                    # inappropriate overlap/ordering detected
                    return False
        # no problems found
        return True
