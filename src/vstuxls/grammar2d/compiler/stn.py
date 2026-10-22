"""Simple Temporal Network (STN): система разностных ограничений `x_v - x_u <= w`.

Ребро `u -> v` с весом `w` означает `x_v - x_u <= w`.
Система совместна тогда и только тогда, когда в графе нет цикла отрицательного веса
(Беллман–Форд). Кратчайшие пути (Флойд–Уоршелл) дают неявные границы на любую разность.
"""

from __future__ import annotations

from dataclasses import dataclass

from vstuxls.geom2d import open_range


@dataclass(frozen=True)
class Constraint:
    """Исходное ограничение `a - b in [lo, hi]` (границы могут быть None = бесконечность)."""
    a: str
    b: str
    lo: int | None
    hi: int | None
    label: str


class STN:
    def __init__(self) -> None:
        self.nodes: dict[str, int] = {}
        self.constraints: list[Constraint] = []
        # (u, v) -> (w, label): самое жёсткое ограничение на ребро
        self._edges: dict[tuple[str, str], tuple[int, str]] = {}

    # ------------------------------------------------------------------ построение
    def node(self, name: str) -> None:
        self.nodes.setdefault(name, len(self.nodes))

    def add_diff(self, a: str, b: str, rng: open_range | None, label: str) -> None:
        """Добавить `a - b in rng`."""
        if rng is None:
            return
        self.add_bounds(a, b, rng.start, rng.stop, label)

    def add_bounds(self, a: str, b: str, lo: int | None, hi: int | None, label: str) -> None:
        self.node(a)
        self.node(b)
        self.constraints.append(Constraint(a, b, lo, hi, label))
        if hi is not None:
            self._put(b, a, hi, label)  # a - b <= hi
        if lo is not None:
            self._put(a, b, -lo, label)  # b - a <= -lo

    def _put(self, u: str, v: str, w: int, label: str) -> None:
        cur = self._edges.get((u, v))
        if cur is None or w < cur[0]:
            self._edges[(u, v)] = (w, label)

    def copy(self) -> 'STN':
        c = STN()
        c.nodes = dict(self.nodes)
        c.constraints = list(self.constraints)
        c._edges = dict(self._edges)
        return c

    def extended(self, constraints: list[Constraint]) -> 'STN':
        c = self.copy()
        for k in constraints:
            c.add_bounds(k.a, k.b, k.lo, k.hi, k.label)
        return c

    # ------------------------------------------------------------------ совместность
    def find_negative_cycle(self) -> list[tuple[str, str, int, str]] | None:
        """Вернуть отрицательный цикл как список рёбер `(u, v, w, label)` либо None, если система совместна."""
        names = list(self.nodes)
        n = len(names)
        if n == 0:
            return None
        dist = {x: 0 for x in names}  # виртуальный источник со всеми нулевыми рёбрами
        pred: dict[str, str | None] = {x: None for x in names}
        edges = [(u, v, w) for (u, v), (w, _) in self._edges.items()]
        last = None
        for _ in range(n + 1):
            last = None
            for u, v, w in edges:
                if dist[u] + w < dist[v]:
                    dist[v] = dist[u] + w
                    pred[v] = u
                    last = v
            if last is None:
                return None
        # есть цикл: уходим назад n шагов, чтобы гарантированно оказаться на цикле
        x = last
        for _ in range(n):
            x = pred[x]  # type: ignore[index]
        cycle_nodes = [x]
        y = pred[x]
        while y != x:
            cycle_nodes.append(y)
            y = pred[y]  # type: ignore[index]
        cycle_nodes.reverse()  # теперь порядок вдоль направления рёбер
        out: list[tuple[str, str, int, str]] = []
        for i, u in enumerate(cycle_nodes):
            v = cycle_nodes[(i + 1) % len(cycle_nodes)]
            w, label = self._edges[(u, v)]
            out.append((u, v, w, label))
        return out

    def is_consistent(self) -> bool:
        return self.find_negative_cycle() is None

    # ------------------------------------------------------------------ замыкание
    def closure(self) -> dict[tuple[str, str], int]:
        """Кратчайшие пути (только для совместной сети): `d[(u, v)]` = верхняя граница `x_v - x_u`."""
        INF = float('inf')
        names = list(self.nodes)
        d: dict[tuple[str, str], float] = {(u, v): (0 if u == v else INF) for u in names for v in names}
        for (u, v), (w, _) in self._edges.items():
            if w < d[(u, v)]:
                d[(u, v)] = w
        for k in names:
            for i in names:
                dik = d[(i, k)]
                if dik == INF:
                    continue
                for j in names:
                    nd = dik + d[(k, j)]
                    if nd < d[(i, j)]:
                        d[(i, j)] = nd
        return {k: int(v) for k, v in d.items() if v != INF}

    @staticmethod
    def implied(closure: dict[tuple[str, str], int], a: str, b: str) -> open_range:
        """Неявный диапазон `a - b` по замыканию."""
        hi = closure.get((b, a))  # a - b <= d(b -> a)
        lo_neg = closure.get((a, b))  # b - a <= d(a -> b)  =>  a - b >= -d
        lo = -lo_neg if lo_neg is not None else None
        if lo is not None and hi is not None and lo > hi:
            return open_range(hi, hi)
        return open_range(lo, hi)

    # ------------------------------------------------------------------ избыточность
    def redundant_constraints(self, only: set[int] | None = None) -> list[tuple[int, str]]:
        """Индексы ограничений, выводимых из остальных.

        Ограничение `a - b in [lo, hi]` избыточно, если каждая его *существующая* граница выводится
        из других ограничений (путь без прямых рёбер этого ограничения). Возвращает `(idx, пояснение)`.
        """
        out: list[tuple[int, str]] = []
        for idx, k in enumerate(self.constraints):
            if only is not None and idx not in only:
                continue
            others = STN()
            for j, kk in enumerate(self.constraints):
                if j != idx:
                    others.add_bounds(kk.a, kk.b, kk.lo, kk.hi, kk.label)
            others.node(k.a)
            others.node(k.b)
            if not others.is_consistent():
                continue
            cl = others.closure()
            ok = True
            if k.hi is not None:
                got = cl.get((k.b, k.a))
                ok &= got is not None and got <= k.hi
            if k.lo is not None:
                got = cl.get((k.a, k.b))
                ok &= got is not None and -got >= k.lo
            if ok and (k.hi is not None or k.lo is not None):
                out.append((idx, 'выводится из остальных ограничений'))
        return out


def describe_cycle(cycle: list[tuple[str, str, int, str]]) -> str:
    """Человекочитаемое объяснение отрицательного цикла (свидетель противоречия)."""
    parts = []
    total = 0
    for u, v, w, label in cycle:
        total += w
        parts.append(f'{v} - {u} <= {w}  ({label})')
    return '; '.join(parts) + f';  сумма = {total} < 0'
