"""
Синтаксический разбор подмножества Python в выражение SymPy.


### Постановка для GPT:

In Sympy library, sympify() or S() does not support chaining comparisons. But plain python does. Write a converter that parses an expression using Python's ast module and constructs a Sympy expression.
I've corrected your code so it works (see below). Please add support for boolean AND, OR, NOT, for unary minus, and for floor-division (//).

>   Great job on the corrections! Let's extend your implementation to include support for boolean operations (AND, OR, NOT), unary minus, and floor division (//).
>    Key Additions:
1. Boolean Operations: Support for and and or using ast.BoolOp.
2. Unary Operations: Support for unary plus (+) and unary minus (-) using ast.UnaryOp.
3. Floor Division: Support for floor division (//) using ast.FloorDiv.

> Example Usage:

> You can test this implementation with expressions like `a < b <= c and d > e or not f` to see how it translates into SymPy expressions.

Доработано:
 - `==` / `!=` как Eq / Ne в SymPy
 - abs(...) для одного аргумента
 - min(...), max(...) для произвольного числа аргументов
 - ternary: IfExpr -> Piecewise

 """

import ast
from sympy import symbols, And, Or, Not, Eq, Ne, Piecewise, Min, Max, S

# Define a mapping from Python operators to SymPy functions
operator_map = {
    ast.Eq: lambda left, right: Eq(left, right),
    ast.NotEq: lambda left, right: Ne(left, right),  # `Ne` is the same as `~Eq`
    ast.Lt: lambda left, right: left < right,
    ast.LtE: lambda left, right: left <= right,
    ast.Gt: lambda left, right: left > right,
    ast.GtE: lambda left, right: left >= right,
}

# Function to convert a Python AST node to a SymPy expression
def ast_to_sympy(node):
    if isinstance(node, ast.Compare):
        # Handle chained comparisons
        comparisons = []
        for i in range(len(node.ops)):
            if i == 0:
                comparisons.append(operator_map[type(node.ops[i])](ast_to_sympy(node.left), ast_to_sympy(node.comparators[i])))
            else:
                comparisons.append(operator_map[type(node.ops[i])](ast_to_sympy(node.comparators[i-1]), ast_to_sympy(node.comparators[i])))
        return And(*comparisons)

    elif isinstance(node, ast.BinOp):
        left = ast_to_sympy(node.left)
        right = ast_to_sympy(node.right)
        if isinstance(node.op, ast.Add):
            return left + right
        elif isinstance(node.op, ast.Sub):
            return left - right
        elif isinstance(node.op, ast.Mult):
            return left * right
        elif isinstance(node.op, ast.Div):
            return left / right
        elif isinstance(node.op, ast.FloorDiv):
            return left // right

    elif isinstance(node, ast.UnaryOp):
        if isinstance(node.op, ast.UAdd):
            return +ast_to_sympy(node.operand)  # Unary plus
        elif isinstance(node.op, ast.USub):
            return -ast_to_sympy(node.operand)  # Unary minus
        elif isinstance(node.op, ast.Not):
            return Not(ast_to_sympy(node.operand))  # Logical NOT

    elif isinstance(node, ast.BoolOp):
        left = ast_to_sympy(node.values[0])
        for value in node.values[1:]:
            right = ast_to_sympy(value)
            if isinstance(node.op, ast.And):
                left = And(left, right)
            elif isinstance(node.op, ast.Or):
                left = Or(left, right)
        return left

    elif isinstance(node, ast.Call):
        func_name = node.func.id
        args_n = len(node.args)
        if func_name == 'abs':
            assert 1 == args_n, f"Exact one argument for abs() expected, but got {args_n} arguments."
            return abs(ast_to_sympy(node.args[0]))
        if func_name in ('min', 'max'):
            assert 1 <= args_n, f"At least one argument for {func_name}() expected, but got {args_n} arguments."
            sympy_func = globals()[func_name.capitalize()]
            return sympy_func(*(ast_to_sympy(arg) for arg in node.args))

    elif isinstance(node, ast.IfExp):
        # Handle the ternary operator (conditional expression)
        test = ast_to_sympy(node.test)
        body = ast_to_sympy(node.body)
        orelse = ast_to_sympy(node.orelse)
        return Piecewise((body, test), (orelse, True))  # see docs: https://docs.sympy.org/latest/modules/functions/elementary.html#piecewise

    elif isinstance(node, ast.Name):
        return symbols(node.id)

    elif isinstance(node, ast.Constant):
        return S(node.value)

    raise NotImplementedError(f"Unsupported AST node type: {type(node)}")


# Main function to convert an expression string to a SymPy expression
def parse_expression(expr_str: str):
    """Converts an expression string to a SymPy expression

    Args:
        expr_str (str): one-line expression using scalars, variables, relation & arithmetic operations.

    Returns:
        _type_: SymPy expr
    """
    # Parse the expression string into an AST
    tree = ast.parse(expr_str, mode='eval')
    # Convert the AST to a SymPy expression
    return ast_to_sympy(tree.body)



"""
# Example usage
if __name__ == "__main__":
    expr = "zz == (a < b == c and d > e != g > h or not f)"
    sympy_expr = parse_expression(expr)
    print(sympy_expr)
→
Eq(zz, ~f | (Eq(b, c) & (d > e) & (g > h) & (a < b) & Ne(e, g)))

# Example usage
expr = "zz * abs(ww - pp)"
sympy_expr = parse_expression(expr)
print(sympy_expr)
print('=>', sympy_expr.subs('ww', 10).subs('pp', 50))
→
zz*Abs(pp - ww)
=> 40*zz

# Example usage
expr = "max(min(zz), abs(ww - pp))"
sympy_expr = parse_expression(expr)
print(sympy_expr)
print('=>', sympy_expr.subs('ww', 10).subs('pp', 50))
→
Max(zz, Abs(pp - ww))
=> Max(40, zz)

# Example usage
expr = "a < b if c else d"
sympy_expr = parse_expression(expr)
print(sympy_expr)
→
Piecewise((a < b, c), (d, True))


# Example usage
expr = "3 if x > 2 else 1"
sympy_expr = parse_expression(expr)
print(sympy_expr)
print(0, '=>', sympy_expr.subs('x', 0))
print(4, '=>', sympy_expr.subs('x', 4))
→
Piecewise((3, x > 2), (1, True))
0 => 1
4 => 3

"""