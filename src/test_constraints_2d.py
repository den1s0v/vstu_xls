import unittest
from geom2d import Box

from utils.sympy_expr import SympyExpr, register_sympy_as_expr_backend
from constraints_2d import SpatialConstraint

register_sympy_as_expr_backend()  # this registers subclass of SpatialConstraint


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
        sc = SpatialConstraint(expr)
        self.assertEqual(expr, str(sc))
        self.assertEqual('x + 1', str(sc._expr))
        self.assertEqual(6, sc.eval({'x': 5}))

    def test_read_and_eval_2(self):
        expr = 'y + + h'
        sc = SpatialConstraint(expr)
        self.assertEqual(expr, str(sc))
        self.assertEqual('h + y', str(sc._expr))
        self.assertEqual(6, sc.eval({'h': 5, 'y': 1}))

    def test_simple_replace(self):
        expr = '1 + b + a'
        sc = SpatialConstraint(expr)
        self.assertEqual(expr, str(sc))
        self.assertEqual('a + b + 1', str(sc._expr))
        sc.replace_vars({'a': 'Y'})
        self.assertEqual('Y + b + 1', str(sc._expr))

    def test_replace_to_values(self):
        expr = '1 + b + a'
        sc = SpatialConstraint(expr)
        self.assertEqual(expr, str(sc))
        self.assertEqual('a + b + 1', str(sc._expr))
        sc.replace_vars({'a': '5'})
        self.assertEqual('b + 6', str(sc._expr))

    def test_exchange_vars(self):
        expr = '1 - b / a'
        sc = SpatialConstraint(expr)
        self.assertEqual(expr, str(sc))
        self.assertEqual('(a - b)/a', str(sc._expr))
        sc.replace_vars({'a': 'b', 'b': 'a'})
        self.assertEqual('(-a + b)/b', str(sc._expr))

    def test_components_1(self):
        expr = 'a_x < b_L < c_R == R'
        sc = SpatialConstraint(expr)
        self.assertSetEqual(set(['a', 'b', 'c', '']), sc.referenced_components())

    def test_components_2(self):
        expr = '_y_z_a_x < b_L < c_R == L < _right'
        sc = SpatialConstraint(expr)
        self.assertSetEqual(set(['_y_z_a', 'b', 'c', '', '_']), sc.referenced_components())

    def test_components_3(self):
        expr = '_y_z_a_x < b_L < c_R == L < _right'
        sc = SpatialConstraint(expr)
        self.assertDictEqual({
            '_y_z_a': ['left'],
            'b': ['left'],
            'c': ['right'],
            '': ['left'],
            '_': ['right'], 
        }, sc.referenced_components_with_attributes())

    def test_components_4(self):
        expr = '_y_z_a_B < b_L < b_R == L < R'
        sc = SpatialConstraint(expr)
        self.assertDictEqual({
            '_y_z_a': ['bottom'],
            'b': ['left', 'right'],
            '': ['left', 'right'],
        }, sc.referenced_components_with_attributes())

    def test_replace_components_1(self):
        expr = 'G_x < G_L < G_R <= _L < G_right - W'
        sc = SpatialConstraint(expr)
        self.assertEqual('(G_R <= _L) & (G_L > G_x) & (G_L < G_R) & (G_right > W + _L)', str(sc._expr))
        sc.replace_components({'G': 'OTHER', '': 'this'})
        self.assertEqual('(OTHER_R <= _L) & (OTHER_L > OTHER_x) & (OTHER_L < OTHER_R) & (OTHER_right > _L + this_W)', str(sc))

    def test_replace_components_2(self):
        expr = '_L < G_right - W'
        sc = SpatialConstraint(expr)
        self.assertEqual('G_right > W + _L', str(sc._expr))
        sc.replace_components({'': 'this', '_': 'parent'})
        self.assertEqual('G_right > parent_L + this_W', str(sc))

    def test_eval_box_1(self):
        expr = 'W * height'
        sc = SpatialConstraint(expr)
        self.assertEqual('W*height', str(sc._expr))
        area = sc.eval_with_components({'this': Box(1, 1, 7, 9)})
        self.assertEqual(7 * 9, area)

    def test_eval_box_2(self):
        expr = 'x == 1 and y == 10 and left == x and top == y and right == 8 and bottom == 19'
        sc = SpatialConstraint(expr)
        area = sc.eval_with_components({'this': Box(1, 10, 7, 9)})
        self.assertEqual(True, area)

    def test_eval_box_3(self):
        # note x: 1 != 2, so full conjunction gives False.
        expr = 'x == 2 and y == 10 and left == x and top == y and right == 8 and bottom == 19'
        sc = SpatialConstraint(expr)
        area = sc.eval_with_components({'this': Box(1, 10, 7, 9)})
        self.assertEqual(False, area)




if __name__ == '__main__':
    unittest.main()
