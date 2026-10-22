"""Тесты компилятора 2D-грамматики (`vstuxls.grammar2d.compiler`)."""

import random
import textwrap
import unittest

from tests_bootstrapper import init_testing_environment

init_testing_environment()

from pathlib import Path

from vstuxls.converters.text import TxtGrid
from vstuxls.geom2d import open_range
from vstuxls.grammar2d.compiler import compile_grammar
from vstuxls.grammar2d.compiler.engine import Engine
from vstuxls.grammar2d.compiler.stn import STN

DATA = Path(__file__).parent / 'test_data'
DEMO = DATA / 'v2_demo_grammar.yml'

TYPES = """
cell_types:
  - ta:
      patterns: [{confidence: 1.0, pattern: 'a+', pattern_syntax: re, anchors: both}]
  - tb:
      patterns: [{confidence: 1.0, pattern: 'b+', pattern_syntax: re, anchors: both}]
  - tab:
      patterns: [{confidence: 1.0, pattern: '[ab]+', pattern_syntax: re, anchors: both}]
"""


def compile_text(body: str, *, types: bool = True, **kwargs):
    text = 'grammar: 2\n' + (TYPES if types else '') + textwrap.dedent(body)
    return compile_grammar(text=text, **kwargs)


def codes(result) -> set[str]:
    return result.report.codes()


class StnTestCase(unittest.TestCase):
    def test_negative_cycle_is_contradiction(self):
        stn = STN()
        stn.add_diff('a', 'b', open_range(1, None), 'a - b >= 1')
        stn.add_diff('b', 'a', open_range(1, None), 'b - a >= 1')
        self.assertFalse(stn.is_consistent())
        self.assertIsNotNone(stn.find_negative_cycle())

    def test_closure_gives_implied_bounds(self):
        stn = STN()
        stn.add_diff('b', 'a', open_range(1, 2), 'b - a in 1..2')
        stn.add_diff('c', 'b', open_range(3, 3), 'c - b == 3')
        self.assertTrue(stn.is_consistent())
        implied = STN.implied(stn.closure(), 'c', 'a')
        self.assertEqual((4, 5), (implied.start, implied.stop))


class LintTestCase(unittest.TestCase):
    def test_unknown_reference(self):
        r = compile_text("""
            patterns:
              root:
                kind: area
                root: true
                inner:
                  x: {pattern: no_such_pattern}
            """)
        self.assertIn('G002', codes(r))

    def test_dependency_cycle(self):
        r = compile_text("""
            patterns:
              root:
                kind: area
                root: true
                inner:
                  x: {pattern: p1}
              p1:
                kind: area
                inner:
                  y: {pattern: p2}
              p2:
                kind: area
                inner:
                  z: {pattern: p1}
            """)
        self.assertIn('G003', codes(r))

    def test_unreachable_pattern_and_unknown_key(self):
        r = compile_text("""
            patterns:
              root:
                kind: area
                root: true
                inner:
                  x: {pattern: ca}
                locaton: left          # опечатка
              ca: {kind: cell, content_type: ta}
              orphan: {kind: cell, content_type: tb}
            """)
        self.assertIn('G004', codes(r))
        self.assertIn('G005', codes(r))

    def test_unproductive_pattern(self):
        r = compile_text("""
            patterns:
              root:
                kind: area
                root: true
                inner:
                  x: {pattern: loop}
              loop:
                kind: array
                item_pattern: loop2
              loop2:
                kind: array
                item_pattern: loop
            """)
        self.assertTrue({'G003', 'G014'} & codes(r))


class GeometryTestCase(unittest.TestCase):
    def test_contradictory_sizes_are_errors(self):
        r = compile_text("""
            patterns:
              root:
                kind: area
                root: true
                size: 5+ x 1
                inner:
                  x:
                    pattern: ca
                    location: {left: 0, right: 0}   # занимает всю ширину родителя
              ca: {kind: cell, content_type: ta, size: 2 x 1}
            """)
        self.assertIn('GEO001', codes(r))
        self.assertTrue(r.report.has_errors)

    def test_consistent_grammar_has_no_geometry_errors(self):
        r = compile_text("""
            patterns:
              root:
                kind: area
                root: true
                inner:
                  x: {pattern: ca}
                  y: {pattern: cb}
                relations:
                  - x.right <= y.left
                  - x.top == y.top
              ca: {kind: cell, content_type: ta}
              cb: {kind: cell, content_type: tb}
            """)
        self.assertFalse([d for d in r.report if d.code.startswith('GEO') and d.severity.name == 'ERROR'])


