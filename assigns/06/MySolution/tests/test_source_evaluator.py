"""Source semantics in the shared engine; never run a divergent source directly."""

from copy import deepcopy
import unittest
from unittest.mock import patch

from MySolution.evaluator import SourceEvaluationError, evaluate
from MySolution.source_ast import ast
from MySolution.target import App, Lam, Var


def loop() -> ast.d0exp:
    return ast.D0Eapp(
        ast.D0Efix("loop", "x", ast.D0Eapp(ast.D0Evar("loop"), ast.D0Evar("x"))),
        ast.D0Eint(0),
    )


def factorial() -> ast.D0Efix:
    return ast.D0Efix(
        "fact", "n",
        ast.D0Eif0(
            ast.D0Eop2("==", ast.D0Evar("n"), ast.D0Eint(0)),
            ast.D0Eint(1),
            ast.D0Eop2(
                "*", ast.D0Evar("n"),
                ast.D0Eapp(
                    ast.D0Evar("fact"),
                    ast.D0Eop2("-", ast.D0Evar("n"), ast.D0Eint(1)),
                ),
            ),
        ),
    )


def fibonacci() -> ast.D0Efix:
    return ast.D0Efix(
        "fib", "n",
        ast.D0Eif0(
            ast.D0Eop2("<=", ast.D0Evar("n"), ast.D0Eint(1)),
            ast.D0Evar("n"),
            ast.D0Eop2(
                "+",
                ast.D0Eapp(
                    ast.D0Evar("fib"),
                    ast.D0Eop2("-", ast.D0Evar("n"), ast.D0Eint(1)),
                ),
                ast.D0Eapp(
                    ast.D0Evar("fib"),
                    ast.D0Eop2("-", ast.D0Evar("n"), ast.D0Eint(2)),
                ),
            ),
        ),
    )


