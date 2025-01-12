import unittest

from tests_bootstrapper import init_testing_environment
init_testing_environment()

from geom2d import Box

from constraints_2d import AlgebraicExpr, SizeConstraint, LocationConstraint
from constraints_2d import SympyExpr
from constraints_2d import constraints_for_box_inside_container, trivial_constraints_for_box


class sumpy_expr_TestCase(unittest.TestCase):

    def test_1(self):
        expr = '1 + + A_x'
        ex = SympyExpr(expr)
        self.assertEqual(expr, str(ex))
        self.assertEqual('A_x + 1', str(ex._expr))
        self.assertEqual(6, ex.eval({'A_x': 5}))
        ex.replace_vars({'A_x': 'y'})
        self.assertEqual('y + 1', str(ex._expr))
        ex.replace_vars()
        self.assertEqual('y + 1', str(ex._expr))
        ex.replace_vars({'A_x': 'z'})  # 'A_x' is no more in the exr, so it wouldn't change.
        self.assertEqual('y + 1', str(ex._expr))


class constraints_2d_TestCase(unittest.TestCase):

    def test_read_and_eval(self):
        expr = '1 + + x'
        sc = AlgebraicExpr(expr)
        self.assertEqual(expr, str(sc))
        self.assertEqual('x + 1', str(sc._expr))
        self.assertEqual(6, sc.eval({'x': 5}))

    def test_read_and_eval_2(self):
        expr = 'y + + h'
        sc = AlgebraicExpr(expr)
        self.assertEqual(expr, str(sc))
        self.assertEqual('h + y', str(sc._expr))
        self.assertEqual(6, sc.eval({'h': 5, 'y': 1}))

    def test_simple_replace(self):
        expr = '1 + b + a'
        sc = AlgebraicExpr(expr)
        self.assertEqual(expr, str(sc))
        self.assertEqual('a + b + 1', str(sc._expr))
        sc.replace_vars({'a': 'Y'})
        self.assertEqual('Y + b + 1', str(sc._expr))

    def test_replace_to_values(self):
        expr = '1 + b + a'
        sc = AlgebraicExpr(expr)
        self.assertEqual(expr, str(sc))
        self.assertEqual('a + b + 1', str(sc._expr))
        sc.replace_vars({'a': '5'})
        self.assertEqual('b + 6', str(sc._expr))

    def test_exchange_vars(self):
        expr = '1 - b / a'
        sc = AlgebraicExpr(expr)
        self.assertEqual(expr, str(sc))
        self.assertEqual('(a - b)/a', str(sc._expr))
        sc.replace_vars({'a': 'b', 'b': 'a'})
        self.assertEqual('(-a + b)/b', str(sc._expr))

    def test_components_1(self):
        expr = 'a_x < b_L < c_R == R'
        sc = AlgebraicExpr(expr)
        self.assertSetEqual(set(['a', 'b', 'c', '']), sc.referenced_components())

    def test_components_2(self):
        expr = '_y_z_a_x < b_L < c_R == L < _right'
        sc = AlgebraicExpr(expr)
        self.assertSetEqual(set(['_y_z_a', 'b', 'c', '', '_']), sc.referenced_components())

    def test_components_3(self):
        expr = '_y_z_a_x < b_L < c_R == L < _right'
        sc = AlgebraicExpr(expr)
        self.assertDictEqual({
            '_y_z_a': ['left'],
            'b': ['left'],
            'c': ['right'],
            '': ['left'],
            '_': ['right'],
        }, sc.referenced_components_with_attributes())

    def test_components_4(self):
        expr = '_y_z_a_B < b_L < b_R == L < R'
        sc = AlgebraicExpr(expr)
        self.assertDictEqual({
            '_y_z_a': ['bottom'],
            'b': ['left', 'right'],
            '': ['left', 'right'],
        }, sc.referenced_components_with_attributes())

    def test_replace_components_1(self):
        expr = 'G_x < G_L < G_R <= _L < G_right - W'
        sc = AlgebraicExpr(expr)
        self.assertEqual('(G_R <= _L) & (G_L > G_x) & (G_L < G_R) & (G_right > W + _L)', str(sc._expr))
        sc.replace_components({'G': 'OTHER', '': 'this'})
        self.assertEqual('(OTHER_R <= _L) & (OTHER_L > OTHER_x) & (OTHER_L < OTHER_R) & (OTHER_right > _L + this_W)', str(sc))

    def test_replace_components_2(self):
        expr = '_L < G_right - W'
        sc = AlgebraicExpr(expr)
        self.assertEqual('G_right > W + _L', str(sc._expr))
        sc.replace_components({'': 'this', '_': 'parent'})
        self.assertEqual('G_right > parent_L + this_W', str(sc))

    def test_eval_box_1(self):
        expr = 'W * height'
        sc = AlgebraicExpr(expr)
        self.assertEqual('W*height', str(sc._expr))
        area = sc.eval_with_components({'this': Box(1, 1, 7, 9)})
        self.assertEqual(7 * 9, area)

    def test_eval_box_2(self):
        expr = 'x == 1 and y == 10 and left == x and top == y and right == 8 and bottom == 19'
        sc = AlgebraicExpr(expr)
        area = sc.eval_with_components({'this': Box(1, 10, 7, 9)})
        self.assertEqual(True, area)

    def test_eval_box_3(self):
        # note x: 1 != 2, so full conjunction gives False.
        expr = 'x == 2 and y == 10 and left == x and top == y and right == 8 and bottom == 19'
        sc = AlgebraicExpr(expr)
        area = sc.eval_with_components({'this': Box(1, 10, 7, 9)})
        self.assertEqual(False, area)


