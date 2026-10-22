"""Генератор тестовых таблиц из грамматики и самопроверка матчера.

Идея: грамматика — это не только распознаватель, но и *порождающее* описание. По ней можно
построить таблицу, про которую заранее известно, какие паттерны и где должны найтись:

1. для паттерна-области берётся его STN-план (`planner.build_area_plan`); компоненты размещаются
   по очереди внутри окон, которые даёт замыкание сети (рёбра уже размещённых компонентов
   задают допустимые значения рёбер следующего);
2. терминалам подбирается текст из выборки строк, порождённых регулярками типа ячейки
   (и проверяется настоящим `CellClassifier`);
3. массивы порождаются как цепочки одинаковых по поперечному размеру элементов с зазором из `gap`;
4. полученная таблица (с объединёнными ячейками) подаётся новому движку, и проверяется, что
   ожидаемые совпадения найдены с точно теми же рамками.

Расхождение — это либо ошибка в движке, либо противоречие/неточность в самой грамматике
(например, регулярка, которую классификатор относит к другому типу).
"""

from __future__ import annotations

import random
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from vstuxls.geom2d import Point, Size
from vstuxls.grammar2d.compiler import celltypes
from vstuxls.grammar2d.compiler.diagnostics import DiagnosticReport
from vstuxls.grammar2d.compiler.engine import Engine
from vstuxls.grammar2d.compiler.geometry import GeometryAnalyzer
from vstuxls.grammar2d.compiler.ir import GrammarIR, PatternIR, PKind
from vstuxls.grammar2d.compiler.planner import EDGES, INF, build_area_plan, window_for
from vstuxls.grid import Cell, Grid

RectT = tuple[int, int, int, int]

_MAX_DEPTH = 8


@dataclass
class Block:
    """Фрагмент таблицы в собственной системе координат."""
    box: RectT  # рамка порождённого паттерна (без внешнего контекста)
    cells: list[tuple[int, int, int, int, str]] = field(default_factory=list)  # (x, y, w, h, текст)
    expect: list[tuple[str, RectT]] = field(default_factory=list)  # (паттерн, рамка)
    # Контекстные ячейки (компоненты `outer`): лежат вне рамки и могут быть общими у соседних элементов
    # (один «день недели» на много дат), поэтому с чужим контекстом они сливаются, а не конфликтуют.
    ctx: list[tuple[int, int, int, int, str]] = field(default_factory=list)
    ctx_expect: list[tuple[str, RectT]] = field(default_factory=list)

    def shifted(self, dx: int, dy: int) -> 'Block':
        def sc(lst):
            return [(x + dx, y + dy, w, h, t) for x, y, w, h, t in lst]

        def se(lst):
            return [(n, (b[0] + dx, b[1] + dy, b[2] + dx, b[3] + dy)) for n, b in lst]

        return Block((self.box[0] + dx, self.box[1] + dy, self.box[2] + dx, self.box[3] + dy),
                     sc(self.cells), se(self.expect), sc(self.ctx), se(self.ctx_expect))

    @staticmethod
    def _pts(cells) -> set[tuple[int, int]]:
        return {(x + i, y + j) for x, y, w, h, _ in cells for i in range(w) for j in range(h)}

    def own_points(self) -> set[tuple[int, int]]:
        return self._pts(self.cells)

    def ctx_points(self) -> set[tuple[int, int]]:
        return self._pts(self.ctx)

    @property
    def all_cells(self) -> list[tuple[int, int, int, int, str]]:
        return self.cells + self.ctx

    @property
    def all_expect(self) -> list[tuple[str, RectT]]:
        return self.expect + self.ctx_expect

    def extent(self) -> RectT:
        cs = self.all_cells
        return (min(c[0] for c in cs), min(c[1] for c in cs),
                max(c[0] + c[2] for c in cs), max(c[1] + c[3] for c in cs))


