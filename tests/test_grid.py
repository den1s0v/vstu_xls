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
        gs = [
            TxtGrid((testdata_path / "grid1.tsv").read_text()),
            ExcelGrid(openpyxl.load_workbook(testdata_path / "grid1.xlsx").active),
        ]
        for g in gs:
            dshift = 1 if isinstance(g, ExcelGrid) else 0
            gw = g.get_view()
            print("grid.get_bounding_box:", g.get_bounding_box())
            print("grid-view range:", gw)

            self.assertEqual(tuple(gw), (dshift, dshift, 9, 9))
            self.assertEqual((dshift, dshift, 9, 9), tuple(gw))

            # Справа НАЛЕВО, снизу ВВЕРХ:
            for cell in gw.iterate_cells((LEFT, UP)):
                print(cell)

            col = gw.get_region(Box(dshift, dshift, 1, 9))
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

            row = gw.get_region(Box(dshift, dshift, 9, 1))
            print("row-view range:", row)
            content_list = []
            for cell in row.iterate_cells():
                print(cell)
                content_list.append(cell.cell.content)

            row_chars = "".join(content_list)
            print(row_chars)

            self.assertEqual(row_chars, "ABCDEFGH")

            rect = gw.get_region(Box(3 + dshift, 3 + dshift, 3, 3))
            print("rect-view range:", rect)
            for d in Direction.known_instances():
                outer = rect.look_outside(d)
                chars = (cell.cell.content for cell in outer.iterate_cells())
                print("rect-view range, %s:" % d.prop_name, outer)
                print("                   ", "".join(chars))

            print()
            rect = gw.get_region(Box(2 + dshift, 2 + dshift, 5, 5))
            print("rect-view range:", rect)
            for d in Direction.known_instances():
                outer = rect.look_outside(d, distance=2)
                chars = (cell.cell.content for cell in outer.iterate_cells())
                print("rect-view range, %s:" % d.prop_name, outer)
                print("                   ", "".join(chars))

            print()
            print("# zero distance")
            rect = gw.get_region(Box(2 + dshift, 2 + dshift, 4, 4))
            print("rect-view range:", rect)
            for d in Direction.known_instances():
                outer = rect.look_outside(d, distance=0)
                # chars = (cell.cell.content for cell in outer.iterateCells())
                print("rect-view range, %s:" % d.prop_name, outer)
                # print('                   ', ''.join(chars))

            print()
            print("# ignored distance")
            rect = gw.get_region(Box(2 + dshift, 2 + dshift, 4, 4))
            print("rect-view range:", rect)
            for d in Direction.known_instances():
                outer = rect.look_outside(d, distance=-10)  # ignored distance
                chars = (cell.cell.content for cell in outer.iterate_cells())
                print("rect-view range, %s:" % d.prop_name, outer)
                print("                   ", "".join(chars))

            print()
            print("# too large distance, clamp.")
            rect = gw.get_region(Box(2 + dshift, 2 + dshift, 4, 4))
            print("rect-view range:", rect)
            for d in Direction.known_instances():
                outer = rect.look_outside(d, distance=999)  # too large distance, clamp.
                chars = (cell.cell.content for cell in outer.iterate_cells())
                print("rect-view range, %s:" % d.prop_name, outer)
                print("                   ", "".join(chars))

    def test_in_2(self):
        workbook = openpyxl.load_workbook(testdata_path / "grid2.xlsx")
        g = ExcelGrid(workbook.active)
        gw = g.get_view()
        self.assertEqual(gw.get_cell_view((1, 1)).cell.content, "a")
        self.assertEqual(gw.get_cell_view((1, 3)).cell.content, "x")
        self.assertEqual(gw.get_cell_view((2, 3)).cell.content, "m")
        self.assertEqual(gw.get_cell_view((3, 1)).cell.content, "b")
        self.assertEqual(gw.get_cell_view((3, 2)).cell.content, "y")

        self.assertEqual(gw.get_cell_view((4, 1)).cell.content, "merged")
        self.assertEqual(gw.get_cell_view((4, 1)).size.h, 3)
        self.assertEqual(gw.get_cell_view((4, 1)).size.w, 2)

    def test_in_3(self):
        workbook = openpyxl.load_workbook(testdata_path / "grid3.xlsx")
        g = ExcelGrid(workbook.active)
        gw = g.get_view()
        self.assertEqual(gw.get_cell_view((1, 1)).cell.content, "a")
        self.assertEqual(gw.get_cell_view((2, 1)).cell.content, "b")
        self.assertEqual(gw.get_cell_view((3, 1)).cell.content, "c")
        self.assertEqual(gw.get_cell_view((4, 1)).cell.content, "d")
        self.assertEqual(gw.get_cell_view((5, 1)).cell.content, "e")
        self.assertEqual(gw.get_cell_view((6, 1)), None)

        self.assertEqual(gw.get_cell_view((1, 2)).cell.content, "x")
        self.assertEqual(gw.get_cell_view((2, 2)).cell.content, "y")
        self.assertEqual(gw.get_cell_view((3, 2)).cell.content, "z")

        self.assertEqual(gw.get_cell_view((4, 2)).cell.content, "i")
        self.assertTrue("bold" in gw.get_cell_view((4, 2)).cell.style.font_style)

        self.assertEqual(gw.get_cell_view((5, 2)).cell.content, "j")
        self.assertEqual(gw.get_cell_view((5, 2)).size.h, 2)
        self.assertEqual(gw.get_cell_view((5, 2)).size.w, 1)
        self.assertEqual(gw.get_cell_view((5, 3)).cell.content, "j")
        self.assertTrue("italic" in gw.get_cell_view((5, 3)).cell.style.font_style)

        self.assertEqual(gw.get_cell_view((6, 2)).cell.content, "k")

        self.assertEqual(gw.get_cell_view((2, 3)).cell.content, "m")
        self.assertEqual(gw.get_cell_view((2, 3)).size.h, 2)
        self.assertEqual(gw.get_cell_view((2, 3)).size.w, 2)

        self.assertEqual(gw.get_cell_view((4, 3)).cell.content, "s")
        self.assertEqual(gw.get_cell_view((6, 3)).cell.content, "_")

        self.assertEqual(gw.get_cell_view((1, 4)).cell.content, "t")
        self.assertEqual(gw.get_cell_view((4, 4)).cell.content, "w")
        self.assertEqual(gw.get_cell_view((5, 4)).cell.content, "p")
        self.assertTrue("bold" in gw.get_cell_view((5, 4)).cell.style.font_style)
        self.assertTrue("italic" in gw.get_cell_view((5, 4)).cell.style.font_style)
        self.assertEqual(gw.get_cell_view((6, 4)), None)


if __name__ == "__main__":
    unittest.main()