class LexicalTestCase(unittest.TestCase):
    def test_overlapping_cell_types_are_reported_with_witness(self):
        r = compile_text("""
            patterns:
              root:
                kind: area
                root: true
                inner:
                  x: {pattern: ca}
                  y: {pattern: cab}
              ca: {kind: cell, content_type: ta}
              cab: {kind: cell, content_type: tab}
            """)
        diags = r.report.by_code('LEX001')
        self.assertTrue(diags)
        self.assertTrue(any(d.witness for d in diags))

    def test_lexical_stage_can_be_disabled(self):
        r = compile_text("""
            patterns:
              root:
                kind: area
                root: true
                inner:
                  x: {pattern: ca}
                  y: {pattern: cab}
              ca: {kind: cell, content_type: ta}
              cab: {kind: cell, content_type: tab}
            """, lexical=False)
        self.assertNotIn('LEX001', codes(r))


class AmbiguityTestCase(unittest.TestCase):
    ALT = """
        patterns:
          root:
            kind: area
            root: true
            inner:
              x: {pattern: choice}
          choice:
            kind: alt
            one_of: [ca1, ca2]
          ca1: {kind: cell, content_type: ta}
          ca2: {kind: cell, content_type: ta%s}
        """

    def test_ambiguous_alt_without_policy(self):
        r = compile_text(self.ALT % '')
        self.assertIn('AMB001', codes(r))

    def test_priority_resolves_ambiguity(self):
        r = compile_text(self.ALT % ', priority: 1')
        self.assertNotIn('AMB001', codes(r))
        self.assertIn('AMB002', codes(r))

    def test_distinct_leaf_types_are_not_ambiguous(self):
        r = compile_text("""
            patterns:
              root:
                kind: area
                root: true
                inner:
                  x: {pattern: choice}
              choice:
                kind: alt
                one_of: [ca, cb]
              ca: {kind: cell, content_type: ta}
              cb: {kind: cell, content_type: tb}
            """)
        self.assertNotIn('AMB001', codes(r))


class FrontendV2TestCase(unittest.TestCase):
    def test_template_expansion_and_count(self):
        r = compile_grammar(DEMO)
        ir = r.ir
        self.assertIn('field_text', ir.patterns)
        self.assertIn('field_number', ir.patterns)
        report = ir['report']
        names = [c.name for c in report.components]
        self.assertEqual(['title', 'body', 'remark', 'remark_2'], names)
        self.assertTrue(all(c.optional for c in report.components if c.name.startswith('remark')))
        self.assertEqual(3, len(report.relations))
        self.assertEqual(3, len(ir['field_text'].relations))  # подпись и значение в одной строке, значение вплотную
        self.assertEqual(0.95, ir['field_number'].policy.confidence)

    def test_v2_demo_grammar_is_clean(self):
        r = compile_grammar(DEMO)
        self.assertEqual([], [d.format() for d in r.report if d.severity.name in ('ERROR', 'WARNING')])

    def test_v1_component_size_means_parent_size(self):
        text = textwrap.dedent("""
            patterns:
              root:
                kind: area
                root: true
                inner:
                  x: {pattern: ca, size: 2 x 1}
              ca: {kind: cell, content_type: ta}
            """)
        r = compile_grammar(text=TYPES + text)  # без `grammar: 2` — диалект v1
        self.assertIn('G020', codes(r))
        self.assertIsNotNone(r.ir['root'].size)


class EngineTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ir = compile_grammar(DEMO, lexical=False, ambiguity=False, geometry=False).ir

    def run_grid(self, text: str):
        return Engine(self.ir, strict_cell_size=True).run(TxtGrid(text))

    def boxes(self, res, name):
        return sorted(m.box for m in res.matches.get(name, []))

    def test_report_with_alt_fields(self):
        res = self.run_grid('TITLE\nName:\talpha\nAge:\t42\n')
        self.assertEqual([(0, 0, 2, 3)], [m.box for m in res.roots])
        self.assertEqual([(0, 1, 2, 2)], self.boxes(res, 'field_text'))
        self.assertEqual([(0, 2, 2, 3)], self.boxes(res, 'field_number'))
        self.assertEqual([(0, 1, 2, 3)], self.boxes(res, 'fields'))

    def test_optional_count_components_extend_root(self):
        res = self.run_grid('TITLE\nName:\talpha\n(note)\n')
        self.assertEqual([(0, 0, 2, 3)], [m.box for m in res.roots])

    def test_relation_violated_no_root(self):
        # значение отделено от подписи пустой ячейкой: `value.left == caption.right` нарушено
        res = self.run_grid('TITLE\nName:\t\talpha\n')
        self.assertEqual([], res.roots)

    def test_forbid_blocks_field_with_glued_caption_on_the_left(self):
        res = self.run_grid('TITLE\nXyz:\tName:\talpha\n')
        self.assertEqual([], self.boxes(res, 'field_text'))
        self.assertEqual([], res.roots)

    def test_array_align_start_allows_different_widths(self):
        res = self.run_grid('TITLE\nName:\talpha\nAge:\t42\nKey:\tvalue\n')
        self.assertEqual([(0, 0, 2, 4)], [m.box for m in res.roots])

    def test_only_best_parse_per_root_box(self):
        res = self.run_grid('TITLE\nName:\talpha\n')
        self.assertEqual(1, len(res.roots))


class DiffAgainstOldMatcherTestCase(unittest.TestCase):
    """Новый движок обязан находить те же корни, что и старый матчер на корпусе `test_data`."""

    def test_sea_grammar_roots_agree(self):
        from vstuxls.converters.xlsx import ExcelGrid
        from vstuxls.grammar2d.compiler.diff import diff_matchers

        rep = diff_matchers(DATA / 'sea_grammar_1.yml', ExcelGrid.read_xlsx(DATA / 'sea9.xlsx'))
        self.assertTrue(rep.roots_agree, rep.format())
        self.assertEqual((1, 1), (rep.old_roots, rep.new_roots))


class FuzzTestCase(unittest.TestCase):
    def test_generated_tables_are_recognized(self):
        from vstuxls.grammar2d.compiler.fuzz import Fuzzer, check_case, generate_case

        ir = compile_grammar(DEMO, lexical=False, ambiguity=False, geometry=False).ir
        fz = Fuzzer(ir, random.Random(0))
        generated = 0
        for seed in range(8):
            case = generate_case(ir, 'report', seed, fuzzer=fz)
            if case is None:
                continue
            generated += 1
            self.assertEqual([], check_case(ir, case), case.render())
        self.assertGreaterEqual(generated, 6)

    def test_fuzz_finds_unrecognizable_grammar(self):
        """Если регулярка типа ячейки не распознаёт то, что породила грамматика, — это расхождение."""
        from vstuxls.grammar2d.compiler.fuzz import Fuzzer, check_case, generate_case

        ir = compile_text("""
            patterns:
              root:
                kind: area
                root: true
                inner:
                  x: {pattern: ca}
              ca: {kind: cell, content_type: ta, size: 3 x 1}
            """).ir
        # размер объявлен 3 x 1, строгий размер проверяется: порождённая таблица должна находиться
        fz = Fuzzer(ir, random.Random(1))
        case = generate_case(ir, 'root', 1, fuzzer=fz)
        self.assertIsNotNone(case)
        self.assertEqual([], check_case(ir, case))


class CliTestCase(unittest.TestCase):
    def test_check_command(self):
        import contextlib
        import io

        from vstuxls.grammar2d.compiler.cli import main

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = main(['check', str(DEMO)])
        self.assertEqual(0, code)

    def test_explain_command_mentions_sizes(self):
        import contextlib
        import io

        from vstuxls.grammar2d.compiler.cli import main

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            main(['explain', str(DEMO), 'field_text'])
        self.assertIn('field_text', out.getvalue())


if __name__ == '__main__':
    unittest.main()
