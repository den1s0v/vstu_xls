from converters.abstract import AbstractGridBuilder
from geom2d.point import Point
from grid import Cell, Grid


class TxtGrid(Grid, AbstractGridBuilder):
    def __init__(self, text: str, sep="\t") -> None:
        super().__init__()
        self._sep = sep
        self._load_cells(text)

    def _load_cells(self, data: str):
        lines = data.splitlines()
        for y, line in enumerate(lines):
            for x, content in enumerate(line.split(self._sep)):
                if not content:
                    continue
                cell = Cell(self, Point(x, y), content=content)
                self.registerCell(cell)
