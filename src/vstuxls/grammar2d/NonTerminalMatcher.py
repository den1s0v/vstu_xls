from vstuxls.geom2d import Box
from vstuxls.grammar2d import NonTerminal
from vstuxls.grammar2d.Match2d import Match2d
from vstuxls.grammar2d.PatternMatcher import PatternMatcher


class NonTerminalMatcher(PatternMatcher):
    """
        ???
    """
    pattern: NonTerminal

    # _match_tree: list[list[Match2d]] = None

    def find_all(self, region: Box = None, match_limit=None) -> list[Match2d]:
        """ NonTerminal (general pattern) is not supposed to be matched itself
        but rather group its extensions under the same name. """
        return []
