"""Контракт и наличие отчёта parsing_diagnostics.json."""

import json
import tempfile
import unittest
from pathlib import Path

from tests_bootstrapper import init_testing_environment

init_testing_environment()

from vstuxls.converters.text import TxtGrid
from vstuxls.grammar2d import read_grammar
from vstuxls.services import DocumentParsingService


class ParsingDiagnosticsTestCase(unittest.TestCase):
    def test_parsing_diagnostics_json_shape(self) -> None:
        root = Path(__file__).parent
        grid = TxtGrid((root / "test_data/grid1.tsv").read_text())
        grammar = read_grammar(root / "test_data/simple_grammar_txt.yml")

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            service = DocumentParsingService(
                grammar=grammar,
                diagnostics_output_dir=out,
                document_source_path="grid1.tsv",
                grammar_source_path="simple_grammar_txt.yml",
            )
            matches = service.parse_document(grid)

            path = out / "parsing_diagnostics.json"
            self.assertTrue(path.is_file(), "parse_document must write parsing_diagnostics.json")
            data = json.loads(path.read_text(encoding="utf-8"))

            self.assertIn("document", data)
            self.assertIn("summary", data)
            self.assertIn("issues", data)
            self.assertIsInstance(data["issues"], list)

            summary = data["summary"]
            for key in (
                "errors_count",
                "warnings_count",
                "infos_count",
                "root_matches_count",
            ):
                self.assertIn(key, summary)

            self.assertEqual(summary["root_matches_count"], len(matches))

            doc = data["document"]
            self.assertIn("started_at", doc)
            self.assertIn("finished_at", doc)
            self.assertIn("duration_ms", doc)

    def test_parse_exception_recorded_in_diagnostics(self) -> None:
        root = Path(__file__).parent
        grid = TxtGrid((root / "test_data/grid1.tsv").read_text())
        grammar = read_grammar(root / "test_data/simple_grammar_txt.yml")

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            service = DocumentParsingService(
                grammar=grammar,
                diagnostics_output_dir=out,
            )

            class BoomGrid:
                def get_view(self):
                    raise RuntimeError("simulated load failure")

            with self.assertRaises(RuntimeError):
                service.parse_document(BoomGrid())

            path = out / "parsing_diagnostics.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["summary"]["errors_count"], 1)
            codes = {issue["code"] for issue in data["issues"]}
            self.assertIn("PARSE_EXCEPTION", codes)


if __name__ == "__main__":
    unittest.main()
