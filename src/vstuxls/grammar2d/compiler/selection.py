"""Слой политики во время выполнения: выбор из конкурирующих совпадений.

Матчер строит *все согласованные* совпадения (структура). Здесь, отдельно, применяются:

* `priority` / `prefer` — между кандидатами **разных** паттернов одной точки выбора, если они перекрываются;
* `overlap` — между кандидатами (режимы `full` — вложение с общим началом, `partial` — любое перекрытие),
  критерии `area|width|height|precision` + `max|min`, по порядку;
* `exclusive_candidates` — может ли совпадение паттерна перекрываться с другими в одном разборе
  (см. `can_overlap`);
* глобальный выбор корней и покрытие: `select_roots`, `coverage`.
"""

from __future__ import annotations

from dataclasses import dataclass

from vstuxls.grammar2d.compiler.ir import GrammarIR


def area_of(box) -> int:
    return (box[2] - box[0]) * (box[3] - box[1])


def overlaps(a, b) -> bool:
    """Строгое перекрытие (общая площадь > 0); касание не считается."""
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def contains(outer, inner) -> bool:
    return outer[0] <= inner[0] and outer[1] <= inner[1] and inner[2] <= outer[2] and inner[3] <= outer[3]


def _metric(m, metric: str) -> float:
    b = m.box
    if metric == 'area':
        return float(area_of(b))
    if metric == 'width':
        return float(b[2] - b[0])
    if metric == 'height':
        return float(b[3] - b[1])
    return float(m.precision)


def compare(m1, m2, criteria: list[tuple[str, str]]) -> int:
    """-1: m1 хуже, 1: m1 лучше, 0: равны по всем критериям."""
    for metric, order in criteria:
        v1, v2 = _metric(m1, metric), _metric(m2, metric)
        if v1 == v2:
            continue
        better = v1 > v2 if order == 'max' else v1 < v2
        return 1 if better else -1
    return 0


def resolve_overlaps(matches: list, mode: str, criteria: list[tuple[str, str]]) -> list:
    """Разрешение накладок (семантика `overlap`)."""
    if mode == 'none' or len(matches) < 2:
        return list(matches)
    dead: set[int] = set()
    n = len(matches)
    for i in range(n):
        if i in dead:
            continue
        for j in range(i + 1, n):
            if j in dead or i in dead:
                continue
            a, b = matches[i], matches[j]
            if mode == 'full':
                hit = (a.box[0], a.box[1]) == (b.box[0], b.box[1]) and (contains(a.box, b.box) or contains(b.box, a.box))
            else:  # partial
                hit = overlaps(a.box, b.box)
            if not hit:
                continue
            c = compare(a, b, criteria)
            if c < 0:
                dead.add(i)
            elif c > 0:
                dead.add(j)
    return [m for k, m in enumerate(matches) if k not in dead]


def apply_priorities(ir: GrammarIR, matches: list) -> list:
    """Вытеснение между разными паттернами: выше `priority` или `prefer`, если боксы перекрываются."""
    if len(matches) < 2:
        return list(matches)
    pols = {}
    for m in matches:
        pols.setdefault(m.pattern, ir[m.pattern].policy)
    if len({p.priority for p in pols.values()}) <= 1 and not any(p.prefer for p in pols.values()):
        return list(matches)
    out = []
    for m in matches:
        pm = pols[m.pattern]
        beaten = False
        for o in matches:
            if o is m or o.pattern == m.pattern or not overlaps(o.box, m.box):
                continue
            po = pols[o.pattern]
            if po.priority > pm.priority or m.pattern in po.prefer and o.pattern not in pm.prefer:
                beaten = True
                break
        if not beaten:
            out.append(m)
    return out


def can_overlap(ir: GrammarIR, pattern_names: list[str]) -> bool:
    """Могут ли совпадения этих паттернов перекрываться в одном разборе (`allows_overlapping`)."""
    return bool(pattern_names) and all(not ir[n].policy.exclusive_candidates for n in pattern_names)


# --------------------------------------------------------------------------- дерево разбора

def leaf_boxes(match) -> list:
    """Рамки листьев (терминалов) дерева разбора; кэшируется в совпадении."""
    cached = match.leaves
    if cached is None:
        cached = [leaf.box for leaf in iter_leaves(match)]
        match.leaves = cached
    return cached


def occupies_overlap(a, b) -> bool:
    """Физическое пересечение: общие ячейки у листьев (массивы с «дырами» не конфликтуют рамками)."""
    if not overlaps(a.box, b.box):
        return False
    for x in leaf_boxes(a):
        for y in leaf_boxes(b):
            if overlaps(x, y):
                return True
    return False


def iter_leaves(match):
    """Листовые совпадения (терминалы) дерева разбора."""
    stack = [match]
    seen: set[int] = set()
    while stack:
        m = stack.pop()
        if id(m) in seen:
            continue
        seen.add(id(m))
        if m.children:
            stack.extend(m.children.values())
        else:
            yield m


@dataclass
class Coverage:
    covered_cells: int
    total_cells: int
    uncovered: list  # [(box, text)]

    @property
    def ratio(self) -> float:
        return self.covered_cells / self.total_cells if self.total_cells else 1.0


def coverage(match, cells: list) -> Coverage:
    """Доля непустых ячеек документа внутри рамки корня, использованных листьями дерева разбора."""
    used = {leaf.box for leaf in iter_leaves(match)}
    inside = [c for c in cells if contains(match.box, c[0])]
    uncovered = [(b, t) for b, t in inside if b not in used and t.strip()]
    nonempty = [c for c in inside if c[1].strip()]
    return Coverage(len(nonempty) - len(uncovered), len(nonempty), uncovered)


def select_roots(matches: list) -> list:
    """Глобальный выбор корней: сначала лучшие по точности и охвату; без фильтрации накладок.

    Для одной и той же рамки остаётся только лучший разбор (альтернативные разборы
    доступны в `EngineResult.matches`)."""
    seen: set = set()
    out = []
    for m in sorted(matches, key=lambda m: (-m.precision, -area_of(m.box), m.box)):
        if (m.pattern, m.box) in seen:
            continue
        seen.add((m.pattern, m.box))
        out.append(m)
    return out
