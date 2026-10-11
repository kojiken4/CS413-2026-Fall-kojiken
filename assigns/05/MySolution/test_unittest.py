"""Independent unittest suite; run from the assignment directory."""

from copy import deepcopy
import unittest
from unittest.mock import patch

import lambda1_vp as ast
from MySolution import operations
from MySolution.helper_cases import all_names_cases, scoped_rename_cases


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


class PrettyPrintTests(unittest.TestCase):
    def test_exact_output_for_every_constructor(self):
        cases = [
            (ast.D0Eint(0), "0"),
            (ast.D0Eint(-7), "-7"),
            (ast.D0Eint(123456789012345678901234567890), "123456789012345678901234567890"),
            (ast.D0Ebtf(True), "true"),
            (ast.D0Ebtf(False), "false"),
            (ast.D0Evar("_value2"), "_value2"),
            (ast.D0Eop1("+1", ast.D0Evar("x")), "(+1 x)"),
            (ast.D0Eop2("+", ast.D0Evar("x"), ast.D0Eint(1)), "(x + 1)"),
            (ast.D0Elam("x", ast.D0Evar("x")), "(lam x. x)"),
            (ast.D0Efix("f", "n", ast.D0Evar("n")), "(fix f(n). n)"),
            (ast.D0Eapp(ast.D0Evar("f"), ast.D0Eint(4)), "(f 4)"),
            (ast.D0Eif0(ast.D0Ebtf(True), ast.D0Eint(1), ast.D0Eint(2)), "(if true then 1 else 2)"),
            (ast.D0Elet("x", ast.D0Eint(3), ast.D0Evar("x")), "(let x = 3 in x)"),
            (ast.D0Epair(ast.D0Eint(1), ast.D0Eint(2)), "(pair 1 2)"),
            (ast.D0Epfst(ast.D0Evar("p")), "(fst p)"),
            (ast.D0Epsnd(ast.D0Evar("p")), "(snd p)"),
        ]
        visitor = operations.PrettyPrintVisitor()
        for expression, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(operations.d0exp_pretty(expression), expected)
                self.assertEqual(expression.accept(visitor), expected)

    def test_nested_application_matches_assignment_example(self):
        expression = ast.D0Eapp(
            ast.D0Elam("x", ast.D0Eop2("+", ast.D0Evar("x"), ast.D0Eint(1))),
            ast.D0Eint(4),
        )
        self.assertEqual(operations.d0exp_pretty(expression), "((lam x. (x + 1)) 4)")

    def test_nested_bindings_and_projections(self):
        expression = ast.D0Elet(
            "p", ast.D0Epair(ast.D0Eint(-2), ast.D0Ebtf(False)),
            ast.D0Efix("f", "n", ast.D0Eif0(
                ast.D0Epsnd(ast.D0Evar("p")),
                ast.D0Epfst(ast.D0Evar("p")),
                ast.D0Eapp(ast.D0Evar("f"), ast.D0Eop1("-1", ast.D0Evar("n"))),
            )),
        )
        self.assertEqual(
            operations.d0exp_pretty(expression),
            "(let p = (pair -2 false) in (fix f(n). (if (snd p) then (fst p) else (f (-1 n)))))",
        )

    def test_names_and_operators_are_inserted_literally(self):
        expression = ast.D0Eop2("custom_op", ast.D0Eop1("neg", ast.D0Evar("_x2")), ast.D0Eint(8))
        self.assertEqual(operations.d0exp_pretty(expression), "((neg _x2) custom_op 8)")

    def test_printing_does_not_evaluate(self):
        expression = ast.D0Eop2("/", ast.D0Eint(1), ast.D0Eint(0))
        with patch.object(ast.EvaluateVisitor, "visit_op2", side_effect=AssertionError("unexpected evaluation")):
            self.assertEqual(operations.d0exp_pretty(expression), "(1 / 0)")

    def test_printing_preserves_input(self):
        expression = ast.D0Elam("x", ast.D0Epair(ast.D0Evar("x"), ast.D0Eint(1)))
        snapshot = deepcopy(expression)
        self.assertEqual(operations.d0exp_pretty(expression), "(lam x. (pair x 1))")
        self.assertEqual(expression, snapshot)


class NameHelperTests(unittest.TestCase):
    def test_all_names_including_unused_binders(self):
        visitor = operations.AllNamesVisitor()
        for expression, expected in all_names_cases():
            with self.subTest(expression=expression):
                snapshot = deepcopy(expression)
                self.assertEqual(expression.accept(visitor), expected)
                self.assertEqual(expression, snapshot)

    def test_scoped_renaming_and_input_preservation(self):
        visitor = operations.ScopedRenameVisitor("x", "x_1")
        for expression, expected in scoped_rename_cases():
            with self.subTest(expression=expression):
                snapshot = deepcopy(expression)
                self.assertEqual(expression.accept(visitor), expected)
                self.assertEqual(expression, snapshot)

    def test_helpers_do_not_evaluate(self):
        expression = ast.D0Eop2("/", ast.D0Evar("x"), ast.D0Eint(0))
        with patch.object(ast.EvaluateVisitor, "visit_op2", side_effect=AssertionError("unexpected evaluation")):
            self.assertEqual(expression.accept(operations.AllNamesVisitor()), frozenset({"x"}))
            self.assertEqual(
                expression.accept(operations.ScopedRenameVisitor("x", "x_1")),
                ast.D0Eop2("/", ast.D0Evar("x_1"), ast.D0Eint(0)),
            )

    def test_fresh_names_avoid_both_inputs_and_target(self):
        expression = ast.D0Elam("y_1", ast.D0Evar("x"))
        replacement = ast.D0Elam("y_2", ast.D0Evar("y"))
        target = "y_3"
        reserved = (
            expression.accept(operations.AllNamesVisitor())
            | replacement.accept(operations.AllNamesVisitor())
            | {target}
        )
        generator = operations.FreshNameGenerator(reserved)
        self.assertEqual(generator.fresh("y"), "y_4")
        self.assertEqual(generator.fresh("y"), "y_5")
        self.assertEqual(generator.fresh("f"), "f_6")
        self.assertEqual(reserved, frozenset({"y_1", "x", "y_2", "y", "y_3"}))

    def test_fresh_names_are_unique_and_deterministic(self):
        first = operations.FreshNameGenerator(frozenset())
        second = operations.FreshNameGenerator(frozenset())
        expected = ["y_1", "y_2", "f_3", "_x_4"]
        self.assertEqual([first.fresh(name) for name in ("y", "y", "f", "_x")], expected)
        self.assertEqual([second.fresh(name) for name in ("y", "y", "f", "_x")], expected)
        self.assertEqual(len(set(expected)), len(expected))


if __name__ == "__main__":
    unittest.main()
