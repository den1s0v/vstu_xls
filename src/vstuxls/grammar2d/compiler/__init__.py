"""Компилятор 2D-грамматики: frontend -> IR -> статический анализ -> (планировщик, матчер).

Быстрый старт::

    from vstuxls.grammar2d.compiler import compile_grammar
    result = compile_grammar('cnf/grammar_root.yml')
    print(result.report.format())

Этапы анализа включаются флагами `compile_grammar(..., geometry=True, lexical=True, ambiguity=True)`.
"""

from vstuxls.grammar2d.compiler.diagnostics import CODES, Diagnostic, DiagnosticReport, Severity, SourceLoc
from vstuxls.grammar2d.compiler.frontend import CompileResult, load_grammar_ir
from vstuxls.grammar2d.compiler.ir import (
    ArrayIR, CellTypeIR, ComponentIR, GrammarIR, LocationIR, PatternIR, PKind, PolicyIR, RelationIR, Role,
)
from vstuxls.grammar2d.compiler.lint import lint


def compile_grammar(
        config_file=None,
        *,
        text: str | None = None,
        file_name: str = '<memory>',
        base_dir=None,
        cell_types_text: str | None = None,
        structure: bool = True,
        geometry: bool = True,
        lexical: bool = True,
        ambiguity: bool = True,
) -> CompileResult:
    """Загрузить грамматику и выполнить статический анализ. Все проблемы собираются в `result.report`."""
    result = load_grammar_ir(config_file, text=text, file_name=file_name, base_dir=base_dir,
                             cell_types_text=cell_types_text)
    ir, report = result.ir, result.report

    if structure:
        lint(ir, report)

    # Остальные этапы подключаются лениво: они опираются на структуру без ошибок ссылок.
    broken_refs = bool(report.by_code('G002') or report.by_code('G001') or report.by_code('G003')
                       or report.by_code('G012'))
    if geometry and not broken_refs:
        from vstuxls.grammar2d.compiler.geometry import analyze_geometry
        analyze_geometry(ir, report)
    if lexical:
        from vstuxls.grammar2d.compiler.celltypes import analyze_cell_types
        analyze_cell_types(ir, report)
    if ambiguity and not broken_refs:
        from vstuxls.grammar2d.compiler.ambiguity import analyze_ambiguity
        analyze_ambiguity(ir, report)
    return result
