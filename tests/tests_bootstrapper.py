# tests_bootstrapper.py

from pathlib import Path
import sys


def init_testing_environment():
    """ Allow Python to load code from src/ dir seamlessly. """
    src_path = Path(__file__).parent.parent / "src"
    sys.path.insert(1, str(src_path.resolve()))
