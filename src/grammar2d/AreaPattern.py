from dataclasses import dataclass, field
from typing import override

from geom2d import open_range, Point
import grammar2d.Grammar as ns
import grammar2d.Match2d as m2
from grammar2d.NonTerminal import NonTerminal
from grammar2d.Pattern2d import Pattern2d, PatternRegistry
from grammar2d.PatternComponent import PatternComponent
from utils import sorted_list


@PatternRegistry.register
@dataclass(kw_only=True)
class AreaPattern(NonTerminal):
    """Структура из элементов разного типа.
    
    AreaPattern включает "внутренние" компоненты
    и может включать внешние компоненты (последние не входят в область матча для AreaPattern).

    Компоненты области типа area в текущей версии грамматики
    могут задавать своё расстояние до стенок области area (в виде диапазона)
    и не могут иметь ограничений непосредственно между собой.
    Зато наборы ограничений между стенками можно задавать в произвольном составе.
    """

    components: list[PatternComponent]

    # Считаются ли незанятые области внутри структуры её частью (opaque; False),
    # или нет (transparent; True).
    # Имеет значение при обнаружении накладок между перекрывающимися совпадениями этого паттерна.
    # Если используется прозрачность (True), то допускается накладывание ограничивающих прямоугольников совпадений,
    # при условии, что не накладываются области, непосредственно занятые внутренними компонентами.
    inner_space_transparent = False

    def __hash__(self) -> int:
        return hash(self.name)

    @classmethod
    @override
    def get_kind(cls):
        return "area"  # ???

    # dependencies: list[Pattern2d] = None
    @override
    def dependencies(self, recursive=False) -> list[Pattern2d]:
        if not self._cache.dependencies:
            dependency_set = set()
            for comp in self.components:
                dependency_set |= set(comp.dependencies(recursive))
            # check circular dependencies
            assert self not in dependency_set, \
                'Grammar pattern `{self.name}` has circular dependency on itself (via component `{comp.name}`) !'
            self._cache.dependencies = list(sorted(dependency_set))
        return self._cache.dependencies

    @override
    def set_grammar(self, grammar: 'ns.Grammar'):
        super().set_grammar(grammar)
        for comp in self.components:
            comp.set_grammar(grammar)

    def get_points_occupied_by_match(self, match: 'm2.Match2d') -> list[Point]:
        """ For Area: transparent if `pattern.inner_space_transparent` is True  else opaque (the default).
        """
        if not self.inner_space_transparent:
            return super().get_points_occupied_by_match(match)

        # Взять все занятые ВНУТРЕННИМИ компонентами позиции.
        component_points = set()
        for name, comp_match in match.component2match.items():
            if self.get_component(name).inner:
                component_points |= set(comp_match.get_occupied_points())

        # Отсечь наружные части внутренних компонентов, если таковые есть (могут быть при отрицательных отступах).
        inner_points = set(match.box.iterate_points())
        return sorted_list(inner_points & component_points)

    # component_by_name: dict[str, PatternComponent] = None
    @property
    def components_by_name(self) -> dict[str, PatternComponent] | None:
        """ Returns whole component mapping as dict. """
        if not self._cache.component_by_name:
            self._cache.component_by_name = {
                comp.name: comp
                for comp in self.components
            }
        return self._cache.component_by_name

    def get_component(self, name: str = None) -> dict[str, PatternComponent] | PatternComponent | None:
        """ Returns requested component if `name` is present, otherwise returns `None`. """
        return self.components_by_name.get(name)

    @override
    def max_score(self) -> float:
        """ precision = score / max_score """
        return sum(comp.weight for comp in self.components if comp.weight > 0)

    def score_of_match(self, match: m2.Match2d) -> float:
        """ Calc score for given match:
            weighted sum of all given components
            (?) if any is absent but required?
        """
        return sum(
                comp_m.precision * self.components_by_name[name].weight
                for name, comp_m in match.component2match.items()
        )

    ...

    def get_matcher(self, grammar_matcher):
        from grammar2d.AreaPatternMatcher import AreaPatternMatcher
        return AreaPatternMatcher(self, grammar_matcher)

    def __str__(self) -> str:
        return "%s(%s)" % (type(self).__name__, repr(self.__dict__()))

    def __repr__(self) -> str:
        return str(self)

    def __dict__(self) -> dict:
        return dict(
            name=self.name,
            description=self.description,
        )