class constraints_for_box_TestCase(unittest.TestCase):

    def test_1(self):
        name = 'element'
        cs = trivial_constraints_for_box(name)

        box = Box(1,2, 3,4)
        self.assertTrue(cs.eval_with_components({name: box}))

    def test_2(self):
        name = 'room'
        container = 'element'
        cs = constraints_for_box_inside_container(name, container)

        # included
        box1 = Box(1,2, 3,4)
        box2 = Box(1,1, 3,6)
        self.assertTrue(cs.eval_with_components({name: box1, container: box2, }))
        self.assertFalse(cs.eval_with_components({name: box2, container: box1, }))

        # overlap
        box1 = Box(1,1, 4,4)
        box2 = Box(2,2, 5,5)
        self.assertFalse(cs.eval_with_components({name: box1, container: box2, }))
        self.assertFalse(cs.eval_with_components({name: box2, container: box1, }))

        # equal
        box1 = Box(1,2, 3,4)
        box2 = Box(1,2, 3,4)
        self.assertTrue(cs.eval_with_components({name: box1, container: box2, }))
        self.assertTrue(cs.eval_with_components({name: box2, container: box1, }))


class SizeConstraintTestCase(unittest.TestCase):

    def test_1(self):
        name = 'this'
        cs = SizeConstraint(size_range_str='4+ x 1..2')

        box = Box(1,2, 4,1)
        self.assertTrue(cs.eval(box.as_dict()))

        box = Box(1,2, 5,0)
        self.assertFalse(cs.eval(box.as_dict()))

        box = Box(1,2, 4,1)
        self.assertTrue(cs.eval_with_components({name: box}))

        box = Box(1,2, 5,2)
        self.assertTrue(cs.eval_with_components({name: box}))

        box = Box(1,2, 3,4)
        self.assertFalse(cs.eval_with_components({name: box}))

        box = Box(1,2, 5,0)
        self.assertFalse(cs.eval_with_components({name: box}))


