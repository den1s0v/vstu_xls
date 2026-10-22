"""Линтер v1: структурные проверки IR (ссылки, циклы, достижимость, продуктивность, типы ячеек)."""

from __future__ import annotations

from vstuxls.grammar2d.compiler.diagnostics import DiagnosticReport, Severity
from vstuxls.grammar2d.compiler.ir import GrammarIR, PatternIR, PKind


def lint(ir: GrammarIR, report: DiagnosticReport) -> None:
    """Выполнить все структурные проверки. Диагностики добавляются в `report`."""
    _check_references(ir, report)
    _check_extends_cycles(ir, report)
    _check_dependency_cycles(ir, report)
    _infer_or_check_root(ir, report)
    _check_cell_types(ir, report)
    _check_relations(ir, report)
    _check_productivity(ir, report)
    _check_reachability(ir, report)
    _check_similar_components(ir, report)
    _check_abstract(ir, report)
    _check_negative_weights(ir, report)


# --------------------------------------------------------------------------- ссылки

def _check_references(ir: GrammarIR, report: DiagnosticReport) -> None:
    for p in ir:
        for base in p.extends:
            if base not in ir:
                report.add('G002', f'`extends` ссылается на неизвестный паттерн `{base}`', pattern=p.name,
                           loc=p.loc, hint=_did_you_mean(base, ir))
        for c in p.components:
            if c.pattern and c.pattern not in ir:
                report.add('G002', f'компонент ссылается на неизвестный паттерн `{c.pattern}`', pattern=p.name,
                           component=c.name, loc=c.loc, hint=_did_you_mean(c.pattern, ir))
        if p.array and p.array.item_pattern and p.array.item_pattern not in ir:
            report.add('G002', f'`item_pattern` ссылается на неизвестный паттерн `{p.array.item_pattern}`',
                       pattern=p.name, loc=p.loc, hint=_did_you_mean(p.array.item_pattern, ir))
        for m in p.one_of:
            if m not in ir:
                report.add('G002', f'`one_of` ссылается на неизвестный паттерн `{m}`', pattern=p.name, loc=p.loc,
                           hint=_did_you_mean(m, ir))
        for target in p.policy.prefer:
            if target not in ir:
                report.add('POL002', f'`prefer` ссылается на неизвестный паттерн `{target}`', pattern=p.name,
                           loc=p.policy.loc)


def _did_you_mean(name: str, ir: GrammarIR) -> str | None:
    import difflib
    m = difflib.get_close_matches(name, list(ir.patterns), n=1, cutoff=0.7)
    return f'возможно, имелось в виду `{m[0]}`' if m else None


# --------------------------------------------------------------------------- циклы

def _sccs(graph: dict[str, list[str]]) -> list[list[str]]:
    """Алгоритм Тарьяна (итеративно); возвращает компоненты сильной связности."""
    index: dict[str, int] = {}
    low: dict[str, int] = {}
    on_stack: set[str] = set()
    stack: list[str] = []
    result: list[list[str]] = []
    counter = 0

    for root in graph:
        if root in index:
            continue
        work = [(root, iter(graph.get(root, ())))]
        index[root] = low[root] = counter
        counter += 1
        stack.append(root)
        on_stack.add(root)
        while work:
            node, it = work[-1]
            advanced = False
            for nxt in it:
                if nxt not in graph:
                    continue
                if nxt not in index:
                    index[nxt] = low[nxt] = counter
                    counter += 1
                    stack.append(nxt)
                    on_stack.add(nxt)
                    work.append((nxt, iter(graph.get(nxt, ()))))
                    advanced = True
                    break
                if nxt in on_stack:
                    low[node] = min(low[node], index[nxt])
            if advanced:
                continue
            work.pop()
            if work:
                low[work[-1][0]] = min(low[work[-1][0]], low[node])
            if low[node] == index[node]:
                comp = []
                while True:
                    w = stack.pop()
                    on_stack.discard(w)
                    comp.append(w)
                    if w == node:
                        break
                result.append(sorted(comp))
    return result


def _find_cycle_path(graph: dict[str, list[str]], members: set[str]) -> list[str]:
    start = sorted(members)[0]
    path = [start]
    seen = {start}
    cur = start
    while True:
        nxt = next((n for n in graph.get(cur, ()) if n in members and (n == start or n not in seen)), None)
        if nxt is None:
            return path
        if nxt == start:
            return path + [start]
        path.append(nxt)
        seen.add(nxt)
        cur = nxt


