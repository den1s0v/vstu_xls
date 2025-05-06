from dataclasses import dataclass

from loguru import logger

# import grammar2d as pt
from geom2d import Box, Direction, RIGHT, DOWN
from grammar2d import AreaPattern
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
        
        pattern = self.pattern
        gm = self.grammar_matcher

        # 1. Найти все матчи-кандидаты для всех паттернов-компонентов.
        
        matches_by_component: dict[list[Match2d]] = {}

        for k in pattern.components:
            occurrences = gm.get_pattern_matches(k.pattern, _region)

            if not occurrences and not p.optional:
                logger.info(f'NO MATCH: pattern `{self.pattern.name}` cannot have any matches since its required component {k.name} has no matches.')
                return []
            
            matches_by_component[k] = occurrences


        # 2. Получить все "развёрнутые" области потенциального местонахождения родителя-area для последующего комбинирования.

        for match_list in matches_by_component.values():
            for m in match_list:
                ...
                
        # 3. Найти комбинации из паттернов всех обязательных компонентов, дающие непустой матч для area.
        
        # 3.1. Добавить в каждый матч опциональные компоненты, попавшие в "зону влияния" найденной области.
        # 3.2. Рассчитать точность (precision) для каждой комбинации-варианта.

        
        
        # 4. Сгруппировать варианты в кластеры (матчи в кластере имеют общие компоненты). 
        # 4.1. Решить вопрос с "транзитивностью": попытаться выделить наиболее перспективную разбивку на кластеры, оставив группы вариантов только в непересекающихся областях.

        
        # 5. Проранжировать варианты в каждом кластере и сформировать лучшие совпадения.
        

        # 6. найти 
        

        # inner_components = [p for p in pattern.components if p.inner]
        # outer_components = [p for p in pattern.components if not p.inner]


        ...
        
        pass


    def match_exact_region(self, region: Region) -> list[Match2d]:
        """ Find all matches within given region. """
        return self.find_all(region)



##### TODO #####
