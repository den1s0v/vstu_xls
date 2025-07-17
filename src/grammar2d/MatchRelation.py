from dataclasses import dataclass
from operator import ne, lt, gt

from grammar2d.Match2d import Match2d


@dataclass
class MatchRelation:
    """ Стратегия сравнения позиций двух совпадений (компонентов) """

    comparison_op: type(lt) | type(ne) = ne  # ne, lt, gt

    def check(self, this: Match2d, other: Match2d) -> bool:
        return self.comparison_op(this.box.position, other.box.position)

    def check_many(self, *matches: Match2d) -> bool:
        """ Сравнивает набор совпадений предпочтительным образом: как цепочку или каждый с каждым, в зависимости от
        вида сравнения """
        return self.check_all(*matches) if self.comparison_op is ne else self.check_chain(*matches)

    def check_chain(self, *matches: Match2d) -> bool:
        """ Попарно сравнить все соседние совпадения (компонентов) в цепочке  """
        # slide with a window of 2
        return all(
            self.check(matches[i], matches[i + 1])
            for i in range(len(matches) - 1))

    def check_all(self, *matches: Match2d) -> bool:
        """ Попарно сравнить все комбинации совпадений (компонентов) """
        return all(
            self.check(matches[i], matches[j])
            for i in range(len(matches) - 1)
            for j in range(i + 1, len(matches))
        )
