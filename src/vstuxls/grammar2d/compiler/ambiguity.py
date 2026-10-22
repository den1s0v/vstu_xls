"""Анализ неоднозначности и слой политики.

*Структура* грамматики описывает множество допустимых разборов; *политика* выбирает из него.
Здесь проверяется, что там, где разбор может быть неоднозначен, правило выбора задано явно.

Точка выбора — паттерн, на месте которого могут стоять несколько конкретных паттернов
(`general` с `extends`, `alt`/`one_of`, либо конкретный паттерн, у которого есть расширения).
Пара альтернатив *потенциально неоднозначна*, если их вычисленные размеры пересекаются по обеим осям и у них
есть общий обязательный терминал (тот же тип ячейки или типы, имеющие общие строки).
Это эвристика-предупреждение: доказать взаимную исключаемость в общем случае нельзя.

Правило выбора считается заданным, если у альтернатив разные `priority`, одна вытесняет другую (`prefer`),
либо у точки выбора включено разрешение накладок (`overlap`, режим не `none`).

Диагностики: AMB001 (правила нет), AMB002 (правило есть — информация), POL001 (`allows_overlapping`),
POL005 (цикл в `prefer`).
"""

from __future__ import annotations

from vstuxls.grammar2d.compiler.diagnostics import DiagnosticReport, Severity
from vstuxls.grammar2d.compiler.geometry import GeometryAnalyzer
from vstuxls.grammar2d.compiler.ir import GrammarIR, PatternIR, PKind


def leaf_signature(ir: GrammarIR, name: str, memo: dict[str, frozenset[str]] | None = None,
                   _active: set[str] | None = None) -> frozenset[str]:
    """Типы ячеек обязательных терминалов, достижимых из паттерна."""
    memo = memo if memo is not None else {}
    _active = _active if _active is not None else set()
    if name in memo:
        return memo[name]
    if name in _active or name not in ir:
        return frozenset()
    _active.add(name)
    p = ir[name]
    sig: set[str] = set()
    if p.kind is PKind.CELL:
        if p.content_type:
            sig.add(p.content_type)
    elif p.kind is PKind.AREA:
        for c in p.components:
            if c.must_exist and c.pattern:
                for m in ir.choice_set(c.pattern):
                    sig |= leaf_signature(ir, m, memo, _active)
    elif p.kind.is_array and p.array and p.array.item_pattern:
        for m in ir.choice_set(p.array.item_pattern):
            sig |= leaf_signature(ir, m, memo, _active)
    else:
        for m in ir.choice_set(name):
            if m != name:
                sig |= leaf_signature(ir, m, memo, _active)
    _active.discard(name)
    res = frozenset(sig)
    memo[name] = res
    return res


def _types_related(ir: GrammarIR, a: frozenset[str], b: frozenset[str]) -> bool:
    if a & b:
        return True
    return any(frozenset((x, y)) in ir.lexical_conflicts for x in a for y in b)


def _distinguished(ir: GrammarIR, a: frozenset[str], b: frozenset[str]) -> bool:
    """Ветка требует тип ячейки, который другая ветка не может содержать (и наоборот): наборы ячеек различны."""
    def alone(x: str, other: frozenset[str]) -> bool:
        return all(x != y and frozenset((x, y)) not in ir.lexical_conflicts for y in other)

    return any(alone(x, b) for x in a) or any(alone(y, a) for y in b)


def _choice_points(ir: GrammarIR) -> list[PatternIR]:
    out = []
    for p in ir:
        members = list(ir.choice_set(p.name))
        if len(members) >= 2 and (p.kind in (PKind.GENERAL, PKind.ALT) or ir.direct_extenders(p.name)):
            out.append(p)
    return out


def resolution_of(ir: GrammarIR, point: PatternIR, a: str, b: str) -> str | None:
    """Чем разрешается конфликт `a` vs `b` в точке выбора (None, если ничем)."""
    pa, pb = ir[a].policy, ir[b].policy
    if pa.priority != pb.priority:
        return f'priority ({a}: {pa.priority}, {b}: {pb.priority})'
    if b in pa.prefer or a in pb.prefer:
        winner, loser = (a, b) if b in pa.prefer else (b, a)
        return f'prefer ({winner} вытесняет {loser})'
    for owner in (point, ir[a], ir[b]):
        ov = owner.policy.overlap
        if ov is not None and ov.decides():
            crit = ', '.join(f'{m}-{o}' for m, o in ov.criteria)
            return f'overlap {ov.mode} у `{owner.name}` ({crit})'
    return None


