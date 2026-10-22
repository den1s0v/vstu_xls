"""Матчер по IR: все согласованные совпадения + слой политики (без жадного отсечения).

Отличия от старого `GrammarMatcher`:

* порядок и окна поиска компонентов выводятся из STN-замыкания (`planner.py`), а не из эвристик во время
  выполнения; грамматика не обязана знать «опорные линии»;
* нет `CUTOFF_COEF`/`max_results=1`: для каждого паттерна ищутся все согласованные совпадения; число совпадений
  на одну рамку ограничивается явным параметром `max_parses_per_box`;
* выбор между конкурентами — отдельный слой (`selection.py`), он применяется при использовании совпадений;
* необязательные компоненты НЕ расширяют рамку родителя (рамка = объемлющий прямоугольник обязательных
  внутренних компонентов); `forbid` отвергает совпадение, если запрещённый контекст найден;
* стили (`style:`) и `static_data` в этой версии не проверяются (ограничение, см. `docs/grammar_compiler.md`).
"""

from __future__ import annotations

from bisect import bisect_left
from collections import defaultdict
from dataclasses import dataclass, field

from vstuxls.geom2d import Box
from vstuxls.grammar2d.compiler import selection as sel
from vstuxls.grammar2d.compiler.diagnostics import DiagnosticReport
from vstuxls.grammar2d.compiler.geometry import GeometryAnalyzer
from vstuxls.grammar2d.compiler.ir import ComponentIR, GrammarIR, PatternIR, PKind
from vstuxls.grammar2d.compiler.lint import reachable_patterns
from vstuxls.grammar2d.compiler.planner import (
    EDGES, INF, AreaPlan, CandidateIndex, build_area_plan, order_components, window_for,
)

RectT = tuple[int, int, int, int]  # left, top, right, bottom (линии сетки)
_BIG = 10 ** 9


class NMatch:
    """Совпадение паттерна: рамка (линии сетки), точность, дочерние совпадения."""
    __slots__ = ('pattern', 'box', 'precision', 'children', 'text', 'items', 'leaves')

    def __init__(self, pattern: str, box: RectT, precision: float,
                 children: dict | None = None, text: str | None = None, items: list | None = None) -> None:
        self.leaves = None  # кэш рамок листьев (см. selection.leaf_boxes)
        self.pattern = pattern
        self.box = box
        self.precision = precision
        self.children = children or {}
        self.text = text
        self.items = items

    def as_box(self) -> Box:
        return Box(self.box[0], self.box[1], self.box[2] - self.box[0], self.box[3] - self.box[1])

    def __repr__(self) -> str:
        return f'<{self.pattern} {self.box} p={self.precision:.2f}>'

    def tree(self, indent: int = 0, name: str = '') -> str:
        pad = '  ' * indent
        head = f'{pad}{name + ": " if name else ""}{self.pattern} {self.box} p={self.precision:.2f}'
        if self.text is not None:
            head += f' {self.text!r}'
        lines = [head]
        for k, ch in self.children.items():
            lines.append(ch.tree(indent + 1, str(k)))
        return '\n'.join(lines)


@dataclass
class EngineResult:
    roots: list[NMatch]
    matches: dict[str, list[NMatch]]
    cells: list[tuple[RectT, str]]
    warnings: list[str] = field(default_factory=list)
    plans: dict[str, AreaPlan] = field(default_factory=dict)


