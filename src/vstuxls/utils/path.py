from pathlib import Path


def current_rootpath() -> Path:
    curfile = Path(__file__)
    while curfile.name != "src":
        curfile = curfile.parent
    return curfile.parent
