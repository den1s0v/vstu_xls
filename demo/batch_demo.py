import argparse
from importlib.resources import files
from pathlib import Path

from loguru import logger

from vstuxls.converters.xlsx import ExcelGrid
from vstuxls.export.vstu import export_schedule_document_as_json
from vstuxls.grammar2d import read_grammar
from vstuxls.services import DocumentParsingService, WaveDebugExporter
from vstuxls.utils import Checkpointer
from vstuxls.utils.convert import convert_all_in_dir


def parse_args() -> argparse.Namespace:
    lib_dir = files("vstuxls")
    root_dir = Path(__file__).resolve().parent.parent
    default_grammar = Path(str(root_dir / "cnf" / "grammar_root.yml"))
    # default_input_dir = root_dir / "tests" / "test_data"
    default_input_dir = root_dir / "materials/2026-03-20"
    default_output_base = root_dir / "data" / "output"
    default_report_base = root_dir / "data" / "reports"

    parser = argparse.ArgumentParser(
        description="Batch process XLSX files with grammar matching and debug exports.",
    )
    parser.add_argument(
        "--grammar",
        type=Path,
        default=default_grammar,
        help=f"Path to grammar YAML (default: {default_grammar})",
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=default_input_dir,
        help=f"Directory to scan for XLSX files (default: {default_input_dir})",
    )
    parser.add_argument(
        "--output-base",
        type=Path,
        default=default_output_base,
        help=f"Base directory for JSON export (default: {default_output_base})",
    )
    parser.add_argument(
        "--report-base",
        type=Path,
        default=default_report_base,
        help=f"Base directory for debug reports export (default: {default_report_base})",
    )
    parser.add_argument(
        "--waves-json",
        action="store_true",
        default=True,
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
        default=True,
        help="Export wave snapshots as Excel copies (enabled by default).",
    )
    parser.add_argument(
        "--no-excel",
        dest="waves_excel",
        action="store_false",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--no-diagnostics",
        action="store_true",
        help="Не сохранять parsing_diagnostics.json в папку отчёта по каждому файлу.",
    )
    return parser.parse_args()


def process_single_file(
    input_path: Path,
    grammar_path: Path,
    json_output_dir: Path,
    reports_output_base: Path,
    enable_json: bool = True,
    enable_excel: bool = True,
    enable_diagnostics: bool = True,
) -> bool:
    """Обрабатывает один XLSX файл и сохраняет отчёты в подпапку с уникальным именем."""
    try:
        logger.info("Processing file: {}", input_path)

        # Генерируем уникальное имя для подпапки (на основе имени исходного файла, без подпути)
        file_stem = input_path.stem
        output_dir = reports_output_base / file_stem
        # Убеждаемся, что директория для отчётов существует, прежде чем экспортировать unused_patterns.*
        output_dir.mkdir(parents=True, exist_ok=True)

        # Читаем грамматику
        grammar = read_grammar(grammar_path)

        # Загружаем документ
        grid = ExcelGrid.read_xlsx(input_path)

        # Создаём экспортёр с уникальной папкой для этого файла
        exporter = WaveDebugExporter(
            output_dir=output_dir,
            enable_json=enable_json,
            enable_excel=enable_excel,
            only_wave_indices=(999, ),
        )

        # Создаём сервис
        service = DocumentParsingService(
            grammar=grammar,
            wave_exporter=exporter,
            diagnostics_output_dir=output_dir if enable_diagnostics else None,
            document_source_path=input_path,
            grammar_source_path=grammar_path,
        )

        # Распознаём документ
        matches = service.parse_document(grid)

        logger.info("  Found {} root matches", len(matches))
        if enable_diagnostics:
            logger.info("  Diagnostics: {}", (output_dir / "parsing_diagnostics.json").resolve())

        # Экспортируем финальный отчёт о неиспользованных паттернах
        if matches:
            document_match = matches[0]

            service.export_final_report(document_match=document_match)
            logger.info("  Saved reports to {}", output_dir.resolve())

            # Экспортируем JSON-расписание в общую папку импорта
            if not json_output_dir:
                root_dir = Path(__file__).resolve().parent.parent
                json_output_dir = root_dir / "data" / "imports"
            json_output_dir.mkdir(parents=True, exist_ok=True)
            json_path = json_output_dir / f"{file_stem}.json"

            export_schedule_document_as_json(
                document_match,
                dst_path=str(json_path),
                source_path=input_path,
            )
            logger.info("  Exported JSON schedule to {}", json_path.resolve())

        return True

    except Exception as exc:
        logger.error("  Failed to process {}: {}", input_path, exc)
        return False


def process_many(
        paths: list[Path], grammar_path: Path,
        output_base: Path, report_base: Path,
        enable_json: bool,
        enable_excel: bool,
        input_path_base: Path | None = None,
        enable_diagnostics: bool = True,
) -> None:
    """Обрабатывает несколько XLSX файлов.
    input_path_base: если задано, то в целевой папке будет воссоздана такая же структура подкаталогов, как и в источнике относительно заданного пути. Должно быть подпутём всх путей из paths или None (без подкаталогов).
    """
    ch = Checkpointer()
    success_count = 0

    for path in paths:
        # prepare paths
        target_dir = report_base
        json_output_dir = output_base
        if input_path_base:
            # cut input_path_base from path
            if path.is_relative_to(input_path_base):
                subpath = path.parent.relative_to(input_path_base)
                target_dir = report_base / subpath
                json_output_dir = output_base / subpath

        # run extracting info from sheet under path
        if process_single_file(
            path, grammar_path, json_output_dir, target_dir,
            enable_json, enable_excel, enable_diagnostics,
        ):
            success_count += 1

    ch.hit(f'Completed: {success_count}/{len(paths)} files processed')


def process_all_in_dir(
    folder_path: Path,
    grammar_path: Path,
    output_base: Path,
    report_base: Path,
    enable_json: bool = True,
    enable_excel: bool = True,
    enable_diagnostics: bool = True,
) -> None:
    """Обрабатывает все XLSX файлы в указанной папке (рекурсивно).

    Дополнительно: перед обработкой пытается сконвертировать все `.xls` в `.xlsx`
    в том же дереве каталогов, если для них ещё нет соседнего `.xlsx` файла.
    """
    # Сначала конвертируем старые `.xls` → `.xlsx`, если такие файлы есть
    convert_all_in_dir(folder_path)

    # Теперь собираем все `.xlsx` для основной обработки
    paths = list(folder_path.rglob('*.xlsx'))
    logger.info("Found {} XLSX files in {}", len(paths), folder_path)
    process_many(
        paths, grammar_path, output_base, report_base,
        enable_json, enable_excel, folder_path, enable_diagnostics,
    )


def main() -> None:
    args = parse_args()

    logger.info("Starting batch processing…")
    logger.info("Grammar: {}", args.grammar)
    logger.info("Input directory: {}", args.input_dir)
    logger.info("Output base directory: {}", args.output_base)

    process_all_in_dir(
        folder_path=args.input_dir,
        grammar_path=args.grammar,
        output_base=args.output_base,
        report_base=args.report_base,
        enable_json=args.waves_json,
        enable_excel=args.waves_excel,
        enable_diagnostics=not args.no_diagnostics,
    )

    logger.info("Batch processing completed.")


if __name__ == "__main__":
    main()