class Engine:
    def __init__(self, ir: GrammarIR, *, max_parses_per_box: int = 2, max_matches_per_pattern: int = 50_000,
                 max_chains: int = 5_000, strict_cell_size: bool = False) -> None:
        self.ir = ir
        # Старый матчер не проверял `size` у терминалов; по умолчанию это сохранено, но нарушения сообщаются.
        self.strict_cell_size = strict_cell_size
        self.max_parses_per_box = max_parses_per_box
        self.max_matches = max_matches_per_pattern
        self.max_chains = max_chains
        self.ga = GeometryAnalyzer(ir, DiagnosticReport(), cell_size_enforced=strict_cell_size)
        self.ga.run()

    # ------------------------------------------------------------------ запуск
    def run(self, grid) -> EngineResult:
        self.matches: dict[str, list[NMatch]] = {}
        self.warnings: list[str] = []
        self.plans: dict[str, AreaPlan] = {}
        self._cand_cache: dict[str, list[NMatch]] = {}
        self._index_cache: dict[str, CandidateIndex] = {}
        self._aic_cache: dict[tuple, list[NMatch]] = {}
        self._classify(grid)

        ir = self.ir
        waves, leftover = ir.waves()
        needed = reachable_patterns(ir) if ir.target_mode == 'root' else set(ir.patterns)
        for name in [n for w in waves for n in w]:
            if name not in needed:
                continue
            p = ir[name]
            if not p.is_concrete or p.kind is PKind.ARRAY_IN_CONTEXT:
                continue
            ms = self._match_pattern(p)
            self.matches[name] = ms
            if len(ms) not in p.count_in_document and not p.root:
                self.warnings.append(f'найдено {len(ms)} совпадений `{name}`, ожидалось {p.count_in_document}')
        roots = sel.select_roots(self.candidates(ir.root_name) if ir.root_name else [])
        if ir.root:
            if len(roots) not in ir.root.count_in_document:
                self.warnings.append(f'найдено {len(roots)} корней `{ir.root_name}`, ожидалось {ir.root.count_in_document}')
            stop = ir.root.count_in_document.stop
            if stop is not None and len(roots) > stop:
                roots = roots[:stop]  # глобальный выбор: остаются лучшие разборы
        return EngineResult(roots, self.matches, self.cells, self.warnings, self.plans)

    # ------------------------------------------------------------------ ячейки
    def _classify(self, grid) -> None:
        from vstuxls.string_matching import CellClassifier, CellType
        ir = self.ir
        types = [CellType(name=n, description=ct.description,
                          patterns=[dict(sp.data) for sp in ct.patterns], update_content=ct.update_content)
                 for n, ct in ir.cell_types.items()]
        ccl = CellClassifier(types)
        self.cells: list[tuple[RectT, str]] = []
        self.type_cells: dict[str, list[tuple[RectT, object]]] = defaultdict(list)
        view = grid.get_view()
        self.grid_box: RectT = (view.left, view.top, view.right, view.bottom)
        has_prio = any(ct.priority or ct.except_types for ct in ir.cell_types.values())
        for cw in view.iterate_cells():
            box = (cw.left, cw.top, cw.right, cw.bottom)
            text = cw.cell.content
            self.cells.append((box, text))
            found = {m.pattern.content_class.name: m for m in ccl.match(text, 5)}
            if has_prio and found:
                found = self._apply_lex_policy(found)
            for name, m in found.items():
                self.type_cells[name].append((box, m))

    def _apply_lex_policy(self, found: dict) -> dict:
        ir = self.ir
        names = set(found)
        drop = {t for t in names if any(u in names for u in ir.cell_types[t].except_types)}
        rest = names - drop
        if rest:
            top = max(ir.cell_types[t].priority for t in rest)
            drop |= {t for t in rest if ir.cell_types[t].priority < top}
        return {k: v for k, v in found.items() if k not in drop}

    # ------------------------------------------------------------------ доступ к кандидатам
    def candidates(self, name: str | None) -> list[NMatch]:
        """Совпадения паттерна `name` (с учётом `extends`/`alt`) после применения политики."""
        if not name or name not in self.ir:
            return []
        cached = self._cand_cache.get(name)
        if cached is not None:
            return cached
        seen: set[int] = set()
        out: list[NMatch] = []
        for member in self.ir.choice_set(name):
            for m in self.matches.get(member, ()):
                if id(m) not in seen:
                    seen.add(id(m))
                    out.append(m)
        out = sel.apply_priorities(self.ir, out)
        ov = self.ir[name].policy.overlap
        if ov is not None and ov.decides():
            out = sel.resolve_overlaps(out, ov.mode, ov.criteria)
        self._cand_cache[name] = out
        return out

    def _index(self, name: str) -> CandidateIndex:
        idx = self._index_cache.get(name)
        if idx is None:
            idx = self._index_cache[name] = CandidateIndex(self.candidates(name))
        return idx

    # ------------------------------------------------------------------ диспетчер
    def _match_pattern(self, p: PatternIR) -> list[NMatch]:
        if p.kind is PKind.CELL:
            res = self._match_cell(p)
        elif p.kind is PKind.AREA:
            res = self._match_area(p)
        elif p.kind is PKind.ARRAY:
            res = self._match_array(p)
        else:
            res = []
        if len(res) > self.max_matches:
            self.warnings.append(f'`{p.name}`: {len(res)} совпадений, оставлено {self.max_matches} лучших')
            res = sorted(res, key=lambda m: -m.precision)[:self.max_matches]
        return res

    def _size_ok(self, p: PatternIR, box: RectT) -> bool:
        if p.size is None:
            return True
        return (box[2] - box[0]) in p.size[0] and (box[3] - box[1]) in p.size[1]

    # ------------------------------------------------------------------ терминалы
    def _match_cell(self, p: PatternIR) -> list[NMatch]:
        out = []
        thr = p.policy.effective_threshold()
        bad_size = 0
        for box, sm in self.type_cells.get(p.content_type or '', ()):
            prec = float(sm.confidence)
            if prec < thr:
                continue
            if not self._size_ok(p, box):
                bad_size += 1
                if self.strict_cell_size:
                    continue
            out.append(NMatch(p.name, box, prec, text=sm.text))
        if bad_size and not self.strict_cell_size:
            self.warnings.append(
                f'`{p.name}`: у {bad_size} ячеек размер не соответствует заявленному `size` {p.size[0]} x {p.size[1]} '
                f'(в режиме совместимости размер ячейки не проверяется; `strict_cell_size=True` включит проверку)')
        return out

    # ------------------------------------------------------------------ области
    def _comp_candidates(self, c: ComponentIR) -> list[NMatch]:
        return [m for m in self.candidates(c.pattern) if m.precision >= c.precision_threshold]

    def _dynamic_members(self, c: ComponentIR) -> list[str]:
        """Паттерны компонента, совпадения которых зависят от контекста (array-in-context)."""
        return [m for m in self.ir.choice_set(c.pattern or '') if self.ir[m].kind is PKind.ARRAY_IN_CONTEXT]

    def _match_area(self, p: PatternIR) -> list[NMatch]:
        plan = build_area_plan(self.ga, p)
        self.plans[p.name] = plan
        if not plan.feasible or not any(c.inner for c in plan.required):
            return []
        cands: dict[str, list[NMatch]] = {}
        counts: dict[str, int] = {}
        for c in plan.required:
            if self._dynamic_members(c):
                cands[c.name] = []
                counts[c.name] = _BIG
            else:
                cands[c.name] = self._comp_candidates(c)
                counts[c.name] = len(cands[c.name])
                if not cands[c.name]:
                    return []
        order = order_components(plan, counts)
        ctx = _AreaCtx(p, plan, order, cands)
        self._search(ctx, 0, {}, {}, [])
        return self._finalize_matches(p, ctx.results)

    def _finalize_matches(self, p: PatternIR, raw: list[NMatch]) -> list[NMatch]:
        by_box: dict[RectT, list[NMatch]] = defaultdict(list)
        seen: set[tuple] = set()
        for m in raw:
            key = (m.box, tuple(sorted((k, id(v)) for k, v in m.children.items())))
            if key in seen:
                continue
            seen.add(key)
            by_box[m.box].append(m)
        out: list[NMatch] = []
        for lst in by_box.values():
            lst.sort(key=lambda m: -m.precision)
            out.extend(lst[:self.max_parses_per_box])
        out.sort(key=lambda m: (m.box[1], m.box[0], -m.precision))
        return out

    # --- поиск
    def _query_comp(self, ctx: '_AreaCtx', c: ComponentIR, wins) -> list[NMatch]:
        dyn = self._dynamic_members(c)
        if not dyn:
            idx = ctx.indexes.get(c.name)
            if idx is None:
                idx = ctx.indexes[c.name] = CandidateIndex(ctx.cands[c.name])
            return list(idx.query(wins))
        # array-in-context: границы региона берутся из окон (самые широкие допустимые)
        gb = self.grid_box
        l = wins[0][0] if wins[0][0] > -INF else gb[0]
        t = wins[1][0] if wins[1][0] > -INF else gb[1]
        r = wins[2][1] if wins[2][1] < INF else gb[2]
        b = wins[3][1] if wins[3][1] < INF else gb[3]
        region = (int(l), int(t), int(r), int(b))
        out: list[NMatch] = []
        for name in dyn:
            out.extend(self._aic_matches(name, region))
        # статические члены того же компонента
        static = [m for m in self.candidates(c.pattern) if self.ir[m.pattern].kind is not PKind.ARRAY_IN_CONTEXT]
        out.extend(static)
        return [m for m in out if all(wins[k][0] <= m.box[k] <= wins[k][1] for k in range(4))
                and m.precision >= c.precision_threshold]

    def _aic_matches(self, name: str, region: RectT) -> list[NMatch]:
        key = (name, region)
        res = self._aic_cache.get(key)
        if res is None:
            p = self.ir[name]
            arr = p.array
            items = [m for m in self.candidates(arr.item_pattern if arr else None)
                     if sel.contains(region, m.box)]
            res = self._build_arrays(p, items) if arr else []
            self._aic_cache[key] = res
        return res

    def _search(self, ctx: '_AreaCtx', i: int, bound: dict[str, int], chosen: dict[str, NMatch],
                _unused: list) -> None:
        plan = ctx.plan
        if i == len(ctx.order):
            self._finish_area(ctx, bound, chosen)
            return
        c = ctx.order[i]
        xcl, ycl = plan.closures['x'], plan.closures['y']
        wl = window_for(xcl, bound, f'{c.name}.left')
        wr = window_for(xcl, bound, f'{c.name}.right')
        wt = window_for(ycl, bound, f'{c.name}.top')
        wb = window_for(ycl, bound, f'{c.name}.bottom')
        if wl[0] > wl[1] or wr[0] > wr[1] or wt[0] > wt[1] or wb[0] > wb[1]:
            return
        up_x, dn_x = xcl.get((f'{c.name}.left', f'{c.name}.right')), xcl.get((f'{c.name}.right', f'{c.name}.left'))
        up_y, dn_y = ycl.get((f'{c.name}.top', f'{c.name}.bottom')), ycl.get((f'{c.name}.bottom', f'{c.name}.top'))
        for cand in self._query_comp(ctx, c, (wl, wt, wr, wb)):
            w, h = cand.box[2] - cand.box[0], cand.box[3] - cand.box[1]
            if up_x is not None and w > up_x or dn_x is not None and w < -dn_x:
                continue
            if up_y is not None and h > up_y or dn_y is not None and h < -dn_y:
                continue
            if not self._siblings_ok(ctx, c, cand, chosen):
                continue
            for k, e in enumerate(EDGES):
                bound[f'{c.name}.{e}'] = cand.box[k]
            chosen[c.name] = cand
            self._search(ctx, i + 1, bound, chosen, _unused)
            del chosen[c.name]
            for e in EDGES:
                del bound[f'{c.name}.{e}']
            if len(ctx.results) > self.max_matches * 4:
                return

    def _siblings_ok(self, ctx: '_AreaCtx', c: ComponentIR, cand: NMatch, chosen: dict[str, NMatch]) -> bool:
        may_overlap_c = ctx.may_overlap(c, self)
        for name, other in chosen.items():
            oc = ctx.comp[name]
            # Контекст (outer/require/forbid) может охватывать родителя и соседей: физически не пересекаются
            # только внутренние компоненты (если паттерны не объявлены `allows_overlapping`).
            if (c.inner and oc.inner and not (may_overlap_c or ctx.may_overlap(oc, self))
                    and sel.occupies_overlap(cand, other)):
                return False
            if c.group and oc.group == c.group:
                k1, k2 = (cand.box[1], cand.box[0]), (other.box[1], other.box[0])
                if (c.group_index > oc.group_index) != (k1 > k2) or k1 == k2:
                    return False
        return True

    @staticmethod
    def _check_network(stn, vals: dict[str, int]) -> bool:
        for k in stn.constraints:
            a, b = vals.get(k.a), vals.get(k.b)
            if a is None or b is None:
                continue
            d = a - b
            if k.lo is not None and d < k.lo or k.hi is not None and d > k.hi:
                return False
        return True

    def _finish_area(self, ctx: '_AreaCtx', bound: dict[str, int], chosen: dict[str, NMatch]) -> None:
        p, plan = ctx.p, ctx.plan
        inner = [chosen[c.name] for c in plan.required if c.inner]
        box = (min(m.box[0] for m in inner), min(m.box[1] for m in inner),
               max(m.box[2] for m in inner), max(m.box[3] for m in inner))
        # Рамка родителя может быть однозначно задана контекстом (например, `padding-top: 0`
        # к внешнему компоненту + фиксированная высота): тогда она шире охвата внутренних компонентов.
        pinned = list(box)
        for k, e in enumerate(EDGES):
            cl = plan.closures['x' if e in ('left', 'right') else 'y']
            lo, hi = window_for(cl, bound, f'this.{e}')
            if lo == hi and -INF < lo < INF:
                pinned[k] = int(lo)
        pinned_box = tuple(pinned)
        if pinned_box != box and pinned_box[0] <= box[0] and pinned_box[1] <= box[1] \
                and pinned_box[2] >= box[2] and pinned_box[3] >= box[3]:
            box = pinned_box
        if not self._size_ok(p, box):
            return
        vals = dict(bound)
        for k, e in enumerate(EDGES):
            vals[f'this.{e}'] = box[k]
        for axis in ('x', 'y'):
            if not self._check_network(plan.networks[axis], vals):
                return
        present: list[tuple[ComponentIR, NMatch]] = [(c, chosen[c.name]) for c in plan.required]
        taken = dict(chosen)

        # запрещённый контекст
        for c in plan.forbidden:
            if self._find_extra(ctx, c, vals, taken, first_only=True):
                return
        # необязательные компоненты: лучший кандидат каждого
        for c in plan.optional:
            if self.ir.dialect >= 2 and c.inner:
                found = self._find_extra(ctx, c, vals, taken, extend_from=box)
                best = None
                if found is not None:
                    best, box = found
                    for k, e in enumerate(EDGES):
                        vals[f'this.{e}'] = box[k]
            else:
                best = self._find_extra(ctx, c, vals, taken)
            if best is not None:
                present.append((c, best))
                taken[c.name] = best

        score = sum(c.weight * m.precision for c, m in present)
        max_score = sum(max(c.weight, 0.0) for c in p.components if c.role.value != 'forbid')
        prec = p.policy.confidence * (score / max_score if max_score > 0 else 1.0)
        prec = max(0.0, min(1.0, prec))
        ctx.results.append(NMatch(p.name, box, prec, {c.name: m for c, m in present}))

    def _find_extra(self, ctx: '_AreaCtx', c: ComponentIR, vals: dict[str, int], taken: dict[str, NMatch],
                    first_only: bool = False, extend_from: RectT | None = None):
        """Ищет кандидата для необязательного/запрещённого компонента.

        При `extend_from` (рамка родителя по обязательным компонентам) внутренний необязательный компонент
        может *расширять* рамку (диалект v2: родитель содержит все присутствующие внутренние компоненты);
        тогда возвращается пара `(кандидат, новая рамка)`."""
        plan = ctx.plan
        cls = plan.extra_closures.get(c.name)
        if not cls or cls.get('x') is None or cls.get('y') is None:
            return None  # его ограничения противоречат остальным: никогда не совпадёт
        base = vals
        if extend_from is not None:
            base = {k: v for k, v in vals.items() if not k.startswith('this.')}
        wl = window_for(cls['x'], base, f'{c.name}.left')
        wr = window_for(cls['x'], base, f'{c.name}.right')
        wt = window_for(cls['y'], base, f'{c.name}.top')
        wb = window_for(cls['y'], base, f'{c.name}.bottom')
        if wl[0] > wl[1] or wr[0] > wr[1] or wt[0] > wt[1] or wb[0] > wb[1]:
            return None
        wins = (wl, wt, wr, wb)
        if self._dynamic_members(c):
            ctx.cands.setdefault(c.name, [])
            cands = self._query_comp(ctx, c, wins)
        else:
            if c.name not in ctx.cands:
                ctx.cands[c.name] = self._comp_candidates(c)
            idx = ctx.indexes.get(c.name)
            if idx is None:
                idx = ctx.indexes[c.name] = CandidateIndex(ctx.cands[c.name])
            cands = idx.query(wins)
        best = None
        best_box = extend_from
        for cand in cands:
            if not self._siblings_ok(ctx, c, cand, taken):
                continue
            v = dict(vals)
            nb = extend_from
            if extend_from is not None:
                nb = (min(extend_from[0], cand.box[0]), min(extend_from[1], cand.box[1]),
                      max(extend_from[2], cand.box[2]), max(extend_from[3], cand.box[3]))
                if not self._size_ok(ctx.p, nb):
                    continue
                for k, e in enumerate(EDGES):
                    v[f'this.{e}'] = nb[k]
            for k, e in enumerate(EDGES):
                v[f'{c.name}.{e}'] = cand.box[k]
            if not (self._check_network(plan.extra_networks[c.name]['x'], v)
                    and self._check_network(plan.extra_networks[c.name]['y'], v)):
                continue
            if first_only:
                return cand
            if best is None or (cand.precision, sel.area_of(cand.box)) > (best.precision, sel.area_of(best.box)):
                best, best_box = cand, nb
        if extend_from is not None:
            return (best, best_box) if best is not None else None
        return best

    # ------------------------------------------------------------------ массивы
    def _match_array(self, p: PatternIR) -> list[NMatch]:
        arr = p.array
        if arr is None or not arr.item_pattern:
            return []
        thr = 0.3
        items = [m for m in self.candidates(arr.item_pattern) if m.precision >= thr]
        return self._build_arrays(p, items)

    def _build_arrays(self, p: PatternIR, items: list[NMatch]) -> list[NMatch]:
        arr = p.array
        assert arr is not None
        if not items:
            return []
        if arr.direction == 'fill':
            chains = self._fill_clusters(p, items)
        else:
            dirs = ('row', 'column') if arr.direction == 'auto' else (arr.direction,)
            chains = []
            for d in dirs:
                chains.extend(self._chains(p, items, d))
        out: list[NMatch] = []
        seen: set[tuple] = set()
        n_lo = arr.item_count.start or 0
        n_hi = arr.item_count.stop
        for chain in chains:
            sizes = [len(chain)]
            if n_hi is not None and len(chain) > n_hi:
                sizes = [n_hi]
                windows = [chain[s:s + n_hi] for s in range(len(chain) - n_hi + 1)]
            else:
                windows = [chain]
            if arr.allow_breakdown and p.size is not None:
                windows = [piece for w in windows for piece in self._breakdown(p, w)]
            for w in windows:
                if len(w) < n_lo or len(w) < 1:
                    continue
                key = tuple(id(x) for x in w)
                if key in seen:
                    continue
                seen.add(key)
                box = (min(m.box[0] for m in w), min(m.box[1] for m in w),
                       max(m.box[2] for m in w), max(m.box[3] for m in w))
                if not self._size_ok(p, box):
                    continue
                prec = p.policy.confidence * sum(m.precision for m in w) / len(w)
                out.append(NMatch(p.name, box, prec, {str(i): m for i, m in enumerate(w)}, items=list(w)))
        return out

    def _breakdown(self, p: PatternIR, chain: list[NMatch]) -> list[list[NMatch]]:
        """`allow_breakdown`: слишком крупную цепочку режем на куски не больше максимального `size`.

        Кусок — это блок сетки максимального размера, привязанный к левому верхнему углу цепочки;
        элемент относится к блоку, в котором лежит его левый верхний угол."""
        box = (min(m.box[0] for m in chain), min(m.box[1] for m in chain),
               max(m.box[2] for m in chain), max(m.box[3] for m in chain))
        if self._size_ok(p, box) or p.size is None:
            return [chain]
        mw, mh = p.size[0].stop, p.size[1].stop
        if not mw or not mh:
            return [chain]
        blocks: dict[tuple[int, int], list[NMatch]] = defaultdict(list)
        for m in chain:
            blocks[((m.box[0] - box[0]) // mw, (m.box[1] - box[1]) // mh)].append(m)
        return list(blocks.values())

    def _chains(self, p: PatternIR, items: list[NMatch], direction: str) -> list[list[NMatch]]:
        arr = p.array
        assert arr is not None
        a0, a1, c0, c1 = (0, 2, 1, 3) if direction == 'row' else (1, 3, 0, 2)
        g_lo = arr.gap.start or 0
        g_hi = arr.gap.stop if arr.gap.stop is not None else INF
        align = arr.align

        def aligned(x: NMatch, y: NMatch) -> bool:
            if align == 'both':
                return x.box[c0] == y.box[c0] and x.box[c1] == y.box[c1]
            if align == 'start':
                return x.box[c0] == y.box[c0]
            if align == 'end':
                return x.box[c1] == y.box[c1]
            return x.box[c0] < y.box[c1] and y.box[c0] < x.box[c1]

        ordered = sorted(items, key=lambda m: (m.box[a0], m.box[c0]))
        starts = [m.box[a0] for m in ordered]
        succ: dict[int, list[NMatch]] = {}
        has_pred: set[int] = set()
        for it in ordered:
            lo = it.box[a1] + g_lo
            hi = it.box[a1] + g_hi
            i = bisect_left(starts, lo)
            lst = []
            while i < len(ordered) and starts[i] <= hi:
                cand = ordered[i]
                if aligned(it, cand):
                    lst.append(cand)
                    has_pred.add(id(cand))
                i += 1
            succ[id(it)] = lst

        chains: list[list[NMatch]] = []
        for s in ordered:
            if id(s) in has_pred:
                continue
            stack: list[list[NMatch]] = [[s]]
            while stack:
                path = stack.pop()
                nxt = succ[id(path[-1])]
                if not nxt:
                    chains.append(path)
                    if len(chains) >= self.max_chains:
                        self.warnings.append(f'`{p.name}`: достигнут предел числа цепочек массива ({self.max_chains})')
                        return chains
                    continue
                for n in nxt:
                    stack.append(path + [n])
        return chains

    def _fill_clusters(self, p: PatternIR, items: list[NMatch]) -> list[list[NMatch]]:
        """`fill`: непересекающиеся элементы (жадно: точность, затем позиция) и связные кластеры по зазору."""
        arr = p.array
        assert arr is not None
        g_lo = arr.gap.start or 0
        g_hi = arr.gap.stop if arr.gap.stop is not None else INF
        item_names = self.ir.choice_set(arr.item_pattern or '')
        overlap_ok = sel.can_overlap(self.ir, item_names)
        picked: list[NMatch] = []
        for it in sorted(items, key=lambda m: (-m.precision, m.box[1], m.box[0], -sel.area_of(m.box))):
            if overlap_ok or not any(sel.overlaps(it.box, q.box) for q in picked):
                picked.append(it)
        parent = list(range(len(picked)))

        def find(x: int) -> int:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def adjacent(a: RectT, b: RectT) -> bool:
            # по горизонтали: зазор в пределах gap и перекрытие по вертикали (и наоборот)
            gx = max(b[0] - a[2], a[0] - b[2])
            gy = max(b[1] - a[3], a[1] - b[3])
            ov_y = a[1] < b[3] and b[1] < a[3]
            ov_x = a[0] < b[2] and b[0] < a[2]
            return (ov_y and g_lo <= gx <= g_hi) or (ov_x and g_lo <= gy <= g_hi)

        for i in range(len(picked)):
            for j in range(i + 1, len(picked)):
                if adjacent(picked[i].box, picked[j].box):
                    parent[find(i)] = find(j)
        groups: dict[int, list[NMatch]] = defaultdict(list)
        for i, m in enumerate(picked):
            groups[find(i)].append(m)
        return [sorted(g, key=lambda m: (m.box[1], m.box[0])) for g in groups.values()]


@dataclass
class _AreaCtx:
    p: PatternIR
    plan: AreaPlan
    order: list[ComponentIR]
    cands: dict[str, list[NMatch]]
    indexes: dict[str, CandidateIndex] = field(default_factory=dict)
    results: list[NMatch] = field(default_factory=list)
    _overlap_cache: dict[str, bool] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.comp = {c.name: c for c in self.p.components}

    def may_overlap(self, c: ComponentIR, engine: Engine) -> bool:
        v = self._overlap_cache.get(c.name)
        if v is None:
            v = self._overlap_cache[c.name] = sel.can_overlap(engine.ir, engine.ir.choice_set(c.pattern or ''))
        return v


def run_engine(ir: GrammarIR, grid, **kwargs) -> EngineResult:
    """Удобная обёртка: `Engine(ir).run(grid)`."""
    return Engine(ir, **kwargs).run(grid)
