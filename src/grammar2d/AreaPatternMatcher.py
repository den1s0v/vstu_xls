from dataclasses import dataclass

from loguru import logger

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


@dataclass
class AreaPatternMatcher(PatternMatcher):
    pattern: AreaPattern
    grammar_matcher: 'ns.GrammarMatcher'
    _similar_component_pairs: list[tuple[PatternComponent, PatternComponent]] = None
    _component_relation_triples: list[tuple[PatternComponent, PatternComponent, MatchRelation]] = None
    _size_constraint: SizeConstraint = ...

    def find_all(self, _region: Region = None) -> list[Match2d]:
        """ Find all matches within whole document.

        Все найденные совпадения существуют одновременно,
        т.е. они не пересекаются между собой и не мешают друг другу.
        """

        # Найти все матчи-кандидаты для всех паттернов-компонентов.
        match_candidates = self.find_match_candidates_2(_region)

        # Отсеять невозможные / конфликтующие варианты, при наличии.
        matches = self.filter_candidates(match_candidates)

        return matches

    def match_exact_region(self, region: Region) -> list[Match2d]:
        """ Find all matches within given region. """
        return self.find_all(region)

    def find_match_candidates(self, region: Region = None) -> list[Match2d]:
        """ Find all matches no matter if they do apply simultaneously or not.
         The patterns may be not applicable if they do overlap.

         Каждое найденное совпадение существует как бы независимо от остальных.
        """

        pattern = self.pattern
        gm = self.grammar_matcher

        # 1. Найти все матчи-кандидаты для всех паттернов-компонентов.
        # Включая потенциально пустые наборы матчей для опциональных компонентов.

        # matches_by_component: dict[str, list[Match2d]] = {}
        component_matches_list: list[tuple[PatternComponent, list[Match2d]]] = []

        for pattern_component in pattern.components:
            occurrences = gm.get_pattern_matches(pattern_component.subpattern, region)

            if not occurrences and not pattern_component.optional:
                logger.info(f'''NO MATCH: pattern `{self.pattern.name
                }` cannot have any matches since its required component `{pattern_component.name}` has no matches.''')
                return []

            # Убрать совпадения паттерна, слишком неточные для этого компонента
            occurrences = list(filter(
                lambda m: m.precision >= pattern_component.precision_threshold,
                occurrences))

            component_matches_list.append((pattern_component, occurrences))

        # 2. Получить все "развёрнутые" области потенциального местонахождения родителя-area
        #    для последующего комбинирования.
        #   Записать в метаданные: match.data.parent_location[pattern]: RangedBox

        for pattern_component, match_list in component_matches_list:
            for component_match in match_list:
                # Получить область потенциального местонахождения родителя-area
                parent_location = pattern_component.get_ranged_box_for_parent_location(component_match)
                if component_match.data.parent_location is None:
                    # Если словарь не создан
                    component_match.data.parent_location = dict()
                # Записать в метаданные
                component_match.data.parent_location[pattern.name] = parent_location

        # 3. Найти комбинации из паттернов всех обязательных компонентов, дающие непустой матч для area.
        #   (для оптимальности, добавлять обязательные компоненты
        #       в порядке возрастания числа кандидатов для каждого из них, т.е. с самых малочисленных)

        # 3.1. Добавить в каждый матч опциональные компоненты, попавшие в "зону влияния" найденной области.
        # 3.2. Рассчитать точность (precision) для каждой комбинации-варианта.

        # Сортировать: все опциональные в конце, сначала внутренние, по возрастанию числа матчей
        component_matches_list.sort(key=lambda t: (
            not t[0].optional,
            not t[0].inner,
            len(t[1]),
        ))

        partial_matches: list[Match2d] = []
        size_constraint = (list(filter(lambda x: isinstance(x, SizeConstraint), pattern.global_constraints))
                           or
                           (SizeConstraint('* x *'),))[0]

        for component, match_list in component_matches_list:
            current_wave: list[Match2d] = []
            occupied_areas: set[str] = set()

            for component_match in match_list:
                if not partial_matches:
                    # Добавить чистые матчи - эти
                    m = Match2d(pattern,
                                box=component_match.box,
                                precision=component_match.precision * component.weight,
                                component2match={component.name: component_match}
                                )
                    m.data.ranged_box = component_match.data.parent_location[pattern.name]
                    current_wave.append(m)

                else:
                    # попытаться добавить текущий матч в существующие накапливаемые частичные матчи
                    rb2 = component_match.data.parent_location[pattern.name]

                    for existing_match in partial_matches:

                        rb1 = existing_match.data.ranged_box
                        combined_rb = rb1.combine(rb2)

                        # наложить ограничения на размеры области
                        combined_rb = combined_rb and combined_rb.restricted_by_size(*size_constraint)

                        if combined_rb:
                            # Ограничить число комбинаций на поле по позициям
                            combined_rb_repr = repr(combined_rb)
                            if combined_rb_repr in occupied_areas:
                                continue

                            occupied_areas.add(combined_rb_repr)

                            # it's possible to use this one together with the match.
                            m = existing_match.clone()
                            m.component2match[component.name] = component_match
                            m.precision += component_match.precision * component.weight
                            m.data.ranged_box = combined_rb

                            if self._check_similar_component_pairs(m):
                                current_wave.append(m)

                        elif component.optional:
                            # компонент опциональный, здесь его не будет (он не попал в нашу область),
                            # но матч остаётся.
                            current_wave.append(existing_match)

            partial_matches = current_wave
            if not partial_matches:
                break

            ###
            logger.info(f'partial_matches: {len(partial_matches)}')

        # Получить окончательную область совпадения area для всех кандидатов
        for m in partial_matches:
            combined_ranged_box: RangedBox = m.data.ranged_box
            m.box = combined_ranged_box.minimal_box().to_box()
            # recalc precision
            m.calc_precision(force=True)

        return partial_matches

    def find_match_candidates_2(self, region: Region = None) -> list[Match2d]:
        """ Find all matches no matter if they do apply simultaneously or not.
         The patterns may be not applicable if they do overlap.

         Каждое найденное совпадение существует как бы независимо от остальных.

         Вариант с оптимизацией обхода
        """

        pattern = self.pattern
        gm = self.grammar_matcher

        # 1. Найти все матчи-кандидаты для всех паттернов-компонентов.
        # Включая потенциально пустые наборы матчей для опциональных компонентов.

        component_matches_list: list[tuple[PatternComponent, list[Match2d]]] = []

        for pattern_component in pattern.components:
            occurrences = gm.get_pattern_matches(pattern_component.subpattern, region)

            if not occurrences and not pattern_component.optional:
                logger.info(f'''NO MATCH: pattern `{self.pattern.name
                }` cannot have any matches since its required component `{pattern_component.name}` has no matches.''')
                return []

            # Убрать совпадения паттерна, слишком неточные для этого компонента
            occurrences = list(filter(
                lambda m: m.precision >= pattern_component.precision_threshold,
                occurrences))

            component_matches_list.append((pattern_component, occurrences))

        # 2. Получить все "развёрнутые" области потенциального местонахождения родителя-area
        #    для последующего комбинирования.
        #   Записать в метаданные: match.data.parent_location[pattern]: RangedBox

        for pattern_component, match_list in component_matches_list:
            for component_match in match_list:
                # Получить область потенциального местонахождения родителя-area
                parent_location = pattern_component.get_ranged_box_for_parent_location(component_match)
                if component_match.data.parent_location is None:
                    # Если словарь не создан
                    component_match.data.parent_location = dict()
                # Записать в метаданные
                component_match.data.parent_location[(pattern.name, pattern_component.name)] = parent_location

                # ###
                # print()
                # print('component.name:', pattern_component.name)
                # print('component.constraints:', pattern_component.constraints)
                # print(' match location:', component_match.box)
                # print('parent location:', parent_location)
                # print()
                # ###

        # 3. Найти комбинации из паттернов всех обязательных компонентов, дающие непустой матч для area.
        # 3.1. После обязательных, добавлять в каждый матч опциональные компоненты, попавшие в "зону влияния"
        # найденной области (он не может быть опущен, если лежит внутри области,
        # обозначенной обязательными компонентами).
        # Каждое действие добавления нового компонента в матч носит вероятностный и ветвящийся характер.
        #  Поэтому заводим стек для уровней/ветвей наращивания вглубь дерева принятия решений о добавлении компонентов.
        #  На листьях дерева будут готовые, полностью заполненные матчи нашего паттерна.
        #  На каждом уровне будем ограничивать ветвление лучшими вариантами, которые будут отбираться по принципу:
        #  дельта показателя к лучшему варианту добавить компонент умножается на 2 (коэффициент),
        #  это определяет порог отсечения.
        #  В случае нулевой дельты взять порог равным 1 лишней клетке.
        #  По отобранным кандидатам углубляемся внутрь (рекурсия).

        # Сортировать: все опциональные в конце, сначала внутренние, по возрастанию числа матчей
        component_matches_list.sort(key=lambda t: (
            not t[0].optional,
            not t[0].inner,
            len(t[1]),
        ))

        # size_constraint = (tuple(filter(lambda x: isinstance(x, SizeConstraint), pattern.global_constraints))
        #                    or
        #                    (SizeConstraint('* x *'),))[0]

        partial_matches: list[Match2d] = []

        for component, match_list in component_matches_list:
            current_wave: list[Match2d] = []

            if not partial_matches:
                # Добавить чистые матчи - эти
                for component_match in match_list:
                    m = Match2d(pattern,
                                box=component_match.box,
                                precision=component_match.precision * component.weight,
                                component2match={component.name: component_match}
                                )
                    m.data.ranged_box = component_match.data.parent_location[(pattern.name, component.name)]
                    # m.data.distance_to
                    current_wave.append(m)
            else:
                for pm in partial_matches:
                    # попытаться нарастить текущий матч
                    grown_matches = self._grow_match(pm, component, match_list)
                    if grown_matches:
                        current_wave += grown_matches
                    elif component.optional:
                        # компонент опциональный, здесь его не будет
                        # (он не попал в нашу область),
                        # но матч остаётся.
                        current_wave.append(pm)

            partial_matches = current_wave

            ###
            logger.info(f'partial_matches: {len(partial_matches)}')
            ###

            if not partial_matches:
                break

        # Получить окончательную область совпадения area для всех кандидатов
        for m in partial_matches:
            combined_ranged_box: RangedBox = m.data.ranged_box
            m.box = combined_ranged_box.minimal_box().to_box()
            # recalc precision
            m.calc_precision(force=True)

        return partial_matches

    def _get_pattern_size_constraint(self) -> SizeConstraint | None:
        if self._size_constraint is ...:
            self._size_constraint = (list(filter(lambda x: isinstance(x, SizeConstraint), self.pattern.global_constraints))
                           or
                           (None,))[0]
        return self._size_constraint

    def _grow_match(
            self,
            existing_match: Match2d,
            component: PatternComponent,
            match_list: list[Match2d]) -> list[Match2d]:

        # 1. ранжируем всех кандидатов по расположению относительно текущего матча
        # 1.0 Отсеять неподходящие по ожидаемой области и по ограничениям размера/позиции.
        # 1.1. Получить расстояние от текущей позиции
        # и записать её в каждый match компонента под ключом в виде box текущей позиции.
        # 1.2. Проранжироать и найти лучшую дельту.

        rb1 = existing_match.data.ranged_box
        size_constraint = self._get_pattern_size_constraint()

        distance_rb_match_list: list[tuple[float, RangedBox, Match2d]] = []

        for component_match in match_list:

            # Скомбинировать области для проверки
            rb2 = component_match.data.parent_location[(self.pattern.name, component.name)]
            combined_rb = rb1.combine(rb2)

            ###
            combined_rb_back = combined_rb
            # if not combined_rb:
            #     print()
            #     print('Zero combination:')
            #     print(rb1)
            #     print(rb2)
            #     print()
            ###

            if not combined_rb: continue

            # наложить ограничения на размеры области
            if combined_rb and size_constraint:
                combined_rb = combined_rb.restricted_by_size(*size_constraint)
                ###
                # if not combined_rb:
                #     print()
                #     print('combination restricted_by_size:')
                #     print(combined_rb_back)
                #     print(rb1)
                #     print(rb2)
                #     print()
                ###

            if not combined_rb: continue

            if not self._check_component_relations(existing_match, (component, component_match)):
                # не подошёл, дальше не рассматриваем
                ###
                # if component_match not in existing_match.get_children():
                #     print()
                #     print('dropped by component_relations:')
                #     print(component.name)
                #     print(component_match.box)
                #     print({name: m.box for name, m in existing_match.component2match.items()})
                #     print()
                ###
                continue

            # Расстояние до подходящего кандидата
            distance = component.calc_distance_of_match_to_box(component_match, existing_match.box)
            distance_rb_match_list.append((distance, combined_rb, component_match))

        min_distance = min((t[0] for t in distance_rb_match_list), default=0)

        # 2. вычисляем порог отсечки и фильтруем кандидатов по этой отсечке
        # CUTOFF_COEF = 2.0
        CUTOFF_COEF = 1   # !!!!!!! Минимум ←
        CUTOFF_MIN_DIST = 1

        # Отсечка вдвое больше минимальной, но не меньше 1 (в случае, если минимальная равна нулю)
        cutoff_distance = max(min_distance * CUTOFF_COEF, CUTOFF_MIN_DIST)

        selected_match_rb_list = [
            t[1:]
            for t in distance_rb_match_list
            if t[0] <= cutoff_distance
        ]

        del distance_rb_match_list

        # попытаться добавить текущий матч в существующие накапливаемые частичные матчи

        current_wave = []
        # used_self = False

        for combined_rb, component_match in selected_match_rb_list:

            if combined_rb:
                # it's possible to use this one together with the match.
                m2 = existing_match.clone()
                m2.component2match[component.name] = component_match
                m2.precision += component_match.precision * component.weight
                m2.data.ranged_box = combined_rb

                current_wave.append(m2)

            # elif component.optional and not used_self:
            #     # компонент опциональный, здесь его не будет
            #     # (он не попал в нашу область),
            #     # но матч остаётся.
            #     current_wave.append(existing_match)
            #     used_self = True
        return current_wave


    def filter_candidates(self, match_candidates: list[Match2d]) -> list[Match2d]:
        """ Filter given matches so all returned matches do not overlap and the combination seems to be the best.

        Наилучшая раскладка выбирается из соображений количества совместимых совпадений
        и качества каждого вошедшего совпадения (фактически, максимизируется сумма precision всех совпадений).
        """

        ###
        # logger.info(f'match_candidates: {len(match_candidates)}')
        # logger.info(f'match_candidates: {(match_candidates)}')

        arrangements = find_combinations_of_compatible_elements(
            match_candidates,
            components_getter=Match2d.get_occupied_points)

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
        """ Cut off matches having excessive variant of match-to-component mapping. """
        if self._component_relation_triples is None:
            self._component_relation_triples = self.pattern.get_component_matches_relations()

        for k1, k2, rel in self._component_relation_triples:
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
                if not rel.check(m1, m2):
                    # inappropriate overlap/ordering detected
                    return False
        # no problems found
        return True
