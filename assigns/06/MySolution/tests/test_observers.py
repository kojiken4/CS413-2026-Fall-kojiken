"""Bounded observation contexts, output shapes, and separate execution counts."""

from copy import deepcopy
import unittest
from unittest.mock import patch

from MySolution.encodings import boolean, identity, numeral
from MySolution.evaluator import OpenTermError, evaluate
from MySolution.observers import observe
from MySolution.target import App, Lam, Var, free_vars


def omega() -> App:
    delta = Lam("x", App(Var("x"), Var("x")))
    return App(delta, delta)


class ScalarObservationTests(unittest.TestCase):
    def test_literal_naturals_including_zero(self) -> None:
        for number, expected_steps in ((0, 2), (1, 3), (2, 4), (5, 7)):
            with self.subTest(number=number):
                result = observe(numeral(number), "natural", max_steps=20)
                self.assertEqual(result.status, "completed")
                self.assertIs(type(result.value), int)
                self.assertEqual(result.value, number)
                self.assertEqual(result.steps, expected_steps)
                self.assertEqual(result.budget, 20)
                self.assertIsNone(result.diagnostic)

    def test_both_boolean_results(self) -> None:
        for answer in (False, True):
            with self.subTest(answer=answer):
                result = observe(boolean(answer), "boolean", max_steps=2)
                self.assertEqual(result.status, "completed")
                self.assertIs(type(result.value), bool)
                self.assertIs(result.value, answer)
                self.assertEqual(result.steps, 2)

    def test_expected_kind_disambiguates_zero_and_false(self) -> None:
        term = numeral(0)
        natural = observe(term, "natural", max_steps=2)
        boolean_result = observe(term, "boolean", max_steps=2)
        self.assertEqual(natural.status, "completed")
        self.assertIs(type(natural.value), int)
        self.assertEqual(natural.value, 0)
        self.assertEqual(boolean_result.status, "completed")
        self.assertIs(boolean_result.value, False)

    def test_alpha_renamed_numerals_and_booleans(self) -> None:
        renamed_two = Lam("apply", Lam("start", App(Var("apply"), App(Var("apply"), Var("start")))))
        renamed_true = Lam("yes", Lam("no", Var("yes")))
        # Coincident unused outer/used inner names still encode FALSE and zero.
        renamed_false = Lam("same", Lam("same", Var("same")))
        cases = [
            (renamed_two, "natural", 2), (renamed_true, "boolean", True),
            (renamed_false, "boolean", False), (renamed_false, "natural", 0),
        ]
        for value, kind, expected in cases:
            with self.subTest(value=value, kind=kind):
                result = observe(value, kind, max_steps=10)
                self.assertEqual(result.status, "completed")
                self.assertEqual(result.value, expected)

    def test_computed_natural_body_is_forced_through_the_context(self) -> None:
        value = Lam("s", Lam("z", App(identity(), App(Var("s"), App(Var("s"), Var("z"))))))
        execution = evaluate(value, max_steps=0)
        self.assertEqual(execution.value, value)
        self.assertEqual(execution.steps, 0)
        observation = observe(execution.value, "natural", max_steps=5)
        self.assertEqual(observation.status, "completed")
        self.assertEqual(observation.value, 2)
        self.assertEqual(observation.steps, 5)

    def test_computed_boolean_bodies_are_forced_through_the_context(self) -> None:
        for selected, expected in (("t", True), ("f", False)):
            with self.subTest(expected=expected):
                value = Lam("t", Lam("f", App(identity(), Var(selected))))
                result = observe(value, "boolean", max_steps=3)
                self.assertEqual(result.status, "completed")
                self.assertIs(result.value, expected)
                self.assertEqual(result.steps, 3)

    def test_execution_and_observation_have_separate_budgets_and_counts(self) -> None:
        execution = evaluate(App(identity(), numeral(2)), max_steps=1)
        observation = observe(execution.value, "natural", max_steps=4)
        self.assertEqual(execution.status, "completed")
        self.assertEqual((execution.steps, execution.budget), (1, 1))
        self.assertEqual(observation.status, "completed")
        self.assertEqual(observation.value, 2)
        self.assertEqual((observation.steps, observation.budget), (4, 4))

    def test_observation_budget_boundaries(self) -> None:
        cases = [
            (numeral(0), "natural", 0, "exhausted", None),
            (numeral(0), "natural", 1, "exhausted", None),
            (numeral(0), "natural", 2, "completed", 0),
            (numeral(3), "natural", 4, "exhausted", None),
            (numeral(3), "natural", 5, "completed", 3),
            (boolean(False), "boolean", 1, "exhausted", None),
            (boolean(False), "boolean", 2, "completed", False),
        ]
        for value, kind, budget, status, decoded in cases:
            with self.subTest(kind=kind, budget=budget):
                result = observe(value, kind, max_steps=budget)
                self.assertEqual(result.status, status)
                self.assertEqual(result.value, decoded)
                self.assertEqual(result.steps, budget)
                self.assertEqual(result.budget, budget)
                if status == "exhausted":
                    self.assertIn("budget exhausted", result.diagnostic)

    def test_diverging_observation_reports_exhaustion_not_a_decoded_value(self) -> None:
        value = Lam("a", Lam("b", omega()))
        for kind in ("natural", "boolean"):
            with self.subTest(kind=kind):
                result = observe(value, kind, max_steps=9)
                self.assertEqual(result.status, "exhausted")
                self.assertIsNone(result.value)
                self.assertEqual(result.steps, 9)

    def test_malformed_natural_outputs_are_rejected(self) -> None:
        base = Lam("c", Lam("z", Var("z")))
        malformed_outputs = [
            identity(),
            Lam("c", Lam("z", Var("c"))),
            Lam("c", Lam("z", App(Var("c"), Var("z")))),
            Lam("same", Lam("same", App(Var("same"), base))),
        ]
        for output in malformed_outputs:
            with self.subTest(output=output):
                value = Lam("s", Lam("z", output))
                result = observe(value, "natural", max_steps=2)
                self.assertEqual(result.status, "malformed")
                self.assertIsNone(result.value)
                self.assertEqual(result.steps, 2)
                self.assertIn("finite spine", result.diagnostic)

    def test_natural_output_shapes_allow_alpha_renaming_and_shadowed_base(self) -> None:
        base = Lam("same", Lam("same", Var("same")))
        spine = Lam("choose", Lam("end", App(Var("choose"), base)))
        # Shape inspection must understand scope, not require fixed context names.
        value = Lam("s", Lam("z", spine))
        result = observe(value, "natural", max_steps=2)
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.value, 1)

    def test_malformed_boolean_output_is_rejected(self) -> None:
        value = Lam("t", Lam("f", boolean(True)))
        result = observe(value, "boolean", max_steps=2)
        self.assertEqual(result.status, "malformed")
        self.assertIsNone(result.value)
        self.assertEqual(result.steps, 2)
        self.assertIn("either marker", result.diagnostic)

    def test_boolean_marker_matching_allows_alpha_renaming(self) -> None:
        value = Lam("t", Lam("f", Lam("renamed", Var("renamed"))))
        result = observe(value, "boolean", max_steps=2)
        self.assertEqual(result.status, "completed")
        self.assertIs(result.value, True)

    def test_budget_exhaustion_is_distinct_from_malformed_output(self) -> None:
        value = Lam("t", Lam("f", boolean(True)))
        exhausted = observe(value, "boolean", max_steps=1)
        malformed = observe(value, "boolean", max_steps=2)
        self.assertEqual(exhausted.status, "exhausted")
        self.assertEqual(malformed.status, "malformed")
        self.assertIsNone(exhausted.value)
        self.assertIsNone(malformed.value)

    def test_observation_is_deterministic_and_preserves_input(self) -> None:
        value = Lam("s", Lam("z", App(identity(), App(Var("s"), Var("z")))))
        before = deepcopy(value)
        for budget in (0, 4):
            with self.subTest(budget=budget):
                self.assertEqual(
                    observe(value, "natural", max_steps=budget),
                    observe(value, "natural", max_steps=budget),
                )
                self.assertEqual(value, before)

    def test_context_is_closed_pure_syntax_run_by_the_shared_engine(self) -> None:
        with patch("MySolution.observers.evaluate", wraps=evaluate) as shared_engine:
            result = observe(numeral(2), "natural", max_steps=4)
        self.assertEqual(result.value, 2)
        shared_engine.assert_called_once()
        context = shared_engine.call_args.args[0]
        self.assertEqual(shared_engine.call_args.kwargs, {"max_steps": 4})
        self.assertEqual(free_vars(context), frozenset())
        pending = [context]
        while pending:
            current = pending.pop()
            self.assertIn(type(current), (Var, Lam, App))
            if isinstance(current, Lam):
                pending.append(current.body)
            elif isinstance(current, App):
                pending.extend((current.fn, current.arg))

    def test_negative_and_noninteger_observation_budgets(self) -> None:
        with self.assertRaisesRegex(ValueError, "nonnegative"):
            observe(numeral(0), "natural", max_steps=-1)
        for budget in (True, 1.0, "2", None):
            with self.subTest(budget=budget):
                with self.assertRaisesRegex(TypeError, "nonnegative integer"):
                    observe(numeral(0), "natural", max_steps=budget)

    def test_unknown_expected_kind_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "expected_kind"):
            observe(numeral(0), "integer", max_steps=2)

    def test_observation_requires_a_lambda_value_not_an_unfinished_program(self) -> None:
        for term in (None, Var("x"), App(identity(), numeral(0))):
            with self.subTest(term=term):
                with self.assertRaisesRegex(TypeError, "completed target lambda value"):
                    observe(term, "natural", max_steps=10)

    def test_open_observation_input_follows_closed_execution_policy(self) -> None:
        with self.assertRaisesRegex(OpenTermError, "outside"):
            observe(Lam("x", Var("outside")), "natural", max_steps=10)


if __name__ == "__main__":
    unittest.main()
