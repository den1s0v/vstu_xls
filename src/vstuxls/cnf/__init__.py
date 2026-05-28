from collections.abc import Iterator
from contextlib import contextmanager
from importlib.resources import as_file, files
from pathlib import Path

DEFAULT_CELL_TYPES = "cell_types.yml"
DEFAULT_GRAMMAR = "grammar_root.yml"
LESSON_FRAMES = "lesson_frames.yml"
SPECIFIC_PATTERNS = "specific_patterns.yml"


def cnf_resource(filename: str | None = None):
    resource = files(__name__)
    return resource / filename if filename else resource


@contextmanager
def cnf_path(filename: str | None = None) -> Iterator[Path]:
    """Return a filesystem path to a bundled cnf resource.

    Use this as a context manager because package resources can be extracted to
    a temporary location by some importers.
    """
    with as_file(cnf_resource(filename)) as path:
        yield path
