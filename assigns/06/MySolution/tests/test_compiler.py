"""Nonrecursive source-to-target meaning, scope, delayed branches, and diagnostics."""

from copy import deepcopy
import unittest
from unittest.mock import patch

from MySolution import compiler
from MySolution.compiler import CompilationError, compile_expr
from MySolution.evaluator import evaluate
from MySolution.observers import observe
from MySolution.source_ast import ast
from MySolution.source_ops import validate_source
from MySolution.target import App, Lam, Var, free_vars


def omega() -> ast.d0exp:
    # A nonrecursive stress fixture, available before the required fix/LOOP support.
    function = ast.D0Elam("x", ast.D0Eapp(ast.D0Evar("x"), ast.D0Evar("x")))
    return ast.D0Eapp(function, function)


def source_data(value):
    if isinstance(value, (ast.D0Vint, ast.D0Vbtf)):
        return value.arg1
    if isinstance(value, ast.D0Vpair):
        return source_data(value.arg1), source_data(value.arg2)
    raise AssertionError("expected source data, not a function")


class NonrecursiveCompilerTests(unittest.TestCase):
    def assert_pure_with_preserved_free_vars(self, source, target) -> None:
        pending = [target]
        while pending:
            current = pending.pop()
            self.assertIn(type(current), (Var, Lam, App))
            if isinstance(current, Lam):
                pending.append(current.body)
            elif isinstance(current, App):
                pending.extend((current.fn, current.arg))
        self.assertEqual(free_vars(target), ast.d0exp_fvset(source))

    def assert_pipeline(self, expression, kind, expected) -> None:
        before = deepcopy(expression)
        source = evaluate(expression)
        source_answer = source_data(source.value)
        self.assertIs(type(source_answer), type(expected))
        self.assertEqual(source_answer, expected)
        target = compile_expr(expression)
        self.assert_pure_with_preserved_free_vars(expression, target)
        execution = evaluate(target, max_steps=50000)
        self.assertEqual(execution.status, "completed")
        observed = observe(execution.value, kind, max_steps=50000)
        self.assertEqual(observed.status, "completed", observed.diagnostic)
        self.assertIs(type(observed.value), type(expected))
        self.assertEqual(observed.value, expected)
        self.assertEqual(observed.value, source_answer)
        self.assertEqual(expression, before)

    def test_natural_and_boolean_literals(self) -> None:
        for literal in (0, 3):
            with self.subTest(literal=literal):
                self.assert_pipeline(ast.D0Eint(literal), "natural", literal)
        for literal in (False, True):
            with self.subTest(literal=literal):
                self.assert_pipeline(ast.D0Ebtf(literal), "boolean", literal)

    def test_variables_lambdas_and_applications_translate_structurally(self) -> None:
        expression = ast.D0Eapp(ast.D0Elam("x", ast.D0Evar("x")), ast.D0Evar("outside"))
        target = compile_expr(expression)
        self.assertEqual(target, App(Lam("x", Var("x")), Var("outside")))
        self.assert_pure_with_preserved_free_vars(expression, target)
        identity = compile_expr(ast.D0Elam("x", ast.D0Evar("x")))
        self.assertEqual(evaluate(identity, max_steps=0).value, Lam("x", Var("x")))

    def test_all_arithmetic_operators(self) -> None:
        for operator, left, right, answer in (
            ("+", 0, 0, 0), ("+", 2, 3, 5), ("-", 2, 5, 0),
            ("-", 5, 2, 3), ("*", 3, 4, 12), ("*", 0, 3, 0),
        ):
            with self.subTest(operator=operator, left=left, right=right):
                self.assert_pipeline(
                    ast.D0Eop2(operator, ast.D0Eint(left), ast.D0Eint(right)), "natural", answer,
                )

    def test_all_comparison_operators(self) -> None:
        cases = {
            "<": (True, False, False), "<=": (True, False, True),
            ">": (False, True, False), ">=": (False, True, True),
            "==": (False, False, True), "!=": (True, True, False),
        }
        for operator, answers in cases.items():
            for (left, right), answer in zip(((2, 3), (3, 2), (2, 2)), answers):
                with self.subTest(operator=operator, left=left, right=right):
                    self.assert_pipeline(
                        ast.D0Eop2(operator, ast.D0Eint(left), ast.D0Eint(right)), "boolean", answer,
                    )

    def test_boolean_negation(self) -> None:
        for operand, answer in ((True, False), (False, True)):
            with self.subTest(operand=operand):
                self.assert_pipeline(ast.D0Eop1("not", ast.D0Ebtf(operand)), "boolean", answer)

    def test_complete_and_or_truth_tables(self) -> None:
        for left, right, conjunction, disjunction in (
            (False, False, False, False), (False, True, False, True),
            (True, False, False, True), (True, True, True, True),
        ):
            for operator, answer in (("and", conjunction), ("or", disjunction)):
                with self.subTest(operator=operator, left=left, right=right):
                    self.assert_pipeline(
                        ast.D0Eop2(operator, ast.D0Ebtf(left), ast.D0Ebtf(right)), "boolean", answer,
                    )

    def test_both_conditional_outcomes(self) -> None:
        for condition, answer in ((True, 7), (False, 9)):
            with self.subTest(condition=condition):
                self.assert_pipeline(
                    ast.D0Eif0(ast.D0Ebtf(condition), ast.D0Eint(7), ast.D0Eint(9)), "natural", answer,
                )

    def test_required_arithmetic_example(self) -> None:
        self.assert_pipeline(
            ast.D0Eop2("+", ast.D0Eint(2), ast.D0Eop2("*", ast.D0Eint(3), ast.D0Eint(4))),
            "natural", 14,
        )

    def test_required_comparison_conditional(self) -> None:
        self.assert_pipeline(
            ast.D0Eif0(
                ast.D0Eop2("<=", ast.D0Eint(2), ast.D0Eint(3)), ast.D0Eint(7), ast.D0Eint(9),
            ), "natural", 7,
        )

    def test_required_let_and_function_example(self) -> None:
        self.assert_pipeline(
            ast.D0Elet("x", ast.D0Eint(3), ast.D0Eapp(
                ast.D0Elam("y", ast.D0Eop2("+", ast.D0Evar("x"), ast.D0Evar("y"))),
                ast.D0Eint(4),
            )), "natural", 7,
        )

    def test_required_higher_order_example(self) -> None:
        self.assert_pipeline(
            ast.D0Eapp(
                ast.D0Elam("f", ast.D0Eapp(ast.D0Evar("f"), ast.D0Eint(3))),
                ast.D0Elam("x", ast.D0Eop2("+", ast.D0Evar("x"), ast.D0Eint(1))),
            ), "natural", 4,
        )

    def test_mixed_pair_and_both_projections(self) -> None:
        pair = ast.D0Epair(ast.D0Eint(2), ast.D0Ebtf(True))
        self.assert_pipeline(pair, ("pair", "natural", "boolean"), (2, True))
        self.assert_pipeline(ast.D0Epfst(pair), "natural", 2)
        self.assert_pipeline(ast.D0Epsnd(pair), "boolean", True)

    def test_nested_pairs(self) -> None:
        expression = ast.D0Epair(ast.D0Epair(ast.D0Eint(2), ast.D0Ebtf(True)), ast.D0Eint(3))
        self.assert_pipeline(expression, ("pair", ("pair", "natural", "boolean"), "natural"), ((2, True), 3))

    def test_lexical_function_scope(self) -> None:
        expression = ast.D0Elet("x", ast.D0Eint(3), ast.D0Elet(
            "f", ast.D0Elam("y", ast.D0Eop2("+", ast.D0Evar("x"), ast.D0Evar("y"))),
            ast.D0Elet("x", ast.D0Eint(99), ast.D0Eapp(ast.D0Evar("f"), ast.D0Eint(4))),
        ))
        self.assert_pipeline(expression, "natural", 7)

    def test_nested_lets_and_lambdas_with_shadowing(self) -> None:
        expression = ast.D0Elet("x", ast.D0Eint(2), ast.D0Eop2(
            "+", ast.D0Elet("x", ast.D0Eint(3), ast.D0Eapp(
                ast.D0Elam("x", ast.D0Eop2("+", ast.D0Evar("x"), ast.D0Eint(1))),
                ast.D0Eint(4),
            )), ast.D0Evar("x"),
        ))
        self.assert_pipeline(expression, "natural", 7)

    def test_let_initializer_scope(self) -> None:
        expression = ast.D0Elet("x", ast.D0Eint(3), ast.D0Elet(
            "x", ast.D0Eop2("+", ast.D0Evar("x"), ast.D0Eint(1)), ast.D0Evar("x"),
        ))
        self.assert_pipeline(expression, "natural", 4)
        open_expression = ast.D0Elet("x", ast.D0Evar("x"), ast.D0Evar("x"))
        target = compile_expr(open_expression)
        self.assertEqual(target, App(Lam("x", Var("x")), Var("x")))
        self.assertEqual(free_vars(target), frozenset({"x"}))

    def test_common_encoding_names_remain_available_to_source_programs(self) -> None:
        for name in ("s", "z", "t", "f", "x", "u", "v", "w", "s_1", "u_1", "v_2"):
            with self.subTest(name=name):
                expression = ast.D0Elet(name, ast.D0Eint(3), ast.D0Eif0(
                    ast.D0Ebtf(True), ast.D0Eop2("+", ast.D0Evar(name), ast.D0Eint(4)), ast.D0Eint(9),
                ))
                self.assert_pipeline(expression, "natural", 7)

    def test_open_forms_preserve_their_free_variable_sets(self) -> None:
        cases = [
            ast.D0Evar("s"), ast.D0Evar("TRUE"), ast.D0Evar("Z"),
            ast.D0Elam("x", ast.D0Eapp(ast.D0Evar("f"), ast.D0Evar("x"))),
            ast.D0Eapp(ast.D0Evar("f"), ast.D0Evar("z")),
            ast.D0Eop1("not", ast.D0Evar("p")),
            ast.D0Eop2("and", ast.D0Evar("t"), ast.D0Evar("f")),
            ast.D0Eop2("or", ast.D0Evar("t"), ast.D0Evar("f")),
            ast.D0Eop2("==", ast.D0Evar("m"), ast.D0Evar("n")),
            ast.D0Eif0(ast.D0Evar("c"), ast.D0Evar("u_1"), ast.D0Evar("v_2")),
            ast.D0Elet("x", ast.D0Evar("x"), ast.D0Eop2("+", ast.D0Evar("x"), ast.D0Evar("outside"))),
            ast.D0Epair(ast.D0Evar("s"), ast.D0Evar("z")),
            ast.D0Epfst(ast.D0Evar("p")), ast.D0Epsnd(ast.D0Evar("p")),
        ]
        for expression in cases:
            with self.subTest(expression=expression):
                self.assert_pure_with_preserved_free_vars(expression, compile_expr(expression))

    def test_thunk_parameters_avoid_free_and_unused_bound_source_names(self) -> None:
        expression = ast.D0Eif0(
            ast.D0Evar("c"), ast.D0Elam("u_1", ast.D0Evar("x")), ast.D0Evar("v_3"),
        )
        target = compile_expr(expression)
        then_thunk, else_thunk = target.fn.fn.arg, target.fn.arg
        self.assertIsInstance(then_thunk, Lam)
        self.assertIsInstance(else_thunk, Lam)
        self.assertNotIn(then_thunk.name, validate_source(expression))
        self.assertNotIn(else_thunk.name, validate_source(expression))
        self.assert_pure_with_preserved_free_vars(expression, target)

    def test_unused_valid_branches_are_preserved_in_output(self) -> None:
        cases = [
            ast.D0Eif0(ast.D0Ebtf(True), ast.D0Eint(1), ast.D0Evar("outside")),
            ast.D0Eop2("and", ast.D0Ebtf(False), ast.D0Evar("outside")),
            ast.D0Eop2("or", ast.D0Ebtf(True), ast.D0Evar("outside")),
        ]
        for expression in cases:
            with self.subTest(expression=expression):
                self.assertEqual(free_vars(compile_expr(expression)), frozenset({"outside"}))

    def test_unselected_conditionals_and_short_circuit_operands_skip_divergence(self) -> None:
        cases = [
            (ast.D0Eif0(ast.D0Ebtf(True), ast.D0Eint(1), omega()), "natural", 1),
            (ast.D0Eif0(ast.D0Ebtf(False), omega(), ast.D0Eint(9)), "natural", 9),
            (ast.D0Eop2("and", ast.D0Ebtf(False), omega()), "boolean", False),
            (ast.D0Eop2("or", ast.D0Ebtf(True), omega()), "boolean", True),
        ]
        for expression, kind, expected in cases:
            with self.subTest(expression=expression):
                self.assert_pipeline(expression, kind, expected)

    def test_selected_conditionals_and_required_boolean_operands_diverge(self) -> None:
        cases = [
            ast.D0Eif0(ast.D0Ebtf(True), omega(), ast.D0Eint(1)),
            ast.D0Eif0(ast.D0Ebtf(False), ast.D0Eint(1), omega()),
            ast.D0Eop2("and", ast.D0Ebtf(True), omega()),
            ast.D0Eop2("or", ast.D0Ebtf(False), omega()),
        ]
        for expression in cases:
            with self.subTest(expression=expression):
                result = evaluate(compile_expr(expression), max_steps=100)
                self.assertEqual(result.status, "exhausted")
                self.assertEqual(result.steps, 100)

    def test_unused_arguments_initializers_and_either_pair_component_are_strict(self) -> None:
        cases = [
            ast.D0Eapp(ast.D0Elam("unused", ast.D0Eint(0)), omega()),
            ast.D0Elet("unused", omega(), ast.D0Eint(2)),
            ast.D0Epfst(ast.D0Epair(ast.D0Eint(2), omega())),
            ast.D0Epsnd(ast.D0Epair(omega(), ast.D0Ebtf(True))),
        ]
        for expression in cases:
            with self.subTest(expression=expression):
                result = evaluate(compile_expr(expression), max_steps=100)
                self.assertEqual(result.status, "exhausted")
                self.assertEqual(result.steps, 100)

    def test_compilation_is_deterministic_and_preserves_input(self) -> None:
        expression = ast.D0Eif0(
            ast.D0Eop2("<=", ast.D0Eint(2), ast.D0Eint(3)), ast.D0Eint(7), ast.D0Eint(9),
        )
        before = deepcopy(expression)
        first = compile_expr(expression)
        compile_expr(ast.D0Eop2("==", ast.D0Eint(4), ast.D0Eint(5)))
        self.assertEqual(first, compile_expr(expression))
        self.assertEqual(expression, before)

    def test_compilation_does_not_call_evaluators_even_for_diverging_input(self) -> None:
        with (
            patch("MySolution.evaluator.evaluate", side_effect=AssertionError("shared evaluation")),
            patch.object(ast, "d0exp_evaluate", side_effect=AssertionError("source evaluation")),
            patch.object(ast, "EvaluateVisitor", side_effect=AssertionError("evaluation visitor")),
        ):
            for expression in (ast.D0Eop2("+", ast.D0Eint(2), ast.D0Eint(3)), omega()):
                self.assert_pure_with_preserved_free_vars(expression, compile_expr(expression))

    def test_translation_dispatches_through_the_supplied_visitor_interface(self) -> None:
        original_accept = ast.D0Eint.accept
        with patch.object(ast.D0Eint, "accept", autospec=True, side_effect=original_accept) as accept:
            compile_expr(ast.D0Eint(2))
        visitors = [call.args[1] for call in accept.call_args_list]
        self.assertTrue(all(isinstance(visitor, ast.D0ExpVisitor) for visitor in visitors))
        self.assertTrue(any(isinstance(visitor, compiler._CompileVisitor) for visitor in visitors))

    def test_unsupported_forms_are_rejected_even_in_unused_code(self) -> None:
        bad_forms = [
            (ast.D0Eint(-2), "negative literal.*-2"),
            (ast.D0Eop1("+1", ast.D0Eint(2)), "unsupported unary operator.*\\+1"),
            (ast.D0Eop1("-1", ast.D0Eint(2)), "unsupported unary operator.*-1"),
            (ast.D0Eop2("/", ast.D0Eint(4), ast.D0Eint(2)), "unsupported binary operator.*/"),
            (ast.D0Eop2("&&", ast.D0Ebtf(True), ast.D0Ebtf(False)), "unsupported binary operator.*&&"),
        ]
        wrappers = (
            lambda bad: bad,
            lambda bad: ast.D0Eif0(ast.D0Ebtf(True), ast.D0Eint(1), bad),
            lambda bad: ast.D0Eif0(ast.D0Ebtf(False), bad, ast.D0Eint(1)),
            lambda bad: ast.D0Elam("unused", bad),
            lambda bad: ast.D0Eop2("and", ast.D0Ebtf(False), bad),
            lambda bad: ast.D0Eop2("or", ast.D0Ebtf(True), bad),
            lambda bad: ast.D0Elet("unused", ast.D0Elam("x", bad), ast.D0Eint(1)),
        )
        for bad, diagnostic in bad_forms:
            for index, wrap in enumerate(wrappers):
                expression = wrap(bad)
                before = deepcopy(expression)
                with self.subTest(bad=bad, wrapper=index):
                    with self.assertRaisesRegex(CompilationError, diagnostic):
                        compile_expr(expression)
                    self.assertEqual(expression, before)

    def test_fix_is_supported_in_applications_and_unused_branches(self) -> None:
        expression = ast.D0Efix("f", "x", ast.D0Evar("x"))
        self.assert_pipeline(ast.D0Eapp(expression, ast.D0Eint(3)), "natural", 3)
        self.assert_pipeline(
            ast.D0Eif0(ast.D0Ebtf(True), ast.D0Eint(1), expression), "natural", 1,
        )

    def test_unsupported_code_inside_fix_is_checked(self) -> None:
        expression = ast.D0Efix("f", "x", ast.D0Eint(-1))
        with self.assertRaisesRegex(CompilationError, "negative literal.*-1"):
            compile_expr(expression)


if __name__ == "__main__":
    unittest.main()
