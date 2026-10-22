"""Планировщик: превращает паттерн-область в план соединения (join) компонентов.

Вместо ручных «опорных линий» грамматики порядок поиска выводится из геометрии:

* из ограничений строится STN на каждую ось; его **замыкание** даёт для любого ребра ещё не найденного
  компонента допустимое окно значений при уже известных рёбрах других компонентов
  (минимальная сеть: после неё поиск не требует возвратов из-за парных ограничений);
* **порядок** компонентов выбирается жадно: сперва самый «редкий» (меньше всего кандидатов), затем тот,
  чьё окно в уже найденном контексте уже всего (оценка стоимости = min(кандидаты, площадь окна));
* кандидаты выбираются через **индекс** по рёбрам (сортированные ключи + bisect), а не полным перебором.
"""

from __future__ import annotations

from bisect import bisect_left, bisect_right
from dataclasses import dataclass, field
from typing import Iterable

from vstuxls.grammar2d.compiler.geometry import AXES, GeometryAnalyzer
from vstuxls.grammar2d.compiler.ir import ComponentIR, PatternIR, PKind
from vstuxls.grammar2d.compiler.stn import STN

EDGE_INDEX = {'left': 0, 'top': 1, 'right': 2, 'bottom': 3}
EDGES = ('left', 'top', 'right', 'bottom')
INF = float('inf')

Window = tuple[float, float]  # (lo, hi), границы включительно; ±inf — не ограничено


@dataclass
class AreaPlan:
    """Статическая часть плана области (не зависит от данных документа)."""
    pattern: PatternIR
    required: list[ComponentIR]
    optional: list[ComponentIR]
    forbidden: list[ComponentIR]
    # (ось) -> замыкание базовой сети (только обязательные)
    closures: dict[str, dict[tuple[str, str], int]]
    networks: dict[str, STN]
    # имя необязательного/запрещённого компонента -> (замыкания, сети) с ним
    extra_closures: dict[str, dict[str, dict[tuple[str, str], int]]] = field(default_factory=dict)
    extra_networks: dict[str, dict[str, STN]] = field(default_factory=dict)
    feasible: bool = True
    # результат `order_components` (заполняется при выполнении)
    order: list[ComponentIR] = field(default_factory=list)
    explain: list[str] = field(default_factory=list)


def build_area_plan(ga: GeometryAnalyzer, p: PatternIR) -> AreaPlan:
    required = [c for c in p.components if c.must_exist]
    optional = [c for c in p.components if c.optional and c.role.value != 'forbid']
    forbidden = [c for c in p.components if c.role.value == 'forbid']
    plan = AreaPlan(p, required, optional, forbidden, {}, {})
    for axis in AXES:
        stn, _ = ga.build_network(p, axis, required)
        plan.networks[axis] = stn
        if not stn.is_consistent():
            plan.feasible = False
            plan.closures[axis] = {}
            continue
        plan.closures[axis] = stn.closure()
    if not plan.feasible:
        return plan
    for c in optional + forbidden:
        plan.extra_closures[c.name] = {}
        plan.extra_networks[c.name] = {}
        for axis in AXES:
            sub, _ = ga.build_network(p, axis, required, extra=[c])
            if not sub.is_consistent():
                plan.extra_closures[c.name][axis] = None  # type: ignore[assignment]
                plan.extra_networks[c.name][axis] = sub
            else:
                plan.extra_closures[c.name][axis] = sub.closure()
                plan.extra_networks[c.name][axis] = sub
    return plan


# --------------------------------------------------------------------------- окна

def axis_of_node(node: str) -> str:
    edge = node.rsplit('.', 1)[1]
    return 'x' if edge in ('left', 'right') else 'y'


def window_for(closure: dict[tuple[str, str], int], bound: dict[str, int], node: str) -> Window:
    """Допустимое окно значений `node` при известных значениях `bound` (по замыканию STN)."""
    lo, hi = -INF, INF
    axis = axis_of_node(node)
    for u, val in bound.items():
        if axis_of_node(u) != axis:
            continue
        up = closure.get((u, node))  # x_node - x_u <= up
        if up is not None and val + up < hi:
            hi = val + up
        dn = closure.get((node, u))  # x_u - x_node <= dn  =>  x_node >= val - dn
        if dn is not None and val - dn > lo:
            lo = val - dn
    return lo, hi


