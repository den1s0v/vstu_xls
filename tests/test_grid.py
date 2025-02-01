import unittest

from pathlib import Path


from tests_bootstrapper import init_testing_environment
init_testing_environment()


from geom2d import Box, Point, Direction, LEFT, RIGHT, UP, DOWN
from grid import Grid, Cell, TxtGrid


class GridTestCase(unittest.TestCase):
    def test_in_1(self):

        g = TxtGrid(Path('test_data/grid1.tsv').read_text())
        gw = g.get_view()
        print('grid.get_bounding_box:', g.get_bounding_box())
        print('grid-view range:', gw)

        self.assertEqual(tuple(gw), (0, 0, 9, 9))
        self.assertEqual((0, 0, 9, 9), tuple(gw))

        # Справа НАЛЕВО, снизу ВВЕРХ:
        for cell in gw.iterate_cells((LEFT, UP)):
            print(cell)

        col = gw.get_region(Box(0, 0, 1, 9))
        print('col-view range:', col)
        content_list = []
        # for point in col.iterate_points( [UP, RIGHT] ):
        #     # print(point)
        #     ...
        # Снизу ВВЕРХ, слева НАПРАВО:
        for cell in col.iterate_cells([UP, RIGHT]):
            print(cell)
            content_list.append(cell.cell.content)

        col_chars = ''.join(content_list)
        print(col_chars)

        # self.assertEqual(col_chars, '87654321')
        self.assertEqual(col_chars, '12345678')

        row = gw.get_region(Box(0, 0, 9, 1))
        print('row-view range:', row)
        content_list = []
        for cell in row.iterate_cells():
            print(cell)
            content_list.append(cell.cell.content)

        row_chars = ''.join(content_list)
        print(row_chars)

        self.assertEqual(row_chars, 'ABCDEFGH')

        rect = gw.get_region(Box(3, 3, 3, 3))
        print('rect-view range:', rect)
        for d in Direction.known_instances():
            outer = rect.look_outside(d)
            chars = (cell.cell.content for cell in outer.iterate_cells())
            print('rect-view range, %s:' % d.prop_name, outer)
            print('                   ', ''.join(chars))

        print()
        rect = gw.get_region(Box(2, 2, 5, 5))
        print('rect-view range:', rect)
        for d in Direction.known_instances():
            outer = rect.look_outside(d, distance=2)
            chars = (cell.cell.content for cell in outer.iterate_cells())
            print('rect-view range, %s:' % d.prop_name, outer)
            print('                   ', ''.join(chars))

        print()
        print('# zero distance')
        rect = gw.get_region(Box(2, 2, 4, 4))
        print('rect-view range:', rect)
        for d in Direction.known_instances():
            outer = rect.look_outside(d, distance=0)
            # chars = (cell.cell.content for cell in outer.iterateCells())
            print('rect-view range, %s:' % d.prop_name, outer)
            # print('                   ', ''.join(chars))

        print()
        print('# ignored distance')
        rect = gw.get_region(Box(2, 2, 4, 4))
        print('rect-view range:', rect)
        for d in Direction.known_instances():
            outer = rect.look_outside(d, distance=-10)  # ignored distance
            chars = (cell.cell.content for cell in outer.iterate_cells())
            print('rect-view range, %s:' % d.prop_name, outer)
            print('                   ', ''.join(chars))

        print()
        print('# too large distance, clamp.')
        rect = gw.get_region(Box(2, 2, 4, 4))
        print('rect-view range:', rect)
        for d in Direction.known_instances():
            outer = rect.look_outside(d, distance=999)  # too large distance, clamp.
            chars = (cell.cell.content for cell in outer.iterate_cells())
            print('rect-view range, %s:' % d.prop_name, outer)
            print('                   ', ''.join(chars))


if __name__ == '__main__':
    unittest.main()
    # GridTestCase.test_in_1(None)
