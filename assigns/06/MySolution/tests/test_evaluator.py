"""Weak call-by-value order, exact beta budgets, and residual target terms."""

from copy import deepcopy
import unittest

from MySolution.evaluator import OpenTermError, evaluate
from MySolution.target import App, Lam, Var, free_vars


def identity() -> Lam:
    return Lam("x", Var("x"))


def omega() -> App:
    delta = Lam("x", App(Var("x"), Var("x")))
    return App(delta, delta)


class TargetEvaluationTests(unittest.TestCase):
    def test_value_completes_with_zero_steps_including_budget_zero(self) -> None:
        value = identity()
        for budget in (0, 1, 10):
            with self.subTest(budget=budget):
                result = evaluate(value, max_steps=budget)
                self.assertEqual(result.status, "completed")
                self.assertEqual(result.term, value)
                self.assertEqual(result.value, value)
                self.assertEqual(result.steps, 0)
                self.assertEqual(result.budget, budget)

    def test_zero_budget_application_exhausts_without_contracting(self) -> None:
        term = App(identity(), identity())
        result = evaluate(term, max_steps=0)
        self.assertEqual(result.status, "exhausted")
        self.assertEqual(result.term, term)
        self.assertIsNone(result.value)
        self.assertEqual(result.steps, 0)

    def test_value_reached_on_last_step_is_completed(self) -> None:
        result = evaluate(App(identity(), identity()), max_steps=1)
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.value, identity())
        self.assertEqual(result.steps, 1)

    def test_function_then_argument_then_outer_application(self) -> None:
        value = identity()
        term = App(App(value, value), App(value, value))
        cases = [
            (0, "exhausted", term, 0),
            (1, "exhausted", App(value, App(value, value)), 1),
            (2, "exhausted", App(value, value), 2),
            (3, "completed", value, 3),
            (4, "completed", value, 3),
        ]
        for budget, status, expected, steps in cases:
            with self.subTest(budget=budget):
                result = evaluate(term, max_steps=budget)
                self.assertEqual(result.status, status)
                self.assertEqual(result.term, expected)
                self.assertEqual(result.steps, steps)
                self.assertEqual(result.budget, budget)

    def test_residual_reconstructs_both_kinds_of_surrounding_frame(self) -> None:
        value = identity()
        term = App(value, App(App(value, value), value))
        cases = [
            (0, term),
            (1, App(value, App(value, value))),
            (2, App(value, value)),
        ]
        for budget, expected in cases:
            with self.subTest(budget=budget):
                result = evaluate(term, max_steps=budget)
                self.assertEqual(result.status, "exhausted")
                self.assertEqual(result.term, expected)
                self.assertEqual(result.steps, budget)
                self.assertEqual(free_vars(result.term), frozenset())

    def test_residual_can_be_resumed_with_a_new_budget(self) -> None:
        value = identity()
        term = App(value, App(App(value, value), value))
        first = evaluate(term, max_steps=1)
        second = evaluate(first.term, max_steps=2)
        full = evaluate(term, max_steps=3)
        self.assertEqual(first.status, "exhausted")
        self.assertEqual(second.status, "completed")
        self.assertEqual(second.value, full.value)
        self.assertEqual(first.steps + second.steps, full.steps)

    def test_no_reduction_beneath_a_lambda_even_with_divergent_body(self) -> None:
        term = Lam("unused", omega())
        result = evaluate(term, max_steps=10)
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.value, term)
        self.assertEqual(result.steps, 0)

    def test_no_eta_reduction(self) -> None:
        term = Lam("x", App(identity(), Var("x")))
        result = evaluate(term, max_steps=10)
        self.assertEqual(result.value, term)
        self.assertNotEqual(result.value, identity())
        self.assertEqual(result.steps, 0)

    def test_an_application_returning_a_lambda_stops_before_its_body(self) -> None:
        term = App(Lam("f", Lam("x", App(Var("f"), Var("x")))), identity())
        expected = Lam("x", App(identity(), Var("x")))
        result = evaluate(term, max_steps=1)
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.value, expected)
        self.assertEqual(result.steps, 1)

    def test_unused_terminating_argument_is_evaluated_before_application(self) -> None:
        value = identity()
        function = Lam("unused", value)
        term = App(function, App(value, value))
        partial = evaluate(term, max_steps=1)
        self.assertEqual(partial.status, "exhausted")
        self.assertEqual(partial.term, App(function, value))
        self.assertEqual(partial.steps, 1)
        completed = evaluate(term, max_steps=2)
        self.assertEqual(completed.status, "completed")
        self.assertEqual(completed.value, value)
        self.assertEqual(completed.steps, 2)

    def test_unused_diverging_argument_still_exhausts(self) -> None:
        term = App(Lam("unused", identity()), omega())
        result = evaluate(term, max_steps=7)
        self.assertEqual(result.status, "exhausted")
        self.assertEqual(result.term, term)
        self.assertIsNone(result.value)
        self.assertEqual(result.steps, 7)

    def test_diverging_function_leaves_argument_unevaluated(self) -> None:
        term = App(omega(), App(identity(), identity()))
        result = evaluate(term, max_steps=7)
        self.assertEqual(result.status, "exhausted")
        self.assertEqual(result.term, term)
        self.assertEqual(result.steps, 7)

    def test_divergence_uses_exact_budget_even_when_term_repeats(self) -> None:
        term = omega()
        for budget in (0, 1, 9):
            with self.subTest(budget=budget):
                result = evaluate(term, max_steps=budget)
                self.assertEqual(result.status, "exhausted")
                self.assertEqual(result.term, term)
                self.assertEqual(result.steps, budget)
                self.assertEqual(result.budget, budget)

    def test_many_contractions_do_not_accumulate_python_call_frames(self) -> None:
        result = evaluate(omega(), max_steps=5000)
        self.assertEqual(result.status, "exhausted")
        self.assertEqual(result.steps, 5000)

    def test_results_are_deterministic_and_inputs_unchanged(self) -> None:
        value = identity()
        term = App(App(value, value), App(value, value))
        before = deepcopy(term)
        for budget in (1, 3):
            with self.subTest(budget=budget):
                first = evaluate(term, max_steps=budget)
                second = evaluate(term, max_steps=budget)
                self.assertEqual(first, second)
                self.assertEqual(term, before)

    def test_negative_budget_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "nonnegative"):
            evaluate(identity(), max_steps=-1)

    def test_noninteger_budgets_including_booleans_are_rejected(self) -> None:
        for budget in (True, False, 1.0, "1", None):
            with self.subTest(budget=budget):
                with self.assertRaisesRegex(TypeError, "nonnegative integer"):
                    evaluate(identity(), max_steps=budget)

    def test_open_input_is_rejected_with_sorted_free_names(self) -> None:
        term = App(Var("z"), Var("a"))
        with self.assertRaisesRegex(OpenTermError, "free variables: a, z"):
            evaluate(term, max_steps=10)

    def test_open_lambda_is_rejected_even_when_its_body_would_not_run(self) -> None:
        term = Lam("x", Var("outside"))
        with self.assertRaisesRegex(OpenTermError, "outside"):
            evaluate(term, max_steps=0)


if __name__ == "__main__":
    unittest.main()
