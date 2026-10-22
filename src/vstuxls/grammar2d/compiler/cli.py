"""Командная строка компилятора грамматики.

    python -m vstuxls.grammar2d.compiler check cnf/grammar_root.yml [--json] [--strict] [--no-lexical] ...
    python -m vstuxls.grammar2d.compiler explain cnf/grammar_root.yml PATTERN
    python -m vstuxls.grammar2d.compiler fuzz cnf/grammar_root.yml [--seed N] [--count N]
"""

from __future__ import annotations

import argparse
import json
import sys

from vstuxls.grammar2d.compiler import compile_grammar
from vstuxls.grammar2d.compiler.diagnostics import Severity


def _build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog='vstuxls-grammar', description='Компилятор и анализатор 2D-грамматик')
    sub = ap.add_subparsers(dest='cmd', required=True)

    chk = sub.add_parser('check', help='статический анализ грамматики')
    chk.add_argument('grammar')
    chk.add_argument('--json', action='store_true', help='вывести диагностики в JSON')
    chk.add_argument('--strict', action='store_true', help='считать предупреждения ошибками (код возврата 1)')
    chk.add_argument('--min-severity', choices=['info', 'warning', 'error'], default='info')
    chk.add_argument('--no-geometry', action='store_true')
    chk.add_argument('--no-lexical', action='store_true')
    chk.add_argument('--no-ambiguity', action='store_true')

    exp = sub.add_parser('explain', help='вывести неявные границы и ограничения паттерна')
    exp.add_argument('grammar')
    exp.add_argument('pattern')

    pol = sub.add_parser('policies', help='вывести политики паттернов как отдельную секцию `policies:`')
    pol.add_argument('grammar')

    df = sub.add_parser('diff', help='сравнить старый матчер и новый движок на таблице')
    df.add_argument('grammar')
    df.add_argument('grid', help='.tsv/.txt или .xlsx')
    df.add_argument('--limit', type=int, default=5)

    mt = sub.add_parser('match', help='разобрать таблицу новым движком и вывести дерево корня')
    mt.add_argument('grammar')
    mt.add_argument('grid', help='.tsv/.txt или .xlsx')
    mt.add_argument('--all', action='store_true', help='печатать все корни, а не только лучший')

    fz = sub.add_parser('fuzz', help='сгенерировать таблицы из грамматики и проверить матчер')
    fz.add_argument('grammar')
    fz.add_argument('--seed', type=int, default=0)
    fz.add_argument('--count', type=int, default=20)
    fz.add_argument('--pattern', default=None, help='паттерн для генерации (по умолчанию корень)')
    return ap


def _cmd_check(args) -> int:
    res = compile_grammar(args.grammar, geometry=not args.no_geometry, lexical=not args.no_lexical,
                          ambiguity=not args.no_ambiguity)
    level = {'info': Severity.INFO, 'warning': Severity.WARNING, 'error': Severity.ERROR}[args.min_severity]
    diags = res.report.at_least(level)
    if args.json:
        print(json.dumps([d.to_dict() for d in diags], ensure_ascii=False, indent=2))
    else:
        from vstuxls.grammar2d.compiler.diagnostics import DiagnosticReport
        shown = DiagnosticReport()
        shown.extend(diags)
        print(shown.format())
    if res.report.has_errors:
        return 1
    if args.strict and res.report.at_least(Severity.WARNING):
        return 1
    return 0


def _cmd_explain(args) -> int:
    res = compile_grammar(args.grammar, ambiguity=False, lexical=False)
    from vstuxls.grammar2d.compiler.geometry import explain_pattern
    if args.pattern not in res.ir:
        print(f'неизвестный паттерн: {args.pattern}', file=sys.stderr)
        return 2
    print(explain_pattern(res.ir, args.pattern))
    return 0


def _cmd_policies(args) -> int:
    from vstuxls.grammar2d.compiler.ambiguity import policies_to_yaml
    res = compile_grammar(args.grammar, geometry=False, lexical=False, ambiguity=False)
    print(policies_to_yaml(res.ir))
    return 0


def _cmd_diff(args) -> int:
    from loguru import logger
    logger.remove()  # старый матчер очень многословен
    from vstuxls.grammar2d.compiler.diff import diff_matchers, load_grid
    rep = diff_matchers(args.grammar, load_grid(args.grid))
    print(rep.format(args.limit))
    return 0 if rep.roots_agree else 1


def _cmd_match(args) -> int:
    from vstuxls.grammar2d.compiler.diff import load_grid
    from vstuxls.grammar2d.compiler.engine import Engine
    from vstuxls.grammar2d.compiler.selection import coverage
    res = compile_grammar(args.grammar, lexical=False, ambiguity=False, geometry=False)
    if res.report.has_errors:
        print(res.report.format())
        return 1
    out = Engine(res.ir).run(load_grid(args.grid))
    print(f'корней: {len(out.roots)}')
    for w in out.warnings:
        print('предупреждение:', w)
    for m in (out.roots if args.all else out.roots[:1]):
        print(m.tree())
        cov = coverage(m, out.cells)
        print(f'покрытие: {cov.covered_cells}/{cov.total_cells} ({cov.ratio:.0%}); непокрытых: {len(cov.uncovered)}')
    return 0 if out.roots else 1


def _cmd_fuzz(args) -> int:
    from vstuxls.grammar2d.compiler.fuzz import run_fuzz
    return run_fuzz(args.grammar, seed=args.seed, count=args.count, pattern=args.pattern)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    args = _build_parser().parse_args(argv)
    return {'check': _cmd_check, 'explain': _cmd_explain, 'policies': _cmd_policies,
            'diff': _cmd_diff, 'match': _cmd_match, 'fuzz': _cmd_fuzz}[args.cmd](args)


if __name__ == '__main__':
    sys.exit(main())
