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
        "x": b.x,
        "y": b.y,
        "w": b.w,
        "h": b.h,
        "x2": b.x2,
        "y2": b.y2,
        "position": list(b.position) if isinstance(b.position, Point) else list(b.position),
        "size": list(b.size),
    }

