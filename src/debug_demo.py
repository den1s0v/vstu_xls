from __future__ import annotations

import argparse
from pathlib import Path

from loguru import logger

from converters.xlsx import ExcelGrid
from grammar2d import GrammarMatcher, read_grammar
from services import DocumentParsingService, WaveDebugExporter

# DEFAULT_XLSX_NAME = 'ОН_ФЭВТ_4 курс 2023.xlsx'
# DEFAULT_XLSX_NAME = 'ОН_ФЭУ_3 курс_v2.xlsx'
DEFAULT_XLSX_NAME = 'Сборник_расписаний_1.xlsx'
# DEFAULT_XLSX_NAME = 'Сборник_расписаний_2.xlsx'

def parse_args() -> argparse.Namespace:
    root_dir = Path(__file__).resolve().parent.parent
    default_grammar = root_dir / "cnf" / "grammar_root.yml"
    default_input = root_dir / "tests" / "test_data" / DEFAULT_XLSX_NAME
    default_output = root_dir / "data" / "debug_waves"

    parser = argparse.ArgumentParser(
        description="Run grammar matching with wave-level debug exports.",
    )
    parser.add_argument(
        "--grammar",
        type=Path,
        default=default_grammar,
        help=f"Path to grammar YAML (default: {default_grammar})",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=default_input,
        help=f"Path to XLSX document (default: {default_input})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=default_output,
        help=f"Directory to store debug exports (default: {default_output})",
    )
    parser.add_argument(
        "--waves-json",
        action="store_true",
        help="Export wave snapshots as JSON (enabled by default).",
    )
    parser.add_argument(
        "--no-json",
        dest="waves_json",
        action="store_false",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--waves-excel",
        action="store_true",
        help="Export wave snapshots as Excel copies (enabled by default).",
    )
    parser.add_argument(
        "--no-excel",
        dest="waves_excel",
        action="store_false",
        help=argparse.SUPPRESS,
    )
    parser.set_defaults(
        waves_json=True,
        waves_excel=True,
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    logger.info("Reading grammar from {}", args.grammar)
    grammar = read_grammar(args.grammar)

    logger.info("Loading document {}", args.input)
    grid = ExcelGrid.read_xlsx(args.input)

    exporter = WaveDebugExporter(
        output_dir=args.output,
        enable_json=args.waves_json,
        enable_excel=args.waves_excel,
        only_wave_indices=(0, 1, 4,5,6,7,8, )  # for all: omit / pass empty
    )

    service = DocumentParsingService(
        grammar=grammar,
        wave_exporter=exporter,
    )

    logger.info("Running grammar matcher…")
    matches = service.parse_document(grid)

    logger.info("Done. Found {} root matches.", len(matches))
    if matches:
        logger.info("First match: {}", matches[0])

        logger.info("Analyzing unused patterns…")
        service.export_final_report(document_match=matches[0])

    logger.info("Wave artifacts are saved under {}", args.output.resolve())


if __name__ == "__main__":
    main()

