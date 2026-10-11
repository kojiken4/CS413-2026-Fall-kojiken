"""Independent unittest suite; run from the assignment directory."""

import unittest

import lambda1_vp as ast
from MySolution import operations


class SolutionSmokeTests(unittest.TestCase):
    def test_solution_module_imports(self):
        self.assertEqual(operations.__name__, "MySolution.operations")

    def test_supplied_ast_dispatches_to_visitor(self):
        expression = ast.D0Elam(
            "x", ast.D0Eop2("+", ast.D0Evar("x"), ast.D0Evar("y"))
        )
        self.assertEqual(
            expression.accept(ast.FreeVariableVisitor()), frozenset({"y"})
        )


if __name__ == "__main__":
    unittest.main()