def _check_extends_cycles(ir: GrammarIR, report: DiagnosticReport) -> None:
    graph = {n: [b for b in p.extends if b in ir] for n, p in ir.patterns.items()}
    for comp in _sccs(graph):
        if len(comp) > 1 or comp[0] in graph.get(comp[0], ()):
            path = _find_cycle_path(graph, set(comp))
            report.add('G012', 'циклическое наследование: ' + ' -> '.join(path), pattern=comp[0],
                       loc=ir[comp[0]].loc)


def _check_dependency_cycles(ir: GrammarIR, report: DiagnosticReport) -> None:
    graph = {n: ir.dependencies(n) for n in ir.patterns}
    for comp in _sccs(graph):
        if len(comp) > 1 or comp[0] in graph.get(comp[0], ()):
            path = _find_cycle_path(graph, set(comp))
            report.add('G003', 'циклическая зависимость: ' + ' -> '.join(path), pattern=comp[0],
                       loc=ir[comp[0]].loc,
                       hint='паттерн не может прямо или косвенно содержать сам себя; '
                            'для вложенных структур используйте kind: array')


# --------------------------------------------------------------------------- корень

def _infer_or_check_root(ir: GrammarIR, report: DiagnosticReport) -> None:
    if ir.root_name:
        return
    if not ir.patterns:
        report.add('G010', 'в грамматике нет паттернов')
        return
    used: set[str] = set()
    for p in ir:
        used.update(r for r in p.referenced() if r in ir)
    top = sorted(n for n in ir.patterns if n not in used and not ir[n].is_inline
                 and not any(n in ir[e].extends for e in ir.patterns))
    # Расширяющие паттерны, у которых есть база, не считаем вершинами:
    top = [n for n in top if not ir[n].extends]
    if len(top) == 1:
        ir.root_name = top[0]
        report.add('G010', f'корень не объявлен; выведен автоматически: `{top[0]}`', severity=Severity.INFO,
                   pattern=top[0], hint='добавьте `root: true` к паттерну или `root: <имя>` в корень файла')
    else:
        report.add('G010', f'корень не объявлен и не выводится однозначно; кандидаты: {top}',
                   hint='добавьте `root: true` к паттерну или `root: <имя>` в корень файла')


# --------------------------------------------------------------------------- типы ячеек

def _check_cell_types(ir: GrammarIR, report: DiagnosticReport) -> None:
    used: set[str] = set()
    for p in ir:
        if p.kind is PKind.CELL and p.content_type:
            if p.content_type not in ir.cell_types:
                report.add('G008', f'неизвестный content_type `{p.content_type}`', pattern=p.name, loc=p.loc,
                           hint=_did_you_mean_ct(p.content_type, ir))
            else:
                used.add(p.content_type)
    # Тип, на который ссылается `except` другого типа, тоже считается используемым.
    for ct in ir.cell_types.values():
        used.update(t for t in ct.except_types if t in ir.cell_types)
    for name, ct in ir.cell_types.items():
        if name not in used:
            report.add('G007', f'тип ячейки `{name}` не используется ни одним терминалом', loc=ct.loc)
        for t in ct.except_types:
            if t not in ir.cell_types:
                report.add('G008', f'`except` типа `{name}` ссылается на неизвестный тип `{t}`', loc=ct.loc)


def _did_you_mean_ct(name: str, ir: GrammarIR) -> str | None:
    import difflib
    m = difflib.get_close_matches(name, list(ir.cell_types), n=1, cutoff=0.7)
    return f'возможно, имелось в виду `{m[0]}`' if m else None


# --------------------------------------------------------------------------- отношения

def _check_relations(ir: GrammarIR, report: DiagnosticReport) -> None:
    for p in ir:
        names = {c.name for c in p.components} | {'this'}
        for rel in p.relations:
            for ref in (rel.a, rel.b):
                if ref.comp not in names:
                    report.add('G006', f'отношение `{rel.text}`: неизвестный компонент `{ref.comp}`',
                               pattern=p.name, loc=rel.loc,
                               hint='допустимые имена: ' + ', '.join(sorted(names)))


# --------------------------------------------------------------------------- продуктивность

def productive_patterns(ir: GrammarIR) -> set[str]:
    """Паттерны, которые теоретически могут совпасть (наименьшая неподвижная точка)."""
    productive: set[str] = set()
    changed = True

    def ref_ok(name: str | None) -> bool:
        return bool(name) and any(x in productive for x in ir.choice_set(name))

    while changed:
        changed = False
        for p in ir:
            if p.name in productive or not p.is_concrete and p.kind is not PKind.ALT:
                continue
            ok = False
            if p.kind is PKind.CELL:
                ok = bool(p.content_type) and p.content_type in ir.cell_types
            elif p.kind is PKind.AREA:
                required = [c for c in p.components if c.must_exist]
                ok = bool(p.components) and all(ref_ok(c.pattern) for c in required)
            elif p.kind.is_array:
                ok = bool(p.array and p.array.item_pattern) and ref_ok(p.array.item_pattern)
            elif p.kind is PKind.ALT:
                ok = any(ref_ok(m) for m in p.one_of)
            if ok:
                productive.add(p.name)
                changed = True
    return productive


