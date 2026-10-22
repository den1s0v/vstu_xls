"""Диф-тест: старый `GrammarMatcher` против нового `Engine` на одной грамматике и одной таблице.

Сравниваются множества рамок совпадений каждого конкретного паттерна (по имени). Расхождения нужны не как
«ошибки», а как карта различий: старый матчер отсекает кандидатов жадно и по эвристикам, новый находит все
согласованные и применяет политику отдельно.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PatternDiff:
    name: str
    old: int
    new: int
    only_old: list[tuple] = field(default_factory=list)
    only_new: list[tuple] = field(default_factory=list)

    @property
    def same(self) -> bool:
        return not self.only_old and not self.only_new


@dataclass
class DiffReport:
    patterns: list[PatternDiff]
    old_roots: int
    new_roots: int
    old_seconds: float
    new_seconds: float
    skipped: list[str] = field(default_factory=list)
    roots_equal: bool = False
    warnings: list[str] = field(default_factory=list)

    @property
    def identical(self) -> bool:
        return all(p.same for p in self.patterns) and self.roots_equal

    @property
    def roots_agree(self) -> bool:
        """Главный критерий: рамки корней совпадают (промежуточные кандидаты могут отличаться из-за политики)."""
        return self.roots_equal

    def format(self, limit: int = 5) -> str:
        lines = [f'корней: старый {self.old_roots}, новый {self.new_roots}; рамки корней '
                 f'{"совпадают" if self.roots_equal else "РАЗЛИЧАЮТСЯ"}; '
                 f'время: старый {self.old_seconds:.2f}s, новый {self.new_seconds:.2f}s']
        if self.skipped:
            lines.append('  не искались новым движком (недостижимы от корня): ' + ', '.join(self.skipped))
        for w in self.warnings[:limit]:
            lines.append(f'  предупреждение нового движка: {w}')
        for d in self.patterns:
            mark = '=' if d.same else '≠'
            lines.append(f'  {mark} {d.name}: старый {d.old}, новый {d.new}'
                         + ('' if d.same else f' (только старый: {len(d.only_old)}, только новый: {len(d.only_new)})'))
            for b in d.only_old[:limit]:
                lines.append(f'      - старый: {b}')
            for b in d.only_new[:limit]:
                lines.append(f'      + новый:  {b}')
        return '\n'.join(lines)


def load_grid(path: str | Path):
    """Прочитать таблицу: `.tsv/.txt` — текстовая сетка, `.xlsx` — Excel."""
    path = Path(path)
    if path.suffix.lower() in ('.xlsx', '.xlsm'):
        from vstuxls.converters.xlsx import ExcelGrid
        return ExcelGrid.read_xlsx(path)
    from vstuxls.converters.text import TxtGrid
    return TxtGrid(path.read_text(encoding='utf-8'))


def _lrtb(box) -> tuple[int, int, int, int]:
    return (box.left, box.top, box.right, box.bottom)


def diff_matchers(grammar_path: str | Path, grid, *, only_patterns: list[str] | None = None) -> DiffReport:
    import time

    from vstuxls.grammar2d.compiler import compile_grammar
    from vstuxls.grammar2d.Grammar import read_grammar
    from vstuxls.grammar2d.matching.GrammarMatcher import GrammarMatcher
    from vstuxls.grammar2d.compiler.engine import Engine

    t0 = time.time()
    grammar = read_grammar(grammar_path)
    gm = GrammarMatcher(grammar=grammar)
    old_roots = gm.run_match(grid)
    old_sec = time.time() - t0
    old: dict[str, set] = {}
    for pattern, matches in gm.matches_by_element.items():
        for m in matches:
            if m.pattern.name == pattern.name and m.box is not None:
                old.setdefault(pattern.name, set()).add(_lrtb(m.box))

    res = compile_grammar(grammar_path, lexical=False, ambiguity=False, geometry=False)
    t1 = time.time()
    result = Engine(res.ir).run(grid)
    new_sec = time.time() - t1
    new = {name: {m.box for m in ms} for name, ms in result.matches.items()}

    # Новый движок не ищет паттерны, недостижимые от корня: их сравнивать не с чем.
    skipped = sorted(set(old) - set(new))
    names = [n for n in new if only_patterns is None or n in only_patterns]
    diffs = []
    for n in names:
        o, w = old.get(n, set()), new.get(n, set())
        diffs.append(PatternDiff(n, len(o), len(w), sorted(o - w), sorted(w - o)))
    old_root_boxes = sorted(_lrtb(m.box) for m in (old_roots or []))
    new_root_boxes = sorted(m.box for m in result.roots)
    return DiffReport(diffs, len(old_roots or []), len(result.roots), old_sec, new_sec,
                      skipped=skipped, roots_equal=old_root_boxes == new_root_boxes,
                      warnings=list(result.warnings))