def _merge_ctx(cells: list, expect: list) -> tuple[list, list] | None:
    """Сливает пересекающиеся контекстные ячейки в одну (по объемлющему прямоугольнику).

    Возвращает (ячейки, ожидания) либо None, если ячейки совпадают не целиком (слияние слишком грубое)."""
    names = {bx: n for n, bx in expect}

    def name_of(c):
        return names.get((c[0], c[1], c[0] + c[2], c[1] + c[3]))

    groups: list[list] = []
    for c in cells:
        merged = [g for g in groups if any(_rects_overlap(c, o) for o in g)]
        if any(name_of(o) is None or name_of(o) != name_of(c) for g in merged for o in g):
            return None  # общими могут быть только ячейки одного и того же паттерна
        new = [c]
        for g in merged:
            new.extend(g)
            groups.remove(g)
        groups.append(new)
    out, dropped = [], set()
    for g in groups:
        if len(g) == 1:
            out.append(g[0])
            continue
        l = min(c[0] for c in g)
        t = min(c[1] for c in g)
        r = max(c[0] + c[2] for c in g)
        b = max(c[1] + c[3] for c in g)
        out.append((l, t, r - l, b - t, g[0][4]))
        dropped.update((c[0], c[1], c[0] + c[2], c[1] + c[3]) for c in g)
    return out, [(n, bx) for n, bx in expect if bx not in dropped]


def _rects_overlap(a, b) -> bool:
    return a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]


@dataclass
class FuzzCase:
    seed: int
    pattern: str
    block: Block
    grid: Grid | None = None

    def render(self) -> str:
        """Текстовое представление таблицы (левый верхний угол каждой ячейки; `░` — продолжение)."""
        l, t, r, b = self.block.extent()
        rows = [[''] * (r - l) for _ in range(b - t)]
        for x, y, w, h, text in self.block.all_cells:
            for i in range(w):
                for j in range(h):
                    rows[y - t + j][x - l + i] = text if (i, j) == (0, 0) else '░'
        return '\n'.join('\t'.join(row) for row in rows)


