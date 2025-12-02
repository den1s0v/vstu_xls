from __future__ import annotations

import argparse
import json
from pathlib import Path

from loguru import logger


def collect_metadata_from_dir(imports_dir: Path) -> list[dict]:
    """Собирает метаданные расписаний из всех JSON-файлов в директории.

    Ожидается формат наших экспортов:
        {
          "title": { ...метаданные расписания... },
          "table": { ... }
        }

    Возвращается список объектов `title` (как в schedule_reference_import.json).
    """
    entries: list[dict] = []

    if not imports_dir.exists():
        logger.error("Imports directory does not exist: {}", imports_dir)
        return entries

    for path in sorted(imports_dir.glob("*.json")):
        try:
            with path.open("r", encoding="utf8") as f:
                data = json.load(f)
        except Exception as exc:
            logger.error("Failed to read JSON from {}: {}", path, exc)
            continue

        title = data.get("title")
        if not isinstance(title, dict):
            logger.warning("File {} has no dict `title` field, skipping", path)
            continue

        entries.append(title)

    return entries


def write_metadata_file(entries: list[dict], dst_path: Path) -> None:
    """Сохраняет список метаданных расписаний в файл."""
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    with dst_path.open("w", encoding="utf8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)
    logger.info("Schedule metadata written to {}", dst_path.resolve())


def parse_args() -> argparse.Namespace:
    root_dir = Path(__file__).resolve().parent.parent.parent
    default_imports_dir = root_dir / "data" / "imports"
    default_output = root_dir / "data" / "schedule_metadata.json"

    parser = argparse.ArgumentParser(
        description="Collect schedule metadata from exported JSON files for ReferenceImporter.import_schedule."
    )
    parser.add_argument(
        "--imports-dir",
        type=Path,
        default=default_imports_dir,
        help=f"Directory with exported schedule JSON files (default: {default_imports_dir})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=default_output,
        help=f"Path to resulting metadata JSON (default: {default_output})",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    logger.info("Collecting schedule metadata from {}", args.imports_dir)
    entries = collect_metadata_from_dir(args.imports_dir)

    if not entries:
        logger.warning("No metadata entries collected; nothing to write.")
        return

    write_metadata_file(entries, args.output)


if __name__ == "__main__":
    main()


