"""Source syntax helpers inspect trees without executing them."""

from copy import deepcopy
import unittest
from unittest.mock import patch

from MySolution.source_ast import ast
from MySolution.source_ops import CompilationError, pretty_source, validate_source


class SourceOperationTests(unittest.TestCase):
    def test_source_printing_covers_every_constructor(self) -> None:
        variable = ast.D0Evar("x")
        cases = [
            (ast.D0Eint(2), "2"), (ast.D0Ebtf(True), "true"),
            (ast.D0Ebtf(False), "false"), (variable, "x"),
            (ast.D0Elam("x", variable), "(lam x. x)"),
            (ast.D0Efix("f", "x", ast.D0Eapp(ast.D0Evar("f"), variable)), "(fix f(x). (f x))"),
            (ast.D0Eapp(ast.D0Evar("f"), variable), "(f x)"),
            (ast.D0Eop1("not", ast.D0Ebtf(True)), "(not true)"),
            (ast.D0Eop2("+", variable, ast.D0Eint(1)), "(x + 1)"),
            (ast.D0Eif0(ast.D0Ebtf(True), variable, ast.D0Eint(0)), "(if true then x else 0)"),
            (ast.D0Elet("x", ast.D0Eint(3), variable), "(let x = 3 in x)"),
            (ast.D0Epair(variable, ast.D0Ebtf(True)), "(pair x true)"),
            (ast.D0Epfst(variable), "(fst x)"), (ast.D0Epsnd(variable), "(snd x)"),
        ]
        for expression, expected in cases:
            with self.subTest(expression=expression):
                self.assertEqual(pretty_source(expression), expected)

    def test_printer_can_show_unsupported_syntax_without_validating_it(self) -> None:
        expression = ast.D0Eop2("/", ast.D0Eint(-1), ast.D0Eint(2))
        self.assertEqual(pretty_source(expression), "(-1 / 2)")
        with self.assertRaisesRegex(CompilationError, "unsupported binary operator"):
            validate_source(expression)

    def test_validation_collects_used_and_unused_names_including_fix_binders(self) -> None:
        expression = ast.D0Efix(
            "f", "x", ast.D0Elet(
                "unused", ast.D0Evar("initializer"),
                ast.D0Epair(ast.D0Evar("outside"), ast.D0Evar("x")),
            ),
        )
        self.assertEqual(
            validate_source(expression), frozenset({"f", "x", "unused", "initializer", "outside"}),
        )

    def test_helpers_do_not_execute_or_mutate_source(self) -> None:
        expression = ast.D0Eapp(
            ast.D0Elam("x", ast.D0Eapp(ast.D0Evar("x"), ast.D0Evar("x"))),
            ast.D0Elam("x", ast.D0Eapp(ast.D0Evar("x"), ast.D0Evar("x"))),
        )
        before = deepcopy(expression)
        with patch.object(ast, "d0exp_evaluate", side_effect=AssertionError("execution")):
            self.assertEqual(pretty_source(expression), "((lam x. (x x)) (lam x. (x x)))")
            self.assertEqual(validate_source(expression), frozenset({"x"}))
        self.assertEqual(expression, before)

    def test_invalid_source_names_and_roots_have_compilation_errors(self) -> None:
        for expression in (ast.D0Evar("bad-name"), ast.D0Elam("2x", ast.D0Eint(0))):
            with self.subTest(expression=expression):
                with self.assertRaisesRegex(CompilationError, "invalid source identifier"):
                    validate_source(expression)
        with self.assertRaisesRegex(CompilationError, "expected a source expression"):
            validate_source(None)
        with self.assertRaisesRegex(CompilationError, "unsupported expression"):
            validate_source(ast.D0E000())


if __name__ == "__main__":
    unittest.main()
