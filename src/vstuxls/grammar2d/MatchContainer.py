from dataclasses import dataclass

from vstuxls.grammar2d.Match2d import Match2d


@dataclass
class MatchContainer:
    _matches: None

    def register_match(self, match: Match2d):
        ...
    ...

