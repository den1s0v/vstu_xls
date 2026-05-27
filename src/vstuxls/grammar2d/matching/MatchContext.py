from __future__ import annotations

from dataclasses import dataclass, field

from vstuxls.geom2d import Box, RangedBox


@dataclass(slots=True)
class MatchContext:
    """Per-invocation mutable state for matchers.

    This object is created per `find_all(...)` call and passed through helper
    methods to avoid thread-unsafe instance state on matcher objects.
    """

    region: Box | RangedBox | None = None
    match_limit: object | None = None

    neighbours: dict[Box, set[Box]] = field(default_factory=dict)
    not_neighbours: dict[Box, set[Box]] = field(default_factory=dict)