def _check_productivity(ir: GrammarIR, report: DiagnosticReport) -> None:
    productive = productive_patterns(ir)
    for p in ir:
        if p.kind is PKind.GENERAL:
            continue
        if p.name not in productive:
            reason = _unproductive_reason(ir, p, productive)
            report.add('G014', f'паттерн не может совпасть: {reason}', pattern=p.name, loc=p.loc)
            continue
        if p.kind is PKind.AREA:
            inner_required = [c for c in p.components if c.inner and c.must_exist]
            if not inner_required:
                report.add('G014', 'у области нет обязательных внутренних компонентов: '
                                   'её рамка определяется только необязательными',
                           severity=Severity.WARNING, pattern=p.name, loc=p.loc,
                           hint='сделайте хотя бы один внутренний компонент обязательным')


def _unproductive_reason(ir: GrammarIR, p: PatternIR, productive: set[str]) -> str:
    if p.kind is PKind.CELL:
        return f'неизвестный тип ячейки `{p.content_type}`'
    if p.kind is PKind.AREA:
        bad = [c.name for c in p.components if c.must_exist and not any(x in productive for x in ir.choice_set(c.pattern or ''))]
        return 'обязательные компоненты без возможных совпадений: ' + ', '.join(bad or ['(нет компонентов)'])
    if p.kind.is_array:
        return f'элемент `{p.array.item_pattern if p.array else None}` не может совпасть'
    if p.kind is PKind.ALT:
        return 'ни одна из альтернатив не может совпасть'
    return 'нет возможных реализаций'


# --------------------------------------------------------------------------- достижимость

def reachable_patterns(ir: GrammarIR) -> set[str]:
    if not ir.root_name or ir.root_name not in ir:
        return set(ir.patterns)
    seen: set[str] = set()
    stack = [ir.root_name]
    while stack:
        n = stack.pop()
        if n in seen or n not in ir:
            continue
        seen.add(n)
        stack.extend(ir[n].referenced())
        stack.extend(ir.direct_extenders(n))
    return seen


def _check_reachability(ir: GrammarIR, report: DiagnosticReport) -> None:
    if ir.target_mode == 'all' or not ir.root_name or ir.root_name not in ir:
        return
    seen = reachable_patterns(ir)
    for p in ir:
        if p.name not in seen and not p.is_inline:
            report.add('G004', 'паттерн не используется: до него нельзя дойти от корня', pattern=p.name, loc=p.loc,
                       hint='удалите его или подключите в грамматику (в режиме `root` он всё равно будет искаться)')


# --------------------------------------------------------------------------- прочее

def _check_similar_components(ir: GrammarIR, report: DiagnosticReport) -> None:
    for p in ir:
        seen: dict[tuple, str] = {}
        for c in p.components:
            if c.group:  # развёрнутый count — намеренно одинаковые
                continue
            loc = c.effective_location()
            key = (c.pattern, c.role,
                   tuple(sorted((s, str(r)) for s, r in loc.padding.items())),
                   tuple(sorted((s, str(r)) for s, r in loc.margin.items())))
            if key in seen:
                report.add('G011', f'компонент идентичен `{seen[key]}` (тот же паттерн и расположение)',
                           pattern=p.name, component=c.name, loc=c.loc,
                           hint='если нужно несколько однотипных элементов, используйте `count` или kind: array; '
                                'совпадения таких компонентов упорядочиваются по позиции')
            else:
                seen[key] = c.name


def _check_abstract(ir: GrammarIR, report: DiagnosticReport) -> None:
    for p in ir:
        if p.kind is PKind.GENERAL and not ir.extenders(p.name):
            report.add('G013', 'абстрактный (`general`) паттерн, который никто не расширяет, не может совпасть',
                       pattern=p.name, loc=p.loc)


def _check_negative_weights(ir: GrammarIR, report: DiagnosticReport) -> None:
    for p, c in ir.iter_components():
        if c.weight < 0:
            report.add('POL004', f'отрицательный вес ({c.weight}) используется для проверки отсутствия',
                       pattern=p.name, component=c.name, loc=c.loc,
                       hint='в DSL v2 это выражается явно: секция `forbid` (отрицательный предикат)')
