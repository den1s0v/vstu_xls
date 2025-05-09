from dataclasses import dataclass

from loguru import logger

# import grammar2d as pt
from geom2d import Box, Direction, RIGHT, DOWN
# from grammar2d import AreaPattern, PatternComponent
from grammar2d.AreaPattern import AreaPattern
from grammar2d.PatternComponent import PatternComponent
from grammar2d.PatternMatcher import PatternMatcher
from grammar2d.Match2d import Match2d
import grammar2d.GrammarMatcher as ns
from grid import Region


@dataclass
class AreaPatternMatcher(PatternMatcher):

    pattern: AreaPattern
    grammar_matcher: 'ns.GrammarMatcher'

    def find_all(self, _region: Region = None) -> list[Match2d]:
        """ Find all matches within whole document. """

        # Найти все матчи-кандидаты для всех паттернов-компонентов.
        match_candidates = self.find_match_candidates(_region)

        # Отсеять невозможные / конфликтующие варианты, при наличии.
        matches = self.filter_candidates(match_candidates)

        return matches


    def match_exact_region(self, region: Region) -> list[Match2d]:
        """ Find all matches within given region. """
        return self.find_all(region)


    def find_match_candidates(self, region: Region = None) -> list[Match2d]:
        """ Find all matches no matter if they do apply simultaneously or not.
         The patterns may be not applicable if they do overlap. """

        pattern = self.pattern
        gm = self.grammar_matcher

        # 1. Найти все матчи-кандидаты для всех паттернов-компонентов.

        matches_by_component: dict[PatternComponent, list[Match2d]] = {}

        for k in pattern.components:
            occurrences = gm.get_pattern_matches(k.subpattern, region)

            if not occurrences and not k.optional:
                logger.info(f'NO MATCH: pattern `{self.pattern.name
                }` cannot have any matches since its required component {k.name} has no matches.')
                return []

            matches_by_component[k] = occurrences


        # 2. Получить все "развёрнутые" области потенциального местонахождения родителя-area
        #    для последующего комбинирования.

        for match_list in matches_by_component.values():
            for m in match_list:
                ...

        # 3. Найти комбинации из паттернов всех обязательных компонентов, дающие непустой матч для area.
        #   (для оптимальности, добавлять обязательные компоненты
        #       в порядке возрастанию числа кандидатов для каждого из них)

        # 3.1. Добавить в каждый матч опциональные компоненты, попавшие в "зону влияния" найденной области.
        # 3.2. Рассчитать точность (precision) для каждой комбинации-варианта.

        ...  # TODO

        # inner_components = [p for p in pattern.components if p.inner]
        # outer_components = [p for p in pattern.components if not p.inner]

        return []

    def filter_candidates(self, match_candidates: list[Match2d]) -> list[Match2d]:
        """ Filter given matches so all returned matches do not overlap and the combination seems to be the best. """
        """
        Общий алгоритм решения:
        1. Найти перекрывающиеся конфликтующие пары совпадений.
        2. Найти кластеры конфликтующих совпадений.
        3. Для каждого кластера:
            3.1 Найти раскладки без конфликтов.
            3.2. Проранжировать раскладки и выбрать лучшую.
        4. Объединить раскладки всех кластеров в общее совпадение и вернуть его.
        """

        # (предыдущие неточные идеи:
        # 0. Сгруппировать варианты в кластеры (матчи в кластере имеют общие внутренние компоненты).
        # 1. Найти все глобальные раскладки (варианты разрешить конфликты в кластерах, совместимые с соседними).
        # 2. Проранжировать варианты в каждом кластере и сформировать лучшие совпадения.
        # 3. Решить вопрос с "транзитивностью"/конфликтами: выделить наиболее перспективную разбивку на кластеры,
        #    оставив группы вариантов только в непересекающихся областях.)
        # 4. Сформировать итоговый ответ.

        ...  # TODO

        return []


##### TODO #####