def window_width(closure: dict[tuple[str, str], int], bound_nodes: Iterable[str], node: str) -> float:
    axis = axis_of_node(node)
    best = INF
    for u in bound_nodes:
        if axis_of_node(u) != axis:
            continue
        up, dn = closure.get((u, node)), closure.get((node, u))
        if up is None or dn is None:
            continue
        best = min(best, up + dn)
    return best


def order_components(plan: AreaPlan, counts: dict[str, int]) -> list[ComponentIR]:
    """Порядок обязательных компонентов для соединения (см. описание модуля)."""
    remaining = list(plan.required)
    order: list[ComponentIR] = []
    bound_nodes: list[str] = []
    notes: list[str] = []
    while remaining:
        best, best_cost = None, INF
        for c in remaining:
            n = counts.get(c.name, 0)
            if not order:
                cost = float(n)
            else:
                w_l = window_width(plan.closures['x'], bound_nodes, f'{c.name}.left')
                w_t = window_width(plan.closures['y'], bound_nodes, f'{c.name}.top')
                area = (w_l + 1) * (w_t + 1) if w_l < INF and w_t < INF else INF
                cost = min(float(n), area)
            # при равной стоимости раньше — компоненты с меньшим числом кандидатов
            key = (cost, n)
            if best is None or key < (best_cost, counts.get(best.name, 0)):
                best, best_cost = c, cost
        assert best is not None
        order.append(best)
        remaining.remove(best)
        bound_nodes += [f'{best.name}.{e}' for e in EDGES]
        notes.append(f'{best.name} (кандидатов {counts.get(best.name, 0)}, оценка {best_cost})')
    plan.order = order
    plan.explain = notes
    return order


# --------------------------------------------------------------------------- индекс кандидатов

class CandidateIndex:
    """Индекс совпадений по четырём рёбрам: сортированные ключи + списки; запрос окнами."""

    def __init__(self, matches: list) -> None:
        self.matches = matches
        self._keys: list[list[int]] = []
        self._buckets: list[dict[int, list]] = []
        for k in range(4):
            buckets: dict[int, list] = {}
            for m in matches:
                buckets.setdefault(m.box[k], []).append(m)
            self._buckets.append(buckets)
            self._keys.append(sorted(buckets))

    def query(self, windows: tuple[Window, Window, Window, Window]):
        """Совпадения, все четыре ребра которых попадают в окна `(left, top, right, bottom)`."""
        # выбираем самое узкое окно как первичное
        best_k, best_w = -1, INF
        for k in range(4):
            lo, hi = windows[k]
            width = hi - lo
            if width < best_w:
                best_k, best_w = k, width
        if best_k < 0 or best_w == INF:
            source: Iterable = self.matches
        else:
            lo, hi = windows[best_k]
            keys = self._keys[best_k]
            i = bisect_left(keys, lo)
            j = bisect_right(keys, hi)
            buckets = self._buckets[best_k]
            source = (m for key in keys[i:j] for m in buckets[key])
        for m in source:
            b = m.box
            if (windows[0][0] <= b[0] <= windows[0][1] and windows[1][0] <= b[1] <= windows[1][1]
                    and windows[2][0] <= b[2] <= windows[2][1] and windows[3][0] <= b[3] <= windows[3][1]):
                yield m


def plan_summary(plan: AreaPlan) -> str:
    """Читаемое описание плана — для отладки и отчёта `explain`."""
    kind = 'область' if plan.pattern.kind is PKind.AREA else plan.pattern.kind.value
    lines = [f'План `{plan.pattern.name}` ({kind}): ' + ('допустим' if plan.feasible else 'НЕДОПУСТИМ (противоречия)')]
    if plan.order:
        lines.append('  порядок соединения: ' + ' -> '.join(plan.explain))
    if plan.optional:
        lines.append('  необязательные: ' + ', '.join(c.name for c in plan.optional))
    if plan.forbidden:
        lines.append('  запрещённые: ' + ', '.join(c.name for c in plan.forbidden))
    return '\n'.join(lines)
