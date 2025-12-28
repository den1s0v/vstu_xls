from dataclasses import dataclass

from grammar2d.Pattern2d import Pattern2d
from grammar2d.Match2d import Match2d


@dataclass
class MatchContainer:
    _matches: None

    def register_match(self, match: Match2d):
        ...
    ...

