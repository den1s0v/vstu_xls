# tests_bootstrapper.py

import sys


def init_testing_environment():
    """ Allow Python to load code from src/ dir seamlessly. """
    sys.path.insert(1, '../src/')
