from constraints_2d import SpatialConstraint
from grammar2d import NonTerminal, PatternComponent
from grammar2d.PatternMatcher import PatternMatcher
from grammar2d.Match2d import Match2d, filter_best_matches
from grid import Region


class NonTerminalMatcher(PatternMatcher):
    """
        ???
    """
    pattern: NonTerminal

    # _match_tree: list[list[Match2d]] = None

    def find_all(self, precision_ratio_cutoff=0.9) -> list[Match2d]:
        """ NonTerminal (general pattern) is not supposed to be matched itself
        but rather group its extensions under the same name. """
        return []

    def match_exact_region(self, region: Region) -> list[Match2d]:
        return []