class Fuzzer:
    def __init__(self, ir: GrammarIR, rng: random.Random) -> None:
        self.ir = ir
        self.rng = rng
        self.ga = GeometryAnalyzer(ir, DiagnosticReport(), cell_size_enforced=True)
        self._plans: dict[str, object] = {}
        self._texts: dict[str, list[str]] = {}
        self._compiled = celltypes._compile_types(ir, DiagnosticReport())
        self.problems: list[str] = []
        self.fails: Counter = Counter()
        self.budget = 0
        self._classifier = self._make_classifier()

    def _f(self, reason: str):
        """Запоминает причину неудачной попытки порождения (для диагностики) и возвращает None."""
        self.fails[reason] += 1
        return None

    # ------------------------------------------------------------------ тексты
    def _make_classifier(self):
        from vstuxls.string_matching import CellClassifier, CellType
        types = [CellType(name=n, description=ct.description,
                          patterns=[dict(sp.data) for sp in ct.patterns], update_content=ct.update_content)
                 for n, ct in self.ir.cell_types.items()]
        return CellClassifier(types)

    def texts(self, type_name: str) -> list[str]:
        cached = self._texts.get(type_name)
        if cached is not None:
            return cached
        ct = self._compiled.get(type_name)
        out: list[str] = list(self.ir.cell_types[type_name].examples) if type_name in self.ir.cell_types else []
        if ct is not None:
            for cp in ct.patterns:
                strings, _ = celltypes.sample_strings(cp.source, celltypes._flags_of(cp), 25, self.rng)
                out.extend(s for s in strings if s.strip() and celltypes._matches(cp, s))
        scored: list[tuple[str, float]] = []
        for s in dict.fromkeys(out):
            if '\n' in s or '\t' in s:
                continue
            found = {m.pattern.content_class.name: float(m.confidence) for m in self._classifier.match(s, 5)}
            if type_name in found:
                scored.append((s, found[type_name]))
        # уверенно распознаваемые строки предпочтительнее: порог паттерна/компонента заранее неизвестен
        good = [s for s, conf in scored if conf >= 0.9] or [s for s, conf in scored if conf >= 0.5]
        if not good:
            self.problems.append(f'не удалось подобрать текст для типа ячейки `{type_name}`')
        self._texts[type_name] = good
        return good

    # ------------------------------------------------------------------ генерация
    def gen(self, name: str, depth: int = 0, size_hint=None) -> Block | None:
        if depth > _MAX_DEPTH or name not in self.ir:
            return None
        self.budget -= 1
        if self.budget < 0:
            return self._f('исчерпан бюджет порождения (слишком вложенная или противоречивая структура)')
        variants = [n for n in self.ir.choice_set(name) if self.ir[n].kind is not PKind.ARRAY_IN_CONTEXT or True]
        if not variants:
            return None
        self.rng.shuffle(variants)
        for v in variants[:3]:
            p = self.ir[v]
            if p.kind is PKind.CELL:
                b = self._gen_cell(p, size_hint)
            elif p.kind is PKind.AREA:
                b = self._gen_area(p, depth)
            elif p.kind in (PKind.ARRAY, PKind.ARRAY_IN_CONTEXT):
                b = self._gen_array(p, depth)
            else:
                b = None
            if b is not None:
                if v != name and name in self.ir:
                    pass
                return b
        return None

    def _pick(self, rng_pair, default_lo: int = 1, extra: int = 1) -> int:
        lo = rng_pair.start if rng_pair is not None and rng_pair.start is not None else default_lo
        lo = max(lo, 1)
        hi = rng_pair.stop if rng_pair is not None and rng_pair.stop is not None else lo + extra
        hi = max(lo, min(hi, lo + extra))
        return self.rng.randint(lo, hi)

    def _gen_cell(self, p: PatternIR, hint) -> Block | None:
        sizes = [p.size, hint]
        w = h = None
        for s in sizes:
            if s is None:
                continue
            w = self._pick(s[0]) if w is None else w
            h = self._pick(s[1]) if h is None else h
        if hint is not None and p.size is not None:
            # пересечение объявленного размера и подсказки
            w = self._intersect_pick(p.size[0], hint[0])
            h = self._intersect_pick(p.size[1], hint[1])
            if w is None or h is None:
                return None
        w = w or 1
        h = h or 1
        if not p.content_type:
            return self._f(f'{p.name}: у терминала нет content_type')
        texts = self.texts(p.content_type)
        if not texts:
            return self._f(f'{p.name}: нет подходящего текста для типа `{p.content_type}`')
        text = self.rng.choice(texts)
        box = (0, 0, w, h)
        return Block(box, [(0, 0, w, h, text)], [(p.name, box)])

    def _intersect_pick(self, a, b) -> int | None:
        lo = max(a.start if a.start is not None else 1, b.start if b.start is not None else 1, 1)
        hi_candidates = [x for x in (a.stop, b.stop) if x is not None]
        hi = min(hi_candidates) if hi_candidates else lo + 1
        if lo > hi:
            return None
        return self.rng.randint(lo, min(hi, lo + 1))

    def _plan(self, p: PatternIR):
        plan = self._plans.get(p.name)
        if plan is None:
            plan = self._plans[p.name] = build_area_plan(self.ga, p)
        return plan

    def _gen_area(self, p: PatternIR, depth: int) -> Block | None:
        plan = self._plan(p)
        if not plan.feasible or not any(c.inner for c in plan.required):
            return self._f(f'{p.name}: план области недопустим (противоречивые ограничения)')
        for _ in range(25):
            b = self._try_area(p, plan, depth)
            if b is not None:
                return b
        return None

    def _try_area(self, p: PatternIR, plan, depth: int) -> Block | None:
        placed: list[tuple] = []  # (comp, block)
        own_occ: set[tuple[int, int]] = set()
        ctx_occ: set[tuple[int, int]] = set()
        bound: dict[str, int] = {}
        xcl, ycl = plan.closures['x'], plan.closures['y']
        n_inner = sum(1 for c in plan.required if c.inner)
        for idx, c in enumerate(sorted(plan.required, key=lambda c: not c.inner)):
            if idx == n_inner and placed:
                # внутренние компоненты размещены: рамка паттерна известна, контекст привязываем к ней
                ib = [b.box for cc, b in placed]
                for k, e in enumerate(EDGES):
                    bound[f'this.{e}'] = (min if k < 2 else max)(b[k] for b in ib)
            if not c.pattern:
                return self._f(f'{p.name}.{c.name}: нет ссылки на паттерн')
            hint = c.size
            sub = self.gen(c.pattern, depth + 1, size_hint=hint)
            if sub is None:
                return self._f(f'{p.name}.{c.name}: не удалось породить `{c.pattern}`')
            sw, sh = sub.box[2] - sub.box[0], sub.box[3] - sub.box[1]
            moved = None
            for _try in range(14):
                pos = self._place(c.name, sw, sh, xcl, ycl, bound, first=not placed, spread=2 + _try // 2)
                if pos is None:
                    return self._f(f'{p.name}.{c.name}: нет места по ограничениям расположения')
                cand = sub.shifted(pos[0] - sub.box[0], pos[1] - sub.box[1])
                if c.inner:
                    new_own, new_ctx = cand.own_points(), cand.ctx_points()
                else:  # весь компонент `outer` — контекст
                    new_own, new_ctx = set(), cand.own_points() | cand.ctx_points()
                if not (new_own & (own_occ | ctx_occ) or new_ctx & own_occ):
                    moved = cand
                    break
            if moved is None:
                return self._f(f'{p.name}.{c.name}: пересечение с уже размещённым')
            sub = moved
            own_occ |= new_own
            ctx_occ |= new_ctx
            for k, e in enumerate(EDGES):
                bound[f'{c.name}.{e}'] = sub.box[(0, 1, 2, 3)[k]]
            placed.append((c, sub))

        inner = [b for c, b in placed if c.inner]
        box = (min(b.box[0] for b in inner), min(b.box[1] for b in inner),
               max(b.box[2] for b in inner), max(b.box[3] for b in inner))
        # рамка может быть однозначно задана контекстом
        ctx_bound = {k: v for k, v in bound.items() if not k.startswith('this.')}
        pinned = list(box)
        for k, e in enumerate(EDGES):
            lo, hi = window_for(plan.closures['x' if e in ('left', 'right') else 'y'], ctx_bound, f'this.{e}')
            if lo == hi and -INF < lo < INF:
                pinned[k] = int(lo)
        if tuple(pinned) != box and pinned[0] <= box[0] and pinned[1] <= box[1] \
                and pinned[2] >= box[2] and pinned[3] >= box[3]:
            box = tuple(pinned)
        if p.size is not None and not ((box[2] - box[0]) in p.size[0] and (box[3] - box[1]) in p.size[1]):
            return self._f(f'{p.name}: размер рамки {box[2] - box[0]}x{box[3] - box[1]} вне `size`')
        vals = dict(bound)
        for k, e in enumerate(EDGES):
            vals[f'this.{e}'] = box[k]
        for axis in ('x', 'y'):
            for k in plan.networks[axis].constraints:
                a, b = vals.get(k.a), vals.get(k.b)
                if a is None or b is None:
                    continue
                d = a - b
                if k.lo is not None and d < k.lo or k.hi is not None and d > k.hi:
                    return self._f(f'{p.name}: нарушено ограничение {k.a} - {k.b} in [{k.lo}, {k.hi}] (было {d})')
        cells, ctx, expect, ctx_expect = [], [], [], []
        for c, b in placed:
            if c.inner:
                cells += b.cells
                expect += b.expect
            else:
                ctx += b.cells
                ctx_expect += b.expect
            ctx += b.ctx
            ctx_expect += b.ctx_expect
        merged = _merge_ctx(ctx, ctx_expect)
        if merged is None:
            return self._f(f'{p.name}: контекст разных паттернов пересёкся')
        ctx, ctx_expect = merged
        if Block._pts(ctx) & Block._pts(cells):
            return self._f(f'{p.name}: слитый контекст наехал на содержимое')
        return Block(box, cells, expect + [(p.name, box)], ctx, ctx_expect)

    def _place(self, name: str, w: int, h: int, xcl, ycl, bound: dict[str, int], first: bool, spread: int = 2):
        if first:
            return (0, 0)
        res = []
        for axis, cl, lo_e, hi_e, size in (('x', xcl, 'left', 'right', w), ('y', ycl, 'top', 'bottom', h)):
            a = window_for(cl, bound, f'{name}.{lo_e}')
            b = window_for(cl, bound, f'{name}.{hi_e}')
            lo = max(a[0], b[0] - size)
            hi = min(a[1], b[1] - size)
            if lo > hi:
                return None
            if lo == -INF and hi == INF:
                lo, hi = -size - spread, size + 2 * spread
            elif lo == -INF:
                lo = hi - 2 * spread
            elif hi == INF:
                hi = lo + 2 * spread
            res.append(self.rng.randint(int(lo), int(min(hi, lo + 2 * spread + 1))))
        return tuple(res)

    def _gen_array(self, p: PatternIR, depth: int) -> Block | None:
        arr = p.array
        if arr is None or not arr.item_pattern:
            return None
        direction = arr.direction
        if direction in ('fill', 'auto'):
            direction = self.rng.choice(['row', 'column']) if direction == 'auto' else 'row'
        n_lo = max(arr.item_count.start or 1, 1)
        n_hi = arr.item_count.stop if arr.item_count.stop is not None else n_lo + 2
        n = self.rng.randint(n_lo, max(n_lo, min(n_hi, n_lo + 2)))
        g_lo = arr.gap.start or 0
        g_hi = arr.gap.stop if arr.gap.stop is not None else g_lo + 3
        # Вложенные массивы нужно разделять зазором шире внутреннего, иначе сама грамматика неоднозначна
        # (внутренние массивы слипнутся в один).
        for member in self.ir.choice_set(arr.item_pattern):
            inner = self.ir[member].array
            if inner is not None and inner.direction in ('fill', 'auto', direction):
                inner_hi = inner.gap.stop if inner.gap.stop is not None else (inner.gap.start or 0) + 1
                if g_hi >= inner_hi + 1:
                    g_lo = max(g_lo, inner_hi + 1)
        g_hi = max(g_hi, g_lo)
        a0, a1, c0, c1 = (0, 2, 1, 3) if direction == 'row' else (1, 3, 0, 2)
        items: list[Block] = []
        own_occ: set[tuple[int, int]] = set()
        ctx_occ: set[tuple[int, int]] = set()
        cursor = 0
        cross = None
        for i in range(n):
            blk = None
            for _ in range(15):
                cand = self.gen(arr.item_pattern, depth + 1)
                if cand is None:
                    continue
                size = cand.box[c1] - cand.box[c0]
                if cross is None or size == cross or arr.align != 'both':
                    blk = cand
                    break
            if blk is None:
                return self._f(f'{p.name}: не удалось породить элемент `{arr.item_pattern}` нужного размера')
            if cross is None:
                cross = blk.box[c1] - blk.box[c0]
            gap = 0 if i == 0 else self.rng.randint(g_lo, min(g_hi, g_lo + 1))
            start = cursor + gap
            d = [0, 0]
            d[0 if direction == 'row' else 1] = start - blk.box[a0]
            if arr.align == 'end':
                d[1 if direction == 'row' else 0] = cross - blk.box[c1]  # общий конец поперёк
            else:
                d[1 if direction == 'row' else 0] = -blk.box[c0]
            blk = blk.shifted(d[0], d[1])
            new_own, new_ctx = blk.own_points(), blk.ctx_points()
            if new_own & (own_occ | ctx_occ) or new_ctx & own_occ:
                return self._f(f'{p.name}: элементы массива пересеклись')
            own_occ |= new_own
            ctx_occ |= new_ctx
            cursor = blk.box[a1]
            items.append(blk)
        box = (min(b.box[0] for b in items), min(b.box[1] for b in items),
               max(b.box[2] for b in items), max(b.box[3] for b in items))
        if p.size is not None and not ((box[2] - box[0]) in p.size[0] and (box[3] - box[1]) in p.size[1]):
            return self._f(f'{p.name}: размер массива {box[2] - box[0]}x{box[3] - box[1]} вне `size`')
        cells = [x for b in items for x in b.cells]
        merged = _merge_ctx([x for b in items for x in b.ctx], [x for b in items for x in b.ctx_expect])
        if merged is None:
            return self._f(f'{p.name}: контекст разных паттернов пересёкся')
        ctx, ctx_expect = merged
        if Block._pts(ctx) & Block._pts(cells):
            return self._f(f'{p.name}: слитый контекст наехал на элементы массива')
        expect = [x for b in items for x in b.expect] + [(p.name, box)]
        return Block(box, cells, expect, ctx, ctx_expect)


def build_grid(block: Block) -> Grid:
    """Собрать сетку (с объединёнными ячейками) из блока со смещением в положительную область."""
    l, t, _, _ = block.extent()
    grid = Grid()
    for x, y, w, h, text in block.all_cells:
        grid.register_cell(Cell(grid, Point(x - l + 1, y - t + 1), Size(w, h), content=text))
    return grid


def generate_case(ir: GrammarIR, pattern: str, seed: int, attempts: int = 30,
                  fuzzer: Fuzzer | None = None) -> FuzzCase | None:
    """Порождает одну таблицу для `pattern` (или None, если не удалось уложиться в ограничения)."""
    fz = fuzzer or Fuzzer(ir, random.Random(seed))
    fz.rng = random.Random(seed)
    for _ in range(attempts):
        fz.budget = 1500
        block = fz.gen(pattern)
        if block is not None:
            l, t, _, _ = block.extent()
            block = block.shifted(1 - l, 1 - t)  # те же сдвиги, что в build_grid
            return FuzzCase(seed, pattern, block, build_grid(block))
    return None


def check_case(ir: GrammarIR, case: FuzzCase) -> list[str]:
    """Прогоняет движок на порождённой таблице; возвращает список расхождений."""
    saved = ir.root_name
    ir.root_name = case.pattern
    try:
        res = Engine(ir, strict_cell_size=True).run(case.grid)
    finally:
        ir.root_name = saved
    found: dict[str, set] = defaultdict(set)
    for name, ms in res.matches.items():
        found[name] = {m.box for m in ms}
    problems = []
    # целевой паттерн обязан найтись, внутренности проверяем, где паттерн вообще искали
    def present(name: str, box: RectT) -> bool:
        names = set(ir.choice_set(name)) | {name}
        for n in names:
            if box in found.get(n, ()):
                return True
            # массив может законно оказаться шире ожидаемого (слипшиеся соседи, `fill`)
            if ir[n].kind is PKind.ARRAY and any(
                    f[0] <= box[0] and f[1] <= box[1] and f[2] >= box[2] and f[3] >= box[3] for f in found.get(n, ())):
                return True
        return False

    top_name, top_box = case.block.expect[-1]
    if not present(case.pattern, top_box):
        problems.append(f'не найден `{case.pattern}` в {top_box}')
    for name, box in case.block.expect[:-1] + case.block.ctx_expect:
        if any(n in found for n in set(ir.choice_set(name)) | {name}) and not present(name, box):
            problems.append(f'не найден `{name}` в {box}')
    return problems


def run_fuzz(grammar_path: str, *, seed: int = 0, count: int = 20, pattern: str | None = None) -> int:
    """CLI-вход: `fuzz GRAMMAR --seed N --count N [--pattern P]`."""
    from vstuxls.grammar2d.compiler import compile_grammar

    res = compile_grammar(grammar_path, lexical=False, ambiguity=False, geometry=False)
    ir = res.ir
    target = pattern or ir.root_name
    if not target or target not in ir:
        print('не указан паттерн для генерации (в грамматике нет корня)')
        return 2
    ok = failed = ungenerated = 0
    fz = Fuzzer(ir, random.Random(seed))
    for i in range(count):
        case = generate_case(ir, target, seed * 100003 + i, fuzzer=fz)
        if case is None:
            ungenerated += 1
            continue
        problems = check_case(ir, case)
        if problems:
            failed += 1
            print(f'--- seed {case.seed}: расхождения ({len(problems)}):')
            for pr in problems[:5]:
                print('   ', pr)
            print(case.render())
        else:
            ok += 1
    print(f'итого: {ok} прошло, {failed} расхождений, {ungenerated} не удалось породить из {count}')
    if ungenerated:
        print('основные причины неудач порождения:')
        for reason, n in fz.fails.most_common(8):
            print(f'  {n:5d}  {reason}')
    for pr in fz.problems:
        print('  !', pr)
    return 0 if failed == 0 and ok > 0 else 1
