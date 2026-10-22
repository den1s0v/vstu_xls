"""Геометрический анализ: location/size/gap/relations -> две STN (оси x и y) на паттерн.

Что проверяется:

* **GEO001** — противоречие (отрицательный цикл) с выводом «свидетеля»;
  для необязательных компонентов и `forbid` — предупреждение «никогда не совпадёт»;
* **GEO002** — ограничение сужается другими ограничениями (эффективный диапазон уже заявленного);
* **GEO003** — ограничение избыточно (выводится из остальных);
* **GEO004** — размер массива несовместим с размером контейнера / паттерна;
* **GEO005** — вычисленные (неявные) размеры паттерна (только в `explain`).

Анализ — *релаксация*: рамка области = объемлющий прямоугольник внутренних компонентов — не разностное
ограничение, поэтому моделируются лишь `P.lo <= C.lo`, `C.hi <= P.hi`. Противоречие релаксации — настоящее
противоречие; обратное не утверждается.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from vstuxls.geom2d import open_range
from vstuxls.grammar2d.compiler.diagnostics import DiagnosticReport, Severity
from vstuxls.grammar2d.compiler.ir import (
    ComponentIR, GrammarIR, PatternIR, PKind, Role, X_EDGES, Y_EDGES, axis_of,
)
from vstuxls.grammar2d.compiler.stn import STN, Constraint, describe_cycle

AXES = ('x', 'y')
AXIS_EDGES = {'x': X_EDGES, 'y': Y_EDGES}
ANY = open_range(1, None)  # размер по умолчанию: хотя бы одна клетка


@dataclass
class Intrinsic:
    """Неявные границы размера паттерна (в клетках) по осям."""
    w: open_range
    h: open_range

    def along(self, axis: str) -> open_range:
        return self.w if axis == 'x' else self.h


def _n(comp: str, edge: str) -> str:
    return f'{comp}.{edge}'


def _lo_edge(axis: str) -> str:
    return AXIS_EDGES[axis][0]


def _hi_edge(axis: str) -> str:
    return AXIS_EDGES[axis][1]


def _axis_range(size: tuple[open_range, open_range] | None, axis: str) -> open_range | None:
    if size is None:
        return None
    return size[0] if axis == 'x' else size[1]


class GeometryAnalyzer:
    def __init__(self, ir: GrammarIR, report: DiagnosticReport | None = None,
                 cell_size_enforced: bool = True) -> None:
        self.ir = ir
        self.cell_size_enforced = cell_size_enforced
        self.report = report if report is not None else DiagnosticReport()
        self.intrinsic: dict[str, Intrinsic] = {}
        self.networks: dict[tuple[str, str], STN] = {}
        self.explicit: dict[tuple[str, str], list[int]] = {}
        self._active: set[str] = set()

    # ------------------------------------------------------------------ верхний уровень
    def run(self) -> DiagnosticReport:
        waves, leftover = self.ir.waves()
        order = [n for w in waves for n in w] + leftover
        for name in order:
            self.analyze(self.ir[name])
        return self.report

    def analyze(self, p: PatternIR) -> Intrinsic:
        if p.name in self.intrinsic:
            return self.intrinsic[p.name]
        if p.name in self._active:  # цикл зависимостей (он диагностируется линтером)
            return Intrinsic(ANY, ANY)
        self._active.add(p.name)
        try:
            res = self._analyze_uncached(p)
        finally:
            self._active.discard(p.name)
        self.intrinsic[p.name] = res
        return res

    def _analyze_uncached(self, p: PatternIR) -> Intrinsic:
        if p.kind is PKind.CELL:
            if self.cell_size_enforced:
                res = Intrinsic(self._with_size(ANY, p, 'x', "размер ячейки"),
                                self._with_size(ANY, p, 'y', "размер ячейки"))
            else:  # режим совместимости v1: размер терминала не проверялся матчером
                res = Intrinsic(ANY, ANY)
        elif p.kind is PKind.AREA:
            res = self._analyze_area(p)
        elif p.kind.is_array:
            res = self._analyze_array(p)
        else:  # general / alt: объединение реализаций
            res = self._hull_of_choice(p.name)
        return res

    def _with_size(self, base: open_range, p: PatternIR, axis: str, what: str) -> open_range:
        declared = _axis_range(p.size, axis)
        if declared is None:
            return base
        r = base.intersect(declared)
        if r is None:
            self.report.add('GEO004', f'{what}: заявленный размер {declared} по оси {axis} несовместим '
                                      f'с вычисленным {base}', pattern=p.name, loc=p.loc)
            return declared
        return r

    # ------------------------------------------------------------------ ссылка на паттерн
    def ref_hull(self, name: str | None) -> Intrinsic:
        """Границы размера для ссылки на паттерн: объединение по реализациям (choice set)."""
        if not name or name not in self.ir:
            return Intrinsic(ANY, ANY)
        members = [m for m in self.ir.choice_set(name) if m in self.ir]
        res: list[Intrinsic] = [self.analyze(self.ir[m]) for m in members]
        if not res:
            return Intrinsic(ANY, ANY)
        w = res[0].w.union(*[r.w for r in res[1:]]) if len(res) > 1 else res[0].w
        h = res[0].h.union(*[r.h for r in res[1:]]) if len(res) > 1 else res[0].h
        return Intrinsic(w, h)

    def _hull_of_choice(self, name: str) -> Intrinsic:
        members = [m for m in self.ir.choice_set(name) if m != name]
        if not members:
            return Intrinsic(ANY, ANY)
        sub = [self.analyze(self.ir[m]) for m in members]
        w = sub[0].w.union(*[s.w for s in sub[1:]]) if len(sub) > 1 else sub[0].w
        h = sub[0].h.union(*[s.h for s in sub[1:]]) if len(sub) > 1 else sub[0].h
        return Intrinsic(w, h)

    # ------------------------------------------------------------------ массивы
    def _analyze_array(self, p: PatternIR) -> Intrinsic:
        arr = p.array
        if arr is None:
            return Intrinsic(ANY, ANY)
        item = self.ref_hull(arr.item_pattern)
        n, g = arr.item_count, arr.gap

        def along(item_r: open_range) -> open_range:
            """Размер вдоль направления массива."""
            n_lo = n.start if n.start is not None else 0
            g_lo = g.start if g.start is not None else 0
            lo = max(1, (item_r.start or 1) * n_lo + max(n_lo - 1, 0) * g_lo)
            if n.stop is None or item_r.stop is None or (g.stop is None and n.stop > 1):
                hi = None
            else:
                hi = item_r.stop * n.stop + max(n.stop - 1, 0) * (g.stop or 0)
            return open_range(lo, hi)

        if arr.direction == 'row':
            w, h = along(item.w), item.h
        elif arr.direction == 'column':
            w, h = item.w, along(item.h)
        else:  # auto / fill: направление не фиксировано
            w = along(item.w).union(item.w)
            h = along(item.h).union(item.h)
        # Самый общий случай (выравнивание «none») поперёк оси размер не ограничивает сверху лишь формально —
        # остаёмся при объединении.
        w2 = self._with_size(w, p, 'x', 'размер массива')
        h2 = self._with_size(h, p, 'y', 'размер массива')
        return Intrinsic(w2, h2)

    # ------------------------------------------------------------------ области (STN)
    def build_network(self, p: PatternIR, axis: str, comps: Iterable[ComponentIR],
                      extra: list[ComponentIR] | None = None) -> tuple[STN, list[int]]:
        """Построить STN оси `axis` для `p` с компонентами `comps`.

        Возвращает сеть и индексы ограничений, заданных пользователем явно (для GEO002/GEO003).
        """
        stn = STN()
        explicit: list[int] = []
        lo, hi = _lo_edge(axis), _hi_edge(axis)
        this_lo, this_hi = _n('this', lo), _n('this', hi)
        stn.add_bounds(this_hi, this_lo, 1, None, 'размер паттерна >= 1 клетки')
        declared = _axis_range(p.size, axis)
        if declared is not None:
            explicit.append(len(stn.constraints))
            stn.add_diff(this_hi, this_lo, declared, f'size паттерна `{p.name}`')

        included = list(comps) + list(extra or [])
        names = {c.name for c in included}
        for c in included:
            c_lo, c_hi = _n(c.name, lo), _n(c.name, hi)
            stn.add_bounds(c_hi, c_lo, 1, None, f'размер `{c.name}` >= 1 клетки')
            csize = _axis_range(c.size, axis)
            if csize is not None:
                explicit.append(len(stn.constraints))
                stn.add_diff(c_hi, c_lo, csize, f'size компонента `{c.name}`')
            if c.pattern and c.pattern in self.ir:
                hull = self.ref_hull(c.pattern).along(axis)
                if hull.start not in (None, 1) or hull.stop is not None:
                    stn.add_diff(c_hi, c_lo, hull, f'вычисленный размер паттерна `{c.pattern}`')
            if c.inner:
                stn.add_bounds(c_lo, this_lo, 0, None, f'рамка области охватывает внутренний `{c.name}` (слева/сверху)')
                stn.add_bounds(c_hi, this_hi, None, 0, f'рамка области охватывает внутренний `{c.name}` (справа/снизу)')
            for c_edge, p_edge, rng in c.effective_location().diffs():
                if axis_of(c_edge) != axis:
                    continue
                if c.location is not None:
                    explicit.append(len(stn.constraints))
                stn.add_diff(_n(c.name, c_edge), _n('this', p_edge), rng,
                             f'расположение `{c.name}`: {c_edge} − this.{p_edge} in {rng}')
        for rel in p.relations:
            if rel.axis != axis:
                continue
            if all((r.comp == 'this' or r.comp in names) for r in (rel.a, rel.b)):
                explicit.append(len(stn.constraints))
                stn.add_diff(_n(rel.a.comp, rel.a.edge), _n(rel.b.comp, rel.b.edge), rel.delta,
                             f'отношение `{rel.text or rel}`')
        return stn, explicit

    def _analyze_area(self, p: PatternIR) -> Intrinsic:
        required = [c for c in p.components if c.must_exist]
        others = [c for c in p.components if not c.must_exist]
        sizes: dict[str, open_range] = {}
        consistent_all = True
        for axis in AXES:
            stn, explicit = self.build_network(p, axis, required)
            self.networks[(p.name, axis)] = stn
            self.explicit[(p.name, axis)] = explicit
            cycle = stn.find_negative_cycle()
            if cycle is not None:
                consistent_all = False
                self.report.add('GEO001', f'ограничения по оси {axis} несовместимы: паттерн не может совпасть',
                                pattern=p.name, loc=p.loc, witness=describe_cycle(cycle),
                                hint='ослабьте один из перечисленных диапазонов или сделайте компонент необязательным')
                sizes[axis] = open_range(1, None)
                continue
            cl = stn.closure()
            sizes[axis] = STN.implied(cl, _n('this', _hi_edge(axis)), _n('this', _lo_edge(axis)))
            self._report_explicit(p, axis, stn, explicit)
            # необязательные компоненты и forbid: по одному поверх базовой сети
            for c in others:
                sub, _ = self.build_network(p, axis, required, extra=[c])
                cyc = sub.find_negative_cycle()
                if cyc is not None:
                    self.report.add(
                        'GEO001', f'компонент `{c.name}` ({c.role.value}, необязательный) никогда не совпадёт: '
                                  f'его ограничения по оси {axis} противоречат остальным',
                        severity=Severity.WARNING, pattern=p.name, component=c.name, loc=c.loc,
                        witness=describe_cycle(cyc))
        w = sizes.get('x', ANY)
        h = sizes.get('y', ANY)
        if not consistent_all:
            w, h = ANY, ANY
        return Intrinsic(w, h)

    def _report_explicit(self, p: PatternIR, axis: str, stn: STN, explicit: list[int]) -> None:
        """GEO002/GEO003: избыточные и «сужаемые» явные ограничения."""
        todo = set(explicit)
        redundant = {idx for idx, _ in stn.redundant_constraints(only=todo)}
        seen_keys: set[tuple] = set()
        for idx in sorted(todo):
            k = stn.constraints[idx]
            key = (k.a, k.b, k.lo, k.hi)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            comp_name = k.a.split('.')[0] if k.a.split('.')[0] != 'this' else k.b.split('.')[0]
            comp = p.component(comp_name)
            loc = comp.loc if comp is not None else p.loc
            if self._is_default_like(k):
                continue
            if idx in redundant:
                self.report.add('GEO003', f'ограничение избыточно: {k.label}', pattern=p.name,
                                component=comp_name if comp else None, loc=loc,
                                hint='оно следует из остальных ограничений; его можно удалить')
                continue
            narrowed = self._narrowed(stn, idx)
            if narrowed is not None:
                declared, effective = narrowed
                self.report.add('GEO002', f'{k.label}: заявлено {declared}, фактически допустимо {effective}',
                                pattern=p.name, component=comp_name if comp else None, loc=loc)

    @staticmethod
    def _is_default_like(k: Constraint) -> bool:
        if not k.label.startswith('расположение'):
            return False
        return (k.lo in (None, 0) and k.hi is None) or (k.lo is None and k.hi in (None, 0))

    @staticmethod
    def _narrowed(stn: STN, idx: int) -> tuple[open_range, open_range] | None:
        k = stn.constraints[idx]
        others = STN()
        for j, kk in enumerate(stn.constraints):
            if j != idx:
                others.add_bounds(kk.a, kk.b, kk.lo, kk.hi, kk.label)
        others.node(k.a)
        others.node(k.b)
        if not others.is_consistent():
            return None
        eff = STN.implied(others.closure(), k.a, k.b)
        declared = open_range(k.lo, k.hi)
        tight = False
        if eff.start is not None and (declared.start is None or eff.start > declared.start):
            tight = True
        if eff.stop is not None and (declared.stop is None or eff.stop < declared.stop):
            tight = True
        # «Сужено» интересно, только если заявлено было конечное значение, ставшее строже.
        if not tight:
            return None
        both_open = declared.is_double_open()
        if both_open:
            return None
        better_lo = declared.start is not None and eff.start is not None and eff.start > declared.start
        better_hi = declared.stop is not None and eff.stop is not None and eff.stop < declared.stop
        if not (better_lo or better_hi):
            return None
        final = declared.intersect(eff)
        return (declared, final) if final is not None else None


def analyze_geometry(ir: GrammarIR, report: DiagnosticReport) -> GeometryAnalyzer:
    ga = GeometryAnalyzer(ir, report)
    ga.run()
    return ga


# --------------------------------------------------------------------------- explain

def explain_pattern(ir: GrammarIR, name: str) -> str:
    """Текстовый отчёт: неявные размеры паттерна и допустимые смещения компонентов."""
    ga = GeometryAnalyzer(ir, DiagnosticReport())
    ga.run()
    p = ir[name]
    lines = [f'Паттерн `{name}` ({p.kind.value})']
    it = ga.intrinsic.get(name)
    if it is not None:
        lines.append(f'  вычисленный размер: ширина {it.w}, высота {it.h} (клеток)')
        declared = []
        if p.size:
            declared.append(f'ширина {p.size[0]}, высота {p.size[1]}')
        if declared:
            lines.append('  заявленный размер: ' + '; '.join(declared))
    if p.kind is PKind.AREA:
        for axis in AXES:
            stn = ga.networks.get((name, axis))
            if stn is None or not stn.is_consistent():
                lines.append(f'  ось {axis}: система противоречива (см. `check`)')
                continue
            cl = stn.closure()
            lines.append(f'  ось {axis}:')
            lo, hi = _lo_edge(axis), _hi_edge(axis)
            for c in p.components:
                if not c.must_exist:
                    continue
                parts = []
                for edge in (lo, hi):
                    rng = STN.implied(cl, _n(c.name, edge), _n('this', edge))
                    parts.append(f'{edge}: {rng}')
                size = STN.implied(cl, _n(c.name, hi), _n(c.name, lo))
                lines.append(f'    `{c.name}` ({c.pattern}): ' + ', '.join(parts) + f'; размер {size}')
        optional = [c.name for c in p.components if not c.must_exist]
        if optional:
            lines.append('  необязательные/контекстные: ' + ', '.join(optional))
    elif p.kind.is_array and p.array is not None:
        a = p.array
        lines.append(f'  массив `{a.item_pattern}`: направление {a.direction}, элементов {a.item_count}, '
                     f'промежуток {a.gap}, выравнивание {a.align}')
    elif p.kind in (PKind.GENERAL, PKind.ALT):
        members = ga.ir.choice_set(name)
        lines.append('  реализации: ' + (', '.join(members) or '(нет)'))
    return '\n'.join(lines)
