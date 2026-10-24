"""CBV recursion, recursive scope, and required fix-based divergence cases."""

from copy import deepcopy
import unittest
from unittest.mock import patch

from MySolution import encodings as church
from MySolution.compiler import CompilationError, compile_expr
from MySolution.evaluator import evaluate
from MySolution.examples import factorial, fibonacci, loop
from MySolution.observers import observe
from MySolution.source_ast import ast
from MySolution.target import App, Lam, Var, alpha_equivalent, free_vars
from .test_compiler import source_data


class RecursiveCompilerTests(unittest.TestCase):
    def assert_pipeline(self, expression, expected, kind="natural") -> None:
        before = deepcopy(expression)
        source_answer = source_data(evaluate(expression).value)
        target = compile_expr(expression)
        self.assertEqual(free_vars(target), ast.d0exp_fvset(expression))
        execution = evaluate(target, max_steps=100000)
        self.assertEqual(execution.status, "completed")
        observation = observe(execution.value, kind, max_steps=100000)
        self.assertEqual(observation.status, "completed", observation.diagnostic)
        self.assertIs(type(observation.value), type(expected))
        self.assertEqual(observation.value, expected)
        self.assertEqual(observation.value, source_answer)
        self.assertEqual(expression, before)

    def test_z_matches_the_required_encoding_up_to_bound_names(self) -> None:
        arm = Lam("x", App(Var("g"), Lam("v", App(App(Var("x"), Var("x")), Var("v")))))
        expected = Lam("g", App(arm, arm))
        self.assertTrue(alpha_equivalent(church.z_combinator(), expected))

    def test_compiled_fix_is_z_applied_to_nested_function_and_parameter_binders(self) -> None:
        target = compile_expr(ast.D0Efix("f", "x", ast.D0Evar("x")))
        self.assertIsInstance(target, App)
        self.assertTrue(alpha_equivalent(target.fn, church.z_combinator()))
        self.assertEqual(target.arg, Lam("f", Lam("x", Var("x"))))

    def test_z_returns_an_unapplied_function_without_running_its_body(self) -> None:
        target = compile_expr(ast.D0Efix("f", "x", loop()))
        self.assertEqual(evaluate(target, max_steps=2).status, "exhausted")
        result = evaluate(target, max_steps=3)
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.steps, 3)
        self.assertIsInstance(result.value, Lam)
        # Supplying an argument enters the previously delayed divergent body.
        self.assertEqual(evaluate(App(target, church.numeral(0)), max_steps=100).status, "exhausted")

    def test_ordinary_y_unfolds_too_early_under_call_by_value(self) -> None:
        arm = Lam("x", App(Var("g"), App(Var("x"), Var("x"))))
        y = Lam("g", App(arm, arm))
        ignores_recursion = Lam("f", Lam("x", church.numeral(0)))
        self.assertEqual(evaluate(App(y, ignores_recursion), max_steps=50).status, "exhausted")
        self.assertEqual(evaluate(App(church.z_combinator(), ignores_recursion), max_steps=3).status,
                         "completed")

    def test_factorial_base_case_and_required_example(self) -> None:
        for number, expected in ((0, 1), (4, 24)):
            with self.subTest(number=number):
                self.assert_pipeline(ast.D0Eapp(factorial(), ast.D0Eint(number)), expected)

    def test_fibonacci_both_base_cases_and_required_example(self) -> None:
        for number, expected in ((0, 0), (1, 1), (5, 5)):
            with self.subTest(number=number):
                self.assert_pipeline(ast.D0Eapp(fibonacci(), ast.D0Eint(number)), expected)

    def test_coincident_function_and_parameter_names_respect_parameter_scope(self) -> None:
        function = ast.D0Efix("f", "f", ast.D0Evar("f"))
        expression = ast.D0Elet("f", ast.D0Eint(99), ast.D0Eapp(function, ast.D0Eint(3)))
        self.assert_pipeline(expression, 3)

    def test_local_let_can_shadow_the_recursive_name(self) -> None:
        function = ast.D0Efix("f", "x", ast.D0Elet("f", ast.D0Eint(7), ast.D0Evar("f")))
        self.assert_pipeline(ast.D0Eapp(function, ast.D0Eint(2)), 7)

    def test_local_lambda_can_shadow_the_parameter(self) -> None:
        function = ast.D0Efix("f", "x", ast.D0Eapp(
            ast.D0Elam("x", ast.D0Evar("x")), ast.D0Eint(8),
        ))
        self.assert_pipeline(ast.D0Eapp(function, ast.D0Eint(2)), 8)

    def test_recursive_function_keeps_definition_scope_when_caller_rebinds_names(self) -> None:
        function = ast.D0Efix("f", "n", ast.D0Eif0(
            ast.D0Eop2("==", ast.D0Evar("n"), ast.D0Eint(0)), ast.D0Evar("outside"),
            ast.D0Eapp(ast.D0Evar("f"), ast.D0Eop2("-", ast.D0Evar("n"), ast.D0Eint(1))),
        ))
        expression = ast.D0Elet("outside", ast.D0Eint(7), ast.D0Elet("saved", function,
            ast.D0Elet("outside", ast.D0Eint(99), ast.D0Elet("f", ast.D0Eint(88),
                ast.D0Eapp(ast.D0Evar("saved"), ast.D0Eint(2)),
            )),
        ))
        self.assert_pipeline(expression, 7)

    def test_open_recursive_compilation_preserves_free_names_and_is_pure(self) -> None:
        expression = ast.D0Efix("f", "n", ast.D0Epair(
            ast.D0Evar("g_1"), ast.D0Epair(ast.D0Evar("x_2"), ast.D0Evar("v_3")),
        ))
        target = compile_expr(expression)
        self.assertEqual(free_vars(target), frozenset({"g_1", "x_2", "v_3"}))
        pending = [target]
        while pending:
            term = pending.pop()
            self.assertIn(type(term), (Var, Lam, App))
            if isinstance(term, Lam):
                pending.append(term.body)
            elif isinstance(term, App):
                pending.extend((term.fn, term.arg))
        # Closing those names must preserve their meaning through Z and PAIR.
        closed = expression
        for name, number in (("g_1", 2), ("x_2", 3), ("v_3", 4)):
            closed = ast.D0Elet(name, ast.D0Eint(number), closed)
        self.assert_pipeline(ast.D0Eapp(closed, ast.D0Eint(0)), (2, (3, 4)),
                             ("pair", "natural", ("pair", "natural", "natural")))

    def test_recursion_can_return_nested_pairs(self) -> None:
        function = ast.D0Efix("f", "n", ast.D0Eif0(
            ast.D0Eop2("==", ast.D0Evar("n"), ast.D0Eint(0)),
            ast.D0Epair(ast.D0Epair(ast.D0Eint(2), ast.D0Ebtf(True)), ast.D0Eint(3)),
            ast.D0Eapp(ast.D0Evar("f"), ast.D0Eop2("-", ast.D0Evar("n"), ast.D0Eint(1))),
        ))
        self.assert_pipeline(ast.D0Eapp(function, ast.D0Eint(2)), ((2, True), 3),
                             ("pair", ("pair", "natural", "boolean"), "natural"))

    def test_required_loop_exhausts_exactly_the_given_budget(self) -> None:
        target = compile_expr(loop())
        for budget in (0, 1, 3, 100):
            with self.subTest(budget=budget):
                result = evaluate(target, max_steps=budget)
                self.assertEqual(result.status, "exhausted")
                self.assertEqual(result.steps, budget)

    def test_control_flow_skips_recursive_loop_when_unneeded(self) -> None:
        for expression, expected, kind in (
            (ast.D0Eif0(ast.D0Ebtf(True), ast.D0Eint(1), loop()), 1, "natural"),
            (ast.D0Eif0(ast.D0Ebtf(False), loop(), ast.D0Eint(2)), 2, "natural"),
            (ast.D0Eop2("and", ast.D0Ebtf(False), loop()), False, "boolean"),
            (ast.D0Eop2("or", ast.D0Ebtf(True), loop()), True, "boolean"),
        ):
            with self.subTest(expression=expression):
                self.assert_pipeline(expression, expected, kind)

    def test_selected_and_strict_computations_enter_recursive_loop(self) -> None:
        expressions = (
            ast.D0Eif0(ast.D0Ebtf(True), loop(), ast.D0Eint(1)),
            ast.D0Eif0(ast.D0Ebtf(False), ast.D0Eint(1), loop()),
            ast.D0Eop2("and", ast.D0Ebtf(True), loop()),
            ast.D0Eop2("or", ast.D0Ebtf(False), loop()),
            ast.D0Eapp(ast.D0Elam("unused", ast.D0Eint(0)), loop()),
            ast.D0Elet("unused", loop(), ast.D0Eint(2)),
            ast.D0Epfst(ast.D0Epair(ast.D0Eint(2), loop())),
            ast.D0Epsnd(ast.D0Epair(loop(), ast.D0Ebtf(True))),
        )
        for expression in expressions:
            with self.subTest(expression=expression):
                result = evaluate(compile_expr(expression), max_steps=100)
                self.assertEqual(result.status, "exhausted")
                self.assertEqual(result.steps, 100)

    def test_recursive_compilation_never_evaluates_and_preserves_inputs(self) -> None:
        with (
            patch("MySolution.evaluator.evaluate", side_effect=AssertionError("shared evaluator")),
            patch.object(ast, "d0exp_evaluate", side_effect=AssertionError("supplied evaluator")),
            patch.object(ast, "EvaluateVisitor", side_effect=AssertionError("evaluation visitor")),
        ):
            for expression in (factorial(), fibonacci(), loop()):
                before = deepcopy(expression)
                first = compile_expr(expression)
                self.assertEqual(first, compile_expr(expression))
                self.assertEqual(expression, before)

    def test_invalid_recursive_bodies_are_rejected_even_when_never_called(self) -> None:
        for bad in (ast.D0Eint(-1), ast.D0Eop2("/", ast.D0Eint(4), ast.D0Eint(2))):
            function = ast.D0Efix("f", "x", bad)
            for expression in (function, ast.D0Eif0(ast.D0Ebtf(True), ast.D0Eint(1), function)):
                with self.subTest(expression=expression):
                    with self.assertRaises(CompilationError):
                        compile_expr(expression)


if __name__ == "__main__":
    unittest.main()
