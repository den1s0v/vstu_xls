import unittest

from pathlib import Path

from geom2d import Box, Point
from grid import Grid, Cell

class TxtGrid(Grid):
    def __init__(self, text: str, sep='\t') -> None:
        super().__init__()
        self.load_cells(text, sep)
        
    def load_cells(self, text: str, sep='\t'):
        lines = text.splitlines()
        for i, line in enumerate(lines):
            for j, content in enumerate(line.split(sep)):
                if not content:
                    continue
                cell = Cell(self, Point(i, j), content=content)
                self.registerCell(cell)



class GridTestCase(unittest.TestCase):
    def test_in_1(self):
        
        g = TxtGrid(Path('tests/grid1.tsv').read_text())
        gw = g.getView()
        print('grid.getBoundingBox:', g.getBoundingBox())
        print('grid-view range:', gw)
        
        self.assertEqual(gw, (0,0, 9,9))
        
        # for cell in gw.iterateCells():
        #     print(cell)

        col = gw.getRegion(Box(0,0, 1,9))  
        print('col-view range:', gw)
        content_list = []
        for cell in col.iterateCells():
            print(cell)
            content_list.append(cell.cell.content)
            
        print(''.join(content_list))

 



if __name__ == '__main__':
    unittest.main()
    # GridTestCase.test_in_1(None)