class SourceEvaluationTests(unittest.TestCase):
    def assert_source_value(self, expression: ast.d0exp, expected: ast.d0val) -> None:
        result = evaluate(expression)
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.value, expected)
        self.assertIs(result.value, result.term)
        self.assertIsNone(result.steps)
        self.assertIsNone(result.budget)

    def test_natural_and_boolean_literals(self) -> None:
        for number in (0, 3):
            with self.subTest(number=number):
                self.assert_source_value(ast.D0Eint(number), ast.D0Vint(number))
        for boolean in (False, True):
            with self.subTest(boolean=boolean):
                self.assert_source_value(ast.D0Ebtf(boolean), ast.D0Vbtf(boolean))

    def test_arithmetic_including_truncated_subtraction(self) -> None:
        cases = [
            ("+", 2, 3, 5), ("+", 0, 0, 0),
            ("-", 5, 2, 3), ("-", 2, 5, 0), ("-", 2, 2, 0),
            ("*", 3, 4, 12), ("*", 3, 0, 0), ("*", 0, 3, 0),
        ]
        for operator, left, right, expected in cases:
            with self.subTest(operator=operator, left=left, right=right):
                self.assert_source_value(
                    ast.D0Eop2(operator, ast.D0Eint(left), ast.D0Eint(right)),
                    ast.D0Vint(expected),
                )

    def test_all_comparisons_with_equal_and_unequal_operands(self) -> None:
        # Results for operands (2, 3), (3, 2), and (2, 2), respectively.
        cases = {
            "<": (True, False, False), "<=": (True, False, True),
            ">": (False, True, False), ">=": (False, True, True),
            "==": (False, False, True), "!=": (True, True, False),
        }
        for operator, answers in cases.items():
            for (left, right), answer in zip(((2, 3), (3, 2), (2, 2)), answers):
                with self.subTest(operator=operator, left=left, right=right):
                    self.assert_source_value(
                        ast.D0Eop2(operator, ast.D0Eint(left), ast.D0Eint(right)),
                        ast.D0Vbtf(answer),
                    )

    def test_boolean_negation(self) -> None:
        self.assert_source_value(ast.D0Eop1("not", ast.D0Ebtf(True)), ast.D0Vbtf(False))
        self.assert_source_value(ast.D0Eop1("not", ast.D0Ebtf(False)), ast.D0Vbtf(True))

    def test_complete_boolean_truth_tables(self) -> None:
        cases = [
            (False, False, False, False), (False, True, False, True),
            (True, False, False, True), (True, True, True, True),
        ]
        for left, right, conjunction, disjunction in cases:
            for operator, answer in (("and", conjunction), ("or", disjunction)):
                with self.subTest(operator=operator, left=left, right=right):
                    self.assert_source_value(
                        ast.D0Eop2(operator, ast.D0Ebtf(left), ast.D0Ebtf(right)),
                        ast.D0Vbtf(answer),
                    )

    def test_nested_arithmetic_example(self) -> None:
        self.assert_source_value(
            ast.D0Eop2("+", ast.D0Eint(2), ast.D0Eop2("*", ast.D0Eint(3), ast.D0Eint(4))),
            ast.D0Vint(14),
        )

    def test_higher_order_application(self) -> None:
        expression = ast.D0Eapp(
            ast.D0Elam("f", ast.D0Eapp(ast.D0Evar("f"), ast.D0Eint(3))),
            ast.D0Elam("x", ast.D0Eop2("+", ast.D0Evar("x"), ast.D0Eint(1))),
        )
        self.assert_source_value(expression, ast.D0Vint(4))

    def test_lambda_returns_a_closure_without_running_its_body(self) -> None:
        expression = ast.D0Elam("x", ast.D0Evar("not_evaluated"))
        result = evaluate(expression)
        self.assertIsInstance(result.value, ast.D0Vlam)
        self.assertEqual(result.value.arg1, ast.ENVnil())
        self.assertIs(result.value.arg2, expression)
        self.assertIsNone(result.steps)

    def test_closure_uses_its_defining_environment(self) -> None:
        expression = ast.D0Elet(
            "x", ast.D0Eint(3),
            ast.D0Elet(
                "f", ast.D0Elam("y", ast.D0Eop2("+", ast.D0Evar("x"), ast.D0Evar("y"))),
                ast.D0Elet("x", ast.D0Eint(99), ast.D0Eapp(ast.D0Evar("f"), ast.D0Eint(4))),
            ),
        )
        self.assert_source_value(expression, ast.D0Vint(7))

    def test_function_scope_does_not_leak_into_argument_evaluation(self) -> None:
        expression = ast.D0Elet(
            "x", ast.D0Eint(10),
            ast.D0Eapp(
                ast.D0Elet(
                    "x", ast.D0Eint(3),
                    ast.D0Elam("y", ast.D0Eop2("+", ast.D0Evar("x"), ast.D0Evar("y"))),
                ),
                ast.D0Evar("x"),
            ),
        )
        self.assert_source_value(expression, ast.D0Vint(13))

    def test_lambda_parameter_shadows_outer_binding(self) -> None:
        expression = ast.D0Elet(
            "x", ast.D0Eint(99),
            ast.D0Eapp(ast.D0Elam("x", ast.D0Evar("x")), ast.D0Eint(3)),
        )
        self.assert_source_value(expression, ast.D0Vint(3))

    def test_let_initializer_uses_outer_binding(self) -> None:
        expression = ast.D0Elet(
            "x", ast.D0Eint(3),
            ast.D0Elet(
                "x", ast.D0Eop2("+", ast.D0Evar("x"), ast.D0Eint(1)), ast.D0Evar("x"),
            ),
        )
        self.assert_source_value(expression, ast.D0Vint(4))

    def test_let_does_not_bind_its_initializer(self) -> None:
        expression = ast.D0Elet("x", ast.D0Evar("x"), ast.D0Evar("x"))
        with self.assertRaisesRegex(SourceEvaluationError, "unbound source variable: x"):
            evaluate(expression)

    def test_initializer_scope_does_not_leak_into_let_body(self) -> None:
        expression = ast.D0Elet(
            "x", ast.D0Eint(10),
            ast.D0Elet(
                "y", ast.D0Elet("x", ast.D0Eint(3), ast.D0Evar("x")),
                ast.D0Eop2("+", ast.D0Evar("x"), ast.D0Evar("y")),
            ),
        )
        self.assert_source_value(expression, ast.D0Vint(13))

    def test_left_operand_scope_does_not_leak_into_right_operand(self) -> None:
        expression = ast.D0Elet(
            "x", ast.D0Eint(10),
            ast.D0Eop2(
                "+", ast.D0Elet("x", ast.D0Eint(3), ast.D0Evar("x")), ast.D0Evar("x"),
            ),
        )
        self.assert_source_value(expression, ast.D0Vint(13))

    def test_condition_scope_does_not_leak_into_selected_branch(self) -> None:
        expression = ast.D0Elet(
            "x", ast.D0Eint(10),
            ast.D0Eif0(
                ast.D0Elet("x", ast.D0Eint(3), ast.D0Ebtf(True)),
                ast.D0Evar("x"), ast.D0Eint(0),
            ),
        )
        self.assert_source_value(expression, ast.D0Vint(10))

    def test_both_conditional_outcomes_skip_unselected_divergence(self) -> None:
        self.assert_source_value(
            ast.D0Eif0(ast.D0Ebtf(True), ast.D0Eint(1), loop()), ast.D0Vint(1),
        )
        self.assert_source_value(
            ast.D0Eif0(ast.D0Ebtf(False), loop(), ast.D0Eint(9)), ast.D0Vint(9),
        )

    def test_boolean_operations_skip_unneeded_divergence(self) -> None:
        self.assert_source_value(
            ast.D0Eop2("and", ast.D0Ebtf(False), loop()), ast.D0Vbtf(False),
        )
        self.assert_source_value(
            ast.D0Eop2("or", ast.D0Ebtf(True), loop()), ast.D0Vbtf(True),
        )

    def test_boolean_operations_evaluate_a_required_right_operand(self) -> None:
        for operator, left in (("and", True), ("or", False)):
            with self.subTest(operator=operator):
                with self.assertRaisesRegex(SourceEvaluationError, "right_operand"):
                    evaluate(ast.D0Eop2(operator, ast.D0Ebtf(left), ast.D0Evar("right_operand")))

    def test_boolean_operand_scope_is_restored(self) -> None:
        expression = ast.D0Elet(
            "flag", ast.D0Ebtf(False),
            ast.D0Eop2(
                "or", ast.D0Elet("flag", ast.D0Ebtf(True), ast.D0Ebtf(False)),
                ast.D0Evar("flag"),
            ),
        )
        self.assert_source_value(expression, ast.D0Vbtf(False))

    def test_pairs_projections_and_nested_pairs(self) -> None:
        pair = ast.D0Epair(ast.D0Eint(2), ast.D0Ebtf(True))
        self.assert_source_value(pair, ast.D0Vpair(ast.D0Vint(2), ast.D0Vbtf(True)))
        self.assert_source_value(ast.D0Epfst(pair), ast.D0Vint(2))
        self.assert_source_value(ast.D0Epsnd(pair), ast.D0Vbtf(True))
        self.assert_source_value(
            ast.D0Epair(pair, ast.D0Eint(3)),
            ast.D0Vpair(ast.D0Vpair(ast.D0Vint(2), ast.D0Vbtf(True)), ast.D0Vint(3)),
        )

    def test_pair_component_scope_is_restored(self) -> None:
        expression = ast.D0Elet(
            "x", ast.D0Eint(10),
            ast.D0Epair(ast.D0Elet("x", ast.D0Eint(3), ast.D0Evar("x")), ast.D0Evar("x")),
        )
        self.assert_source_value(expression, ast.D0Vpair(ast.D0Vint(3), ast.D0Vint(10)))

    def test_a_pair_can_hold_a_callable_closure(self) -> None:
        expression = ast.D0Eapp(
            ast.D0Epfst(ast.D0Epair(
                ast.D0Elam("x", ast.D0Eop2("+", ast.D0Evar("x"), ast.D0Eint(1))),
                ast.D0Ebtf(True),
            )),
            ast.D0Eint(3),
        )
        self.assert_source_value(expression, ast.D0Vint(4))

    def test_left_to_right_order_with_finite_error_probes(self) -> None:
        # Unbound variables reveal traversal order without running divergent sources.
        cases = [
            ast.D0Eapp(ast.D0Evar("first"), ast.D0Evar("second")),
            ast.D0Eop2("+", ast.D0Evar("first"), ast.D0Evar("second")),
            ast.D0Eop2("<", ast.D0Evar("first"), ast.D0Evar("second")),
            ast.D0Epair(ast.D0Evar("first"), ast.D0Evar("second")),
        ]
        for expression in cases:
            with self.subTest(expression=expression):
                with self.assertRaisesRegex(SourceEvaluationError, "unbound source variable: first"):
                    evaluate(expression)

    def test_unused_arguments_initializers_and_pair_components_are_strict(self) -> None:
        cases = [
            ast.D0Eapp(ast.D0Elam("unused", ast.D0Eint(0)), ast.D0Evar("required")),
            ast.D0Elet("unused", ast.D0Evar("required"), ast.D0Eint(2)),
            ast.D0Epfst(ast.D0Epair(ast.D0Eint(2), ast.D0Evar("required"))),
            ast.D0Epsnd(ast.D0Epair(ast.D0Evar("required"), ast.D0Ebtf(True))),
        ]
        for expression in cases:
            with self.subTest(expression=expression):
                with self.assertRaisesRegex(SourceEvaluationError, "required"):
                    evaluate(expression)

    def test_factorial_base_case_and_recursive_calls(self) -> None:
        for argument, expected in ((0, 1), (4, 24)):
            with self.subTest(argument=argument):
                self.assert_source_value(
                    ast.D0Eapp(factorial(), ast.D0Eint(argument)), ast.D0Vint(expected),
                )

    def test_fibonacci_base_cases_and_recursive_calls(self) -> None:
        for argument, expected in ((0, 0), (1, 1), (5, 5)):
            with self.subTest(argument=argument):
                self.assert_source_value(
                    ast.D0Eapp(fibonacci(), ast.D0Eint(argument)), ast.D0Vint(expected),
                )

    def test_fix_returns_a_closure_without_unfolding(self) -> None:
        function = loop().arg1
        result = evaluate(function)
        self.assertEqual(result.status, "completed")
        self.assertIsInstance(result.value, ast.D0Vfix)
        self.assertIs(result.value.arg2, function)

    def test_coincident_fix_parameter_shadows_function_and_outer_name(self) -> None:
        expression = ast.D0Elet(
            "f", ast.D0Eint(99),
            ast.D0Eapp(ast.D0Efix("f", "f", ast.D0Evar("f")), ast.D0Eint(3)),
        )
        self.assert_source_value(expression, ast.D0Vint(3))

    def test_recursive_closure_uses_its_defining_environment(self) -> None:
        function = ast.D0Efix(
            "f", "n",
            ast.D0Eif0(
                ast.D0Eop2("==", ast.D0Evar("n"), ast.D0Eint(0)),
                ast.D0Evar("base"),
                ast.D0Eapp(ast.D0Evar("f"), ast.D0Eop2("-", ast.D0Evar("n"), ast.D0Eint(1))),
            ),
        )
        expression = ast.D0Elet(
            "base", ast.D0Eint(7),
            ast.D0Elet(
                "f", function,
                ast.D0Elet("base", ast.D0Eint(99), ast.D0Eapp(ast.D0Evar("f"), ast.D0Eint(2))),
            ),
        )
        self.assert_source_value(expression, ast.D0Vint(7))

    def test_caller_rebinding_does_not_replace_recursive_self_reference(self) -> None:
        expression = ast.D0Elet(
            "fact", factorial(),
            ast.D0Elet(
                "saved", ast.D0Evar("fact"),
                ast.D0Elet(
                    "fact", ast.D0Elam("n", ast.D0Eint(999)),
                    ast.D0Eapp(ast.D0Evar("saved"), ast.D0Eint(4)),
                ),
            ),
        )
        self.assert_source_value(expression, ast.D0Vint(24))

    def test_many_terminating_recursive_calls_use_the_same_loop(self) -> None:
        countdown = ast.D0Efix(
            "f", "n",
            ast.D0Eif0(
                ast.D0Eop2("==", ast.D0Evar("n"), ast.D0Eint(0)), ast.D0Eint(0),
                ast.D0Eapp(ast.D0Evar("f"), ast.D0Eop2("-", ast.D0Evar("n"), ast.D0Eint(1))),
            ),
        )
        self.assert_source_value(ast.D0Eapp(countdown, ast.D0Eint(2000)), ast.D0Vint(0))

    def test_source_inputs_are_unchanged_and_calls_do_not_share_bindings(self) -> None:
        expression = ast.D0Eapp(factorial(), ast.D0Eint(4))
        before = deepcopy(expression)
        first, second = evaluate(expression), evaluate(expression)
        self.assertEqual(first, second)
        self.assertEqual(expression, before)
        self.assert_source_value(ast.D0Elet("x", ast.D0Eint(3), ast.D0Evar("x")), ast.D0Vint(3))
        with self.assertRaisesRegex(SourceEvaluationError, "unbound source variable: x"):
            evaluate(ast.D0Evar("x"))

    def test_unsupported_reached_literals_and_operator_spellings(self) -> None:
        cases = [
            (ast.D0Eint(-1), "negative literal.*-1"),
            (ast.D0Eop1("+1", ast.D0Eint(2)), "unsupported unary operator.*\\+1"),
            (ast.D0Eop1("-1", ast.D0Eint(2)), "unsupported unary operator.*-1"),
            (ast.D0Eop2("/", ast.D0Eint(4), ast.D0Eint(2)), "unsupported binary operator.*/"),
            (ast.D0Eop2("&&", ast.D0Ebtf(True), ast.D0Ebtf(False)), "unsupported binary operator.*&&"),
        ]
        for expression, diagnostic in cases:
            with self.subTest(expression=expression):
                with self.assertRaisesRegex(SourceEvaluationError, diagnostic):
                    evaluate(expression)

    def test_clear_errors_for_misused_source_values(self) -> None:
        cases = [
            (ast.D0Eif0(ast.D0Eint(0), ast.D0Eint(1), ast.D0Eint(2)), "boolean"),
            (ast.D0Eop1("not", ast.D0Eint(0)), "boolean"),
            (ast.D0Eop2("+", ast.D0Ebtf(True), ast.D0Eint(2)), "natural-number"),
            (ast.D0Eapp(ast.D0Eint(0), ast.D0Eint(1)), "function"),
            (ast.D0Epfst(ast.D0Eint(0)), "pair"),
        ]
        for expression, diagnostic in cases:
            with self.subTest(expression=expression):
                with self.assertRaisesRegex(SourceEvaluationError, diagnostic):
                    evaluate(expression)

    def test_source_budget_is_rejected_rather_than_silently_ignored(self) -> None:
        with self.assertRaisesRegex(TypeError, "source evaluation is unbounded; omit max_steps"):
            evaluate(ast.D0Eint(0), max_steps=1)


class EngineBoundaryTests(unittest.TestCase):
    def test_source_does_not_delegate_to_interpreter_or_target_substitution(self) -> None:
        with (
            patch.object(ast, "d0exp_evaluate", side_effect=AssertionError("separate evaluator")),
            patch.object(ast, "EvaluateVisitor", side_effect=AssertionError("separate visitor")),
            patch("MySolution.evaluator.substitute", side_effect=AssertionError("target path")),
        ):
            self.assertEqual(
                evaluate(ast.D0Eapp(factorial(), ast.D0Eint(4))).value, ast.D0Vint(24),
            )

    def test_target_execution_does_not_call_source_operations(self) -> None:
        identity = Lam("x", Var("x"))
        with patch(
            "MySolution.evaluator._apply_source_binary",
            side_effect=AssertionError("source operation in target path"),
        ):
            result = evaluate(App(identity, identity), max_steps=1)
        self.assertEqual(result.value, identity)
        self.assertEqual(result.steps, 1)


if __name__ == "__main__":
    unittest.main()
