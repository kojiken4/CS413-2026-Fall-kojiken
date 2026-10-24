"""Verify source-AST integration; these are not compiler correctness tests."""

from copy import deepcopy
from pathlib import Path
import subprocess
import sys
import unittest

from MySolution.source_ast import ast


class SourceIntegrationTests(unittest.TestCase):
    def test_adapter_loads_the_supplied_file(self) -> None:
        assignment_dir = Path(__file__).resolve().parents[2]
        expected = assignment_dir.parent / "05" / "lambda1_vp.py"
        self.assertEqual(Path(ast.__file__).resolve(), expected.resolve())
        self.assertIs(sys.modules[ast.D0Eint.__module__], ast)

    def test_source_expression_is_built_from_supplied_classes(self) -> None:
        expression = ast.D0Eop2("+", ast.D0Eint(2), ast.D0Eint(3))

        self.assertIsInstance(expression, ast.D0E000)
        self.assertEqual(expression.name, "+")
        self.assertEqual(expression.arg1, ast.D0Eint(2))
        self.assertEqual(expression.arg2, ast.D0Eint(3))

    def test_supplied_visitor_traverses_syntax_without_changing_it(self) -> None:
        expression = ast.D0Eapp(
            ast.D0Elam(
                "x", ast.D0Eop2("+", ast.D0Evar("x"), ast.D0Evar("offset"))
            ),
            ast.D0Eint(4),
        )
        before = deepcopy(expression)
        visitor = ast.FreeVariableVisitor()

        self.assertIsInstance(visitor, ast.D0ExpVisitor)
        self.assertEqual(expression.accept(visitor), frozenset({"offset"}))
        self.assertEqual(expression, before)

    def test_unrelated_same_named_module_does_not_replace_source_ast(self) -> None:
        # A fresh process exercises the initial import, not an already cached one.
        script = """
import sys
from types import ModuleType

unrelated = ModuleType("lambda1_vp")
sys.modules["lambda1_vp"] = unrelated
from MySolution.source_ast import ast

assert ast.D0Eint(2).arg1 == 2
assert ast is not unrelated
assert sys.modules["lambda1_vp"] is unrelated
"""
        result = subprocess.run(
            [sys.executable, "-B", "-c", script],
            cwd=Path(__file__).resolve().parents[2],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
