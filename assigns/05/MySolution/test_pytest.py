"""Independent pytest-style suite; run from the assignment directory."""

import lambda1_vp as ast
from MySolution import operations


def test_solution_module_imports():
    assert operations.__name__ == "MySolution.operations"


def test_supplied_ast_dispatches_to_visitor():
    expression = ast.D0Elam(
        "x", ast.D0Eop2("+", ast.D0Evar("x"), ast.D0Evar("y"))
    )
    assert expression.accept(ast.FreeVariableVisitor()) == frozenset({"y"})
