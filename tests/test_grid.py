import unittest

import openpyxl
from tests_bootstrapper import init_testing_environment

init_testing_environment()

from converters.text import TxtGrid
from converters.xlsx import ExcelGrid
from geom2d.box import Box
from geom2d.direction import LEFT, RIGHT, UP, Direction
from utils.path import current_rootpath

testdata_path = current_rootpath() / "tests" / "test_data"


class GridTestCase(unittest.TestCase):
    def test_in_1(self):
        grid1 = testdata_path / "grid1.tsv"
        grid2 = testdata_path / "grid1.xlsx"
        gs = [TxtGrid(grid1.read_text()), ExcelGrid(openpyxl.load_workbook(grid2).active)]

        for g in gs:
            print(f"Testing {g}")
            gw = g.getView()
            print("grid.getBoundingBox:", g.getBoundingBox())
            print("grid-view range:", gw)

            self.assertEqual(tuple(gw), (0, 0, 9, 9))
            self.assertEqual((0, 0, 9, 9), tuple(gw))

            # Справа НАЛЕВО, снизу ВВЕРХ:
            for cell in gw.iterate_cells((LEFT, UP)):
                print(cell)

            col = gw.getRegion(Box(0, 0, 1, 9))
            print("col-view range:", col)
            content_list = []
            # for point in col.iterate_points( [UP, RIGHT] ):
            #     # print(point)
            #     ...
            # Снизу ВВЕРХ, слева НАПРАВО:
            for cell in col.iterate_cells([UP, RIGHT]):
                print(cell)
                content_list.append(cell.cell.content)

            col_chars = "".join(content_list)
            print(col_chars)

            # self.assertEqual(col_chars, '87654321')
            self.assertEqual(col_chars, "12345678")

            row = gw.getRegion(Box(0, 0, 9, 1))
            print("row-view range:", row)
            content_list = []
            for cell in row.iterate_cells():
                print(cell)
                content_list.append(cell.cell.content)

            row_chars = "".join(content_list)
            print(row_chars)

            self.assertEqual(row_chars, "ABCDEFGH")

            rect = gw.getRegion(Box(3, 3, 3, 3))
            print("rect-view range:", rect)
            for d in Direction._cache.values():
                outer = rect.lookOutside(d)
                chars = (cell.cell.content for cell in outer.iterate_cells())
                print("rect-view range, %s:" % d.prop_name, outer)
                print("                   ", "".join(chars))

            print()
            rect = gw.getRegion(Box(2, 2, 5, 5))
            print("rect-view range:", rect)
            for d in Direction._cache.values():
                outer = rect.lookOutside(d, distance=2)
                chars = (cell.cell.content for cell in outer.iterate_cells())
                print("rect-view range, %s:" % d.prop_name, outer)
                print("                   ", "".join(chars))

            print()
            print("# zero distance")
            rect = gw.getRegion(Box(2, 2, 4, 4))
            print("rect-view range:", rect)
            for d in Direction._cache.values():
                outer = rect.lookOutside(d, distance=0)
                # chars = (cell.cell.content for cell in outer.iterateCells())
                print("rect-view range, %s:" % d.prop_name, outer)
                # print('                   ', ''.join(chars))

            print()
            print("# ignored distance")
            rect = gw.getRegion(Box(2, 2, 4, 4))
            print("rect-view range:", rect)
            for d in Direction._cache.values():
                outer = rect.lookOutside(d, distance=-10)  # ignored distance
                chars = (cell.cell.content for cell in outer.iterate_cells())
                print("rect-view range, %s:" % d.prop_name, outer)
                print("                   ", "".join(chars))

            print()
            print("# too large distance, clamp.")
            rect = gw.getRegion(Box(2, 2, 4, 4))
            print("rect-view range:", rect)
            for d in Direction._cache.values():
                outer = rect.lookOutside(d, distance=999)  # too large distance, clamp.
                chars = (cell.cell.content for cell in outer.iterate_cells())
                print("rect-view range, %s:" % d.prop_name, outer)
                print("                   ", "".join(chars))

    def test_in_2(self):
        print("test xlsx 2")
        workbook = openpyxl.load_workbook(testdata_path / "grid2.xlsx")
        g = ExcelGrid(workbook.active)
        gw = g.getView()
        for cell in gw.iterate_cells():
            print(cell)


if __name__ == "__main__":
    unittest.main()
