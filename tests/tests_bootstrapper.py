# tests_bootstrapper.py

import sys
from pathlib import Path

from loguru import logger


def init_testing_environment():
    """ Allow Python to load code from src/ dir seamlessly. """
    src_path = Path(__file__).parent.parent / "src"
    sys.path.insert(1, str(src_path.resolve()))

    # redefine logging level defaulting to DEBUG
    logger.remove()
    logger.add(sys.stderr, level='INFO')