def analyze_ambiguity(ir: GrammarIR, report: DiagnosticReport) -> None:
    ga = GeometryAnalyzer(ir, DiagnosticReport())
    ga.run()
    memo: dict[str, frozenset[str]] = {}

    for point in _choice_points(ir):
        members = [m for m in ir.choice_set(point.name) if m in ir]
        unresolved: list[tuple[str, str, frozenset[str]]] = []
        resolved: list[tuple[str, str, str]] = []
        for i, a in enumerate(members):
            for b in members[i + 1:]:
                ia, ib = ga.analyze(ir[a]), ga.analyze(ir[b])
                if ia.w.intersect(ib.w) is None or ia.h.intersect(ib.h) is None:
                    continue  # размеры несовместимы: одновременно совпасть не могут
                sa, sb = leaf_signature(ir, a, memo), leaf_signature(ir, b, memo)
                if not _types_related(ir, sa, sb):
                    continue
                if _distinguished(ir, sa, sb):
                    continue  # одной и той же группой ячеек обе ветки быть не могут
                how = resolution_of(ir, point, a, b)
                if how is None:
                    shared = sa & sb or frozenset(sorted(sa | sb)[:2])
                    unresolved.append((a, b, shared))
                else:
                    resolved.append((a, b, how))
        if unresolved:
            pairs = ', '.join(f'`{a}`~`{b}`' for a, b, _ in unresolved[:6])
            more = f' и ещё {len(unresolved) - 6}' if len(unresolved) > 6 else ''
            a, b, shared = unresolved[0]
            report.add(
                'AMB001',
                f'альтернативы в `{point.name}` могут совпасть на одном месте, правило выбора не задано: {pairs}{more}',
                pattern=point.name, loc=point.loc,
                witness=f'`{a}` и `{b}` имеют общие обязательные типы ячеек: {sorted(shared)}; '
                        f'размеры пересекаются',
                hint='задайте `priority` или `prefer` в политике альтернатив, либо `overlap` у точки выбора; '
                     'если ветки различаются структурой — добавьте различающий `require`/`forbid` или `size`',
            )
        if resolved:
            how = '; '.join(sorted({h for _, _, h in resolved}))
            report.add('AMB002', f'в `{point.name}` {len(resolved)} пар(ы) альтернатив пересекаются, '
                                 f'конфликт разрешается: {how}',
                       pattern=point.name, loc=point.loc, severity=Severity.INFO)

    _check_policies(ir, report)


def _check_policies(ir: GrammarIR, report: DiagnosticReport) -> None:
    for p in ir:
        pol = p.policy
        if not pol.exclusive_candidates:
            extra = ' (при этом `overlap` задан, но не применяется к самому паттерну)' \
                if pol.overlap is not None and pol.overlap.decides() else ''
            report.add('POL001', 'фильтрация накладывающихся кандидатов отключена (`allows_overlapping`): '
                                 f'конфликт откладывается до родителя{extra}',
                       pattern=p.name, loc=pol.loc if pol.loc else p.loc,
                       hint='если кандидаты действительно могут перекрываться (напр., элементы разных строк '
                            'массива), опишите это массивом/alt; иначе включите `overlap` и уберите флаг')
    # циклы в prefer
    graph = {n: [t for t in p.policy.prefer if t in ir] for n, p in ir.patterns.items()}
    from vstuxls.grammar2d.compiler.lint import _find_cycle_path, _sccs
    for comp in _sccs(graph):
        if len(comp) > 1 or comp[0] in graph.get(comp[0], ()):
            path = _find_cycle_path(graph, set(comp))
            report.add('POL005', 'prefer образует цикл: ' + ' -> '.join(path), pattern=comp[0],
                       loc=ir[comp[0]].policy.loc or ir[comp[0]].loc)


# --------------------------------------------------------------------------- слой политики

def policies_to_dict(ir: GrammarIR) -> dict[str, dict]:
    """Политики всех паттернов (только отличающиеся от умолчаний) — для секции `policies:`."""
    out: dict[str, dict] = {}
    for p in ir:
        pol = p.policy
        d: dict = {}
        if pol.confidence != 1.0:
            d['confidence'] = pol.confidence
        if pol.precision_threshold is not None:
            d['precision_threshold'] = pol.precision_threshold
        if pol.overlap is not None:
            d['overlap'] = {'mode': pol.overlap.mode,
                            'resolution': [f'{m}-{o}' for m, o in pol.overlap.criteria]}
        if not pol.exclusive_candidates:
            d['exclusive'] = False
        if pol.priority:
            d['priority'] = pol.priority
        if pol.prefer:
            d['prefer'] = list(pol.prefer)
        if pol.cost is not None:
            d['cost'] = pol.cost
        if d:
            out[p.name] = d
    return out


def policies_to_yaml(ir: GrammarIR) -> str:
    """Текст секции `policies:` — для переноса политики из паттернов в отдельный слой."""
    import yaml
    data = policies_to_dict(ir)
    return yaml.safe_dump({'policies': data}, allow_unicode=True, sort_keys=False, default_flow_style=False)
