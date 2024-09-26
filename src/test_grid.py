import unittest

from pathlib import Path

from geom2d import Box, Point, LEFT, RIGHT, UP, DOWN
from grid import Grid, Cell

class TxtGrid(Grid):
    def __init__(self, text: str, sep='\t') -> None:
        super().__init__()
        self.load_cells(text, sep)
        
    def load_cells(self, text: str, sep='\t'):
        lines = text.splitlines()
        for y, line in enumerate(lines):
            for x, content in enumerate(line.split(sep)):
                if not content:
                    continue
                cell = Cell(self, Point(x, y), content=content)
                self.registerCell(cell)



class GridTestCase(unittest.TestCase):
    def test_in_1(self):
        
        g = TxtGrid(Path('tests/grid1.tsv').read_text())
        gw = g.getView()
        print('grid.getBoundingBox:', g.getBoundingBox())
        print('grid-view range:', gw)
        
        self.assertEqual(gw, (0,0, 9,9))
        self.assertEqual((0,0, 9,9), gw)
        
        for cell in gw.iterateCells((LEFT, UP)):
            print(cell)

        col = gw.getRegion(Box(0,0, 1,9))  
        print('col-view range:', col)
        content_list = []
        for cell in col.iterateCells( [UP, RIGHT] ):
            print(cell)
            content_list.append(cell.cell.content)
            
        col_chars = ''.join(content_list)
        print(col_chars)
        
        # self.assertEqual(col_chars, '87654321')
        self.assertEqual(col_chars, '12345678')


        row = gw.getRegion(Box(0,0, 9,1))  
        print('row-view range:', row)
        content_list = []
        for cell in row.iterateCells():
            print(cell)
            content_list.append(cell.cell.content)
            
        row_chars = ''.join(content_list)
        print(row_chars)
        
        self.assertEqual(row_chars, 'ABCDEFGH')




if __name__ == '__main__':
    unittest.main()
    # GridTestCase.test_in_1(None)
