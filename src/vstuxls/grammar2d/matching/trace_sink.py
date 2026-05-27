from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from vstuxls.geom2d import Box, Point, RangedBox


@runtime_checkable
class MatchTraceSink(Protocol):
    """Optional structured tracing for matcher decisions.

    Designed to be extremely cheap when disabled (sink is None).
    """

    def reject(
        self,
        *,
        pattern_name: str,
        phase: str,
        reason: str,
        region: Box | RangedBox | None = None,
        detail: dict[str, Any] | None = None,
    ) -> None: ...

    def accept(
        self,
        *,
        pattern_name: str,
        phase: str,
        region: Box | RangedBox | None = None,
        box: Box | None = None,
        precision: float | None = None,
        detail: dict[str, Any] | None = None,
    ) -> None: ...


@dataclass(slots=True)
class InMemoryMatchTraceSink:
    """Simple sink for tests/debug runs."""

    events: list[dict[str, Any]]

    def reject(
        self,
        *,
        pattern_name: str,
        phase: str,
        reason: str,
        region: Box | RangedBox | None = None,
        detail: dict[str, Any] | None = None,
    ) -> None:
        self.events.append(
            {
                "kind": "reject",
                "pattern": pattern_name,
                "phase": phase,
                "reason": reason,
                "region": _box_to_json(region),
                "detail": detail or {},
            }
        )

    def accept(
        self,
        *,
        pattern_name: str,
        phase: str,
        region: Box | RangedBox | None = None,
        box: Box | None = None,
        precision: float | None = None,
        detail: dict[str, Any] | None = None,
    ) -> None:
        self.events.append(
            {
                "kind": "accept",
                "pattern": pattern_name,
                "phase": phase,
                "region": _box_to_json(region),
                "box": _box_to_json(box),
                "precision": precision,
                "detail": detail or {},
            }
        )


def _box_to_json(b: Box | RangedBox | None) -> dict[str, Any] | None:
    if b is None:
        return None
    if isinstance(b, RangedBox):
        # Keep it readable and stable for debugging.
        return {"type": "RangedBox", "repr": repr(b)}
    return {
        "type": "Box",
        "left": b.left,
        "top": b.top,
        "right": b.right,
        "bottom": b.bottom,
        "width": b.w,
        "height": b.h,
    }


@dataclass(slots=True)
class FilteringLimitingMatchTraceSink:
    """A wrapper sink that applies pattern filters and event caps.

    - If `patterns_allowlist` is set, only those patterns are recorded.
    - If `max_events` is set, stops recording after the cap is reached.
    - If `max_events_per_pattern` is set, caps each pattern independently.
    """

    inner: MatchTraceSink
    patterns_allowlist: set[str] | None = None
    max_events: int | None = None
    max_events_per_pattern: int | None = None

    _total: int = 0
    _per_pattern: dict[str, int] = None  # late init

    def _allowed(self, pattern_name: str) -> bool:
        if self.patterns_allowlist is not None and pattern_name not in self.patterns_allowlist:
            return False
        if self.max_events is not None and self._total >= self.max_events:
            return False
        if self.max_events_per_pattern is not None:
            if self._per_pattern is None:
                self._per_pattern = {}
            if self._per_pattern.get(pattern_name, 0) >= self.max_events_per_pattern:
                return False
        return True

    def _bump(self, pattern_name: str) -> None:
        self._total += 1
        if self.max_events_per_pattern is not None:
            if self._per_pattern is None:
                self._per_pattern = {}
            self._per_pattern[pattern_name] = self._per_pattern.get(pattern_name, 0) + 1

    def reject(
        self,
        *,
        pattern_name: str,
        phase: str,
        reason: str,
        region: Box | RangedBox | None = None,
        detail: dict[str, Any] | None = None,
    ) -> None:
        if not self._allowed(pattern_name):
            return
        self._bump(pattern_name)
        self.inner.reject(
            pattern_name=pattern_name,
            phase=phase,
            reason=reason,
            region=region,
            detail=detail,
        )

    def accept(
        self,
        *,
        pattern_name: str,
        phase: str,
        region: Box | RangedBox | None = None,
        box: Box | None = None,
        precision: float | None = None,
        detail: dict[str, Any] | None = None,
    ) -> None:
        if not self._allowed(pattern_name):
            return
        self._bump(pattern_name)
        self.inner.accept(
            pattern_name=pattern_name,
            phase=phase,
            region=region,
            box=box,
            precision=precision,
            detail=detail,
        )