class LocationConstraintTestCase(unittest.TestCase):

    def test_inside(self):
        cs = LocationConstraint(sides_str='bottom, right', check_implicit_sides=False)

        parent_box = Box.from_2points(0,0, 10,10)

        # matches itself
        self.assertTrue(cs.eval_with_components(dict(this=parent_box, parent=parent_box)))

        box = Box.from_2points(9,9, 10,10)
        self.assertTrue(cs.eval_with_components(dict(this=box, parent=parent_box)))

        box = Box.from_2points(1,2, 10,10)
        self.assertTrue(cs.eval_with_components(dict(this=box, parent=parent_box)))

        # negative tests
        box = Box.from_2points(1,2, 9,10)
        self.assertFalse(cs.eval_with_components(dict(this=box, parent=parent_box)))

        box = Box.from_2points(1,2, 11,10)
        self.assertFalse(cs.eval_with_components(dict(this=box, parent=parent_box)))

        box = Box.from_2points(1,2, 10,9)
        self.assertFalse(cs.eval_with_components(dict(this=box, parent=parent_box)))

        box = Box.from_2points(1,2, 10,11)
        self.assertFalse(cs.eval_with_components(dict(this=box, parent=parent_box)))

        # Note: no constraints on other sides!
        box = Box.from_2points(-15,-15, 10,10)
        self.assertTrue(cs.eval_with_components(dict(this=box, parent=parent_box)))

    def test_inside_with_implicit_sides(self):
        cs = LocationConstraint(
            sides_str='bottom, right',
            # check_implicit_sides=True
        )

        parent_box = Box.from_2points(0,0, 10,10)

        # matches itself
        self.assertTrue(cs.eval_with_components(dict(this=parent_box, parent=parent_box)))

        box = Box.from_2points(9,9, 10,10)

        self.assertTrue(cs.eval_with_components(dict(this=box, parent=parent_box)))

        box = Box.from_2points(1,2, 10,10)
        self.assertTrue(cs.eval_with_components(dict(this=box, parent=parent_box)))

        # negative tests
        box = Box.from_2points(1,2, 9,10)
        self.assertFalse(cs.eval_with_components(dict(this=box, parent=parent_box)))

        box = Box.from_2points(1,2, 11,10)
        self.assertFalse(cs.eval_with_components(dict(this=box, parent=parent_box)))

        box = Box.from_2points(1,2, 10,9)
        self.assertFalse(cs.eval_with_components(dict(this=box, parent=parent_box)))

        box = Box.from_2points(1,2, 10,11)
        self.assertFalse(cs.eval_with_components(dict(this=box, parent=parent_box)))

        # Note: constraints on other sides work to keep inner inside!
        box = Box.from_2points(-15,-15, 10,10)
        self.assertFalse(cs.eval_with_components(dict(this=box, parent=parent_box)))

        box = Box.from_2points(0,-15, 10,10)
        self.assertFalse(cs.eval_with_components(dict(this=box, parent=parent_box)))

        box = Box.from_2points(-15,0, 10,10)
        self.assertFalse(cs.eval_with_components(dict(this=box, parent=parent_box)))

    def test_outside(self):
        cs = LocationConstraint(sides_str='bottom', inside=False, check_implicit_sides=False)

        parent_box = Box.from_2points(0,0, 10,10)

        # Does not match itself
        self.assertFalse(cs.eval_with_components(dict(this=parent_box, parent=parent_box)))

        # zero gap
        box = Box.from_2points(0,10, 10,15)
        self.assertTrue(cs.eval_with_components(dict(this=box, parent=parent_box)))

        box = Box.from_2points(1,12, 10,10)
        self.assertTrue(cs.eval_with_components(dict(this=box, parent=parent_box)))

        # positive gap
        box = Box.from_2points(1,11, 5,20)
        self.assertTrue(cs.eval_with_components(dict(this=box, parent=parent_box)))

        box = Box.from_2points(1,15, 5,20)
        self.assertTrue(cs.eval_with_components(dict(this=box, parent=parent_box)))

        box = Box.from_2points(-1,150, 1,200)
        self.assertTrue(cs.eval_with_components(dict(this=box, parent=parent_box)))

        box = Box.from_2points(9,150, 11,200)
        self.assertTrue(cs.eval_with_components(dict(this=box, parent=parent_box)))

        # negative gap
        box = Box.from_2points(1,9, 10,20)
        self.assertFalse(cs.eval_with_components(dict(this=box, parent=parent_box)))

        box = Box.from_2points(1,-9, 10,0)
        self.assertFalse(cs.eval_with_components(dict(this=box, parent=parent_box)))

        box = Box.from_2points(1,-20, 10,-10)
        self.assertFalse(cs.eval_with_components(dict(this=box, parent=parent_box)))

        # shift out horizontally (OK when check_implicit_sides=False)
        box = Box.from_2points(-10,10, 0,11)
        self.assertTrue(cs.eval_with_components(dict(this=box, parent=parent_box)))

        box = Box.from_2points(-10,10, -5,11)
        self.assertTrue(cs.eval_with_components(dict(this=box, parent=parent_box)))

        box = Box.from_2points(10,10, 15,11)
        self.assertTrue(cs.eval_with_components(dict(this=box, parent=parent_box)))

        box = Box.from_2points(20,10, 50,11)
        self.assertTrue(cs.eval_with_components(dict(this=box, parent=parent_box)))

    def test_outside_with_implicit_sides(self):
        cs = LocationConstraint(
            sides_str='bottom',
            inside=False,
            # check_implicit_sides=True
        )

        parent_box = Box.from_2points(0,0, 10,10)

        # Does not match itself
        self.assertFalse(cs.eval_with_components(dict(this=parent_box, parent=parent_box)))

        # zero gap
        box = Box.from_2points(0,10, 10,15)
        self.assertTrue(cs.eval_with_components(dict(this=box, parent=parent_box)))

        box = Box.from_2points(1,12, 10,10)
        self.assertTrue(cs.eval_with_components(dict(this=box, parent=parent_box)))

        # positive gap
        box = Box.from_2points(1,11, 5,20)
        self.assertTrue(cs.eval_with_components(dict(this=box, parent=parent_box)))

        box = Box.from_2points(1,15, 5,20)
        self.assertTrue(cs.eval_with_components(dict(this=box, parent=parent_box)))

        box = Box.from_2points(-1,150, 1,200)
        self.assertTrue(cs.eval_with_components(dict(this=box, parent=parent_box)))

        box = Box.from_2points(9,150, 11,200)
        self.assertTrue(cs.eval_with_components(dict(this=box, parent=parent_box)))

        # negative gap
        box = Box.from_2points(1,9, 10,20)
        self.assertFalse(cs.eval_with_components(dict(this=box, parent=parent_box)))

        box = Box.from_2points(1,-9, 10,0)
        self.assertFalse(cs.eval_with_components(dict(this=box, parent=parent_box)))

        box = Box.from_2points(1,-20, 10,-10)
        self.assertFalse(cs.eval_with_components(dict(this=box, parent=parent_box)))

        # shift out horizontally (FAIL when check_implicit_sides=True)
        box = Box.from_2points(-10,10, 0,11)
        self.assertFalse(cs.eval_with_components(dict(this=box, parent=parent_box)))

        box = Box.from_2points(-10,10, -5,11)
        self.assertFalse(cs.eval_with_components(dict(this=box, parent=parent_box)))

        box = Box.from_2points(10,10, 15,11)
        self.assertFalse(cs.eval_with_components(dict(this=box, parent=parent_box)))

        box = Box.from_2points(20,10, 50,11)
        self.assertFalse(cs.eval_with_components(dict(this=box, parent=parent_box)))

    def test_outside_with_two_sides(self):
        cs = LocationConstraint(
            # "looks" at bottom left corner:
            sides_str='bottom left',
            inside=False,
            # check_implicit_sides=True
        )

        parent_box = Box.from_2points(0,0, 10,10)

        # Does not match itself
        self.assertFalse(cs.eval_with_components(dict(this=parent_box, parent=parent_box)))

        # zero gap (both or one side)
        box = Box.from_2points(-10,20, 0,10)
        self.assertTrue(cs.eval_with_components(dict(this=box, parent=parent_box)))

        box = Box.from_2points(-10,20, -1,10)
        self.assertTrue(cs.eval_with_components(dict(this=box, parent=parent_box)))

        box = Box.from_2points(-10,20, 0,11)
        self.assertTrue(cs.eval_with_components(dict(this=box, parent=parent_box)))

        # positive gap
        box = Box.from_2points(-10,20, -1,11)
        self.assertTrue(cs.eval_with_components(dict(this=box, parent=parent_box)))

        box = Box.from_2points(-100,200, -150, 150)
        self.assertTrue(cs.eval_with_components(dict(this=box, parent=parent_box)))

        # negative gap
        box = Box.from_2points(-10,20, 1,10)
        self.assertFalse(cs.eval_with_components(dict(this=box, parent=parent_box)))

        box = Box.from_2points(-10,20, 0,9)
        self.assertFalse(cs.eval_with_components(dict(this=box, parent=parent_box)))

        box = Box.from_2points(-10,20, 1,9)
        self.assertFalse(cs.eval_with_components(dict(this=box, parent=parent_box)))

        # shift right horizontally
        box = Box.from_2points(-5,20, 5,10)
        self.assertFalse(cs.eval_with_components(dict(this=box, parent=parent_box)))

        box = Box.from_2points(5,20, 15,10)
        self.assertFalse(cs.eval_with_components(dict(this=box, parent=parent_box)))

        box = Box.from_2points(10,20, 15,10)
        self.assertFalse(cs.eval_with_components(dict(this=box, parent=parent_box)))

        box = Box.from_2points(100,20, 150,10)
        self.assertFalse(cs.eval_with_components(dict(this=box, parent=parent_box)))

    def test_inside_with_range_gaps(self):
        cs = LocationConstraint(side_to_gap=dict(
            left='2..4',
            top ='2..4',
            right ='1..3',
            bottom='1..3',
        ))

        parent_box = Box.from_2points(0,0, 10,10)

        # cannot match itself
        self.assertFalse(cs.eval_with_components(dict(this=parent_box, parent=parent_box)))

        # smallest
        box = Box.from_2points(4,4, 7,7)
        self.assertTrue(cs.eval_with_components(dict(this=box, parent=parent_box)))

        # largest
        box = Box.from_2points(2,2, 9,9)
        self.assertTrue(cs.eval_with_components(dict(this=box, parent=parent_box)))

        # negative tests
        # smaller than smallest
        box = Box.from_2points(5,4, 7,7)
        self.assertFalse(cs.eval_with_components(dict(this=box, parent=parent_box)))

        box = Box.from_2points(4,5, 7,7)
        self.assertFalse(cs.eval_with_components(dict(this=box, parent=parent_box)))

        box = Box.from_2points(4,4, 6,7)
        self.assertFalse(cs.eval_with_components(dict(this=box, parent=parent_box)))

        box = Box.from_2points(4,4, 7,6)
        self.assertFalse(cs.eval_with_components(dict(this=box, parent=parent_box)))

        # larger than largest
        box = Box.from_2points(1,2, 9,9)
        self.assertFalse(cs.eval_with_components(dict(this=box, parent=parent_box)))

        box = Box.from_2points(2,1, 9,9)
        self.assertFalse(cs.eval_with_components(dict(this=box, parent=parent_box)))

        box = Box.from_2points(2,2, 10,9)
        self.assertFalse(cs.eval_with_components(dict(this=box, parent=parent_box)))

        box = Box.from_2points(2,2, 9,10)
        self.assertFalse(cs.eval_with_components(dict(this=box, parent=parent_box)))

    def test_inside_with_constant_gap(self):
        cs = LocationConstraint(side_to_gap=dict(
            left='4',
            top ='4',
            right ='3',
            bottom='3',
        ))

        parent_box = Box.from_2points(0,0, 10,10)

        # cannot match itself
        self.assertFalse(cs.eval_with_components(dict(this=parent_box, parent=parent_box)))

        # valid
        box = Box.from_2points(4,4, 7,7)
        self.assertTrue(cs.eval_with_components(dict(this=box, parent=parent_box)))

        # negative tests
        # smaller
        box = Box.from_2points(5,4, 7,7)
        self.assertFalse(cs.eval_with_components(dict(this=box, parent=parent_box)))

        box = Box.from_2points(4,5, 7,7)
        self.assertFalse(cs.eval_with_components(dict(this=box, parent=parent_box)))

        box = Box.from_2points(4,4, 6,7)
        self.assertFalse(cs.eval_with_components(dict(this=box, parent=parent_box)))

        box = Box.from_2points(4,4, 7,6)
        self.assertFalse(cs.eval_with_components(dict(this=box, parent=parent_box)))

        # larger
        box = Box.from_2points(3,4, 7,7)
        self.assertFalse(cs.eval_with_components(dict(this=box, parent=parent_box)))

        box = Box.from_2points(4,3, 7,7)
        self.assertFalse(cs.eval_with_components(dict(this=box, parent=parent_box)))

        box = Box.from_2points(4,4, 8,7)
        self.assertFalse(cs.eval_with_components(dict(this=box, parent=parent_box)))

        box = Box.from_2points(4,4, 7,8)
        self.assertFalse(cs.eval_with_components(dict(this=box, parent=parent_box)))


if __name__ == '__main__':
    unittest.main()
