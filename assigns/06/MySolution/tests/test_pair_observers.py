"""Pair projections and recursively observed data share one observation budget."""

from copy import deepcopy
import unittest
from unittest.mock import patch

from MySolution.encodings import boolean, identity, numeral, pair
from MySolution.evaluator import evaluate
from MySolution.observers import observe
from MySolution.target import App, Lam, Var, free_vars


def pair_value(left, right):
    execution = evaluate(App(App(pair(), left), right), max_steps=1000)
    assert execution.status == "completed"
    return execution.value


def omega():
    delta = Lam("x", App(Var("x"), Var("x")))
    return App(delta, delta)


class PairObservationTests(unittest.TestCase):
    def test_mixed_pair_and_separate_execution_observation_counts(self) -> None:
        execution = evaluate(App(App(pair(), numeral(2)), boolean(True)), max_steps=2)
        result = observe(execution.value, ("pair", "natural", "boolean"), max_steps=14)
        self.assertEqual(execution.status, "completed")
        self.assertEqual((execution.steps, execution.budget), (2, 2))
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.value, (2, True))
        self.assertEqual((result.steps, result.budget), (14, 14))
        self.assertEqual(result.term, execution.value)
        self.assertIsNone(result.diagnostic)

    def test_required_nested_pair_example(self) -> None:
        value = pair_value(pair_value(numeral(2), boolean(True)), numeral(3))
        kind = ("pair", ("pair", "natural", "boolean"), "natural")
        result = observe(value, kind, max_steps=27)
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.value, ((2, True), 3))
        self.assertEqual(result.steps, 27)

    def test_pair_nested_on_the_right(self) -> None:
        value = pair_value(numeral(2), pair_value(boolean(True), numeral(3)))
        kind = ("pair", "natural", ("pair", "boolean", "natural"))
        result = observe(value, kind, max_steps=27)
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.value, (2, (True, 3)))
        self.assertEqual(result.steps, 27)

    def test_all_contexts_receive_only_the_remaining_budget(self) -> None:
        value = pair_value(numeral(2), boolean(True))
        with patch("MySolution.observers.evaluate", wraps=evaluate) as engine:
            result = observe(value, ("pair", "natural", "boolean"), max_steps=14)
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.steps, 14)
        self.assertEqual([call.kwargs["max_steps"] for call in engine.call_args_list], [14, 10, 6, 2])
        for call in engine.call_args_list:
            self.assertEqual(free_vars(call.args[0]), frozenset())

    def test_budget_boundaries_across_projections_and_scalar_contexts(self) -> None:
        value = pair_value(numeral(2), boolean(True))
        for budget in (0, 3, 4, 7, 8, 11, 12, 13, 14, 20):
            with self.subTest(budget=budget):
                result = observe(value, ("pair", "natural", "boolean"), max_steps=budget)
                if budget < 14:
                    self.assertEqual(result.status, "exhausted")
                    self.assertIsNone(result.value)
                    self.assertEqual(result.steps, budget)
                    self.assertIn("result.", result.diagnostic)
                else:
                    self.assertEqual(result.status, "completed")
                    self.assertEqual(result.value, (2, True))
                    self.assertEqual(result.steps, 14)
                self.assertEqual(result.budget, budget)

    def test_nested_budget_is_not_reset_for_children(self) -> None:
        value = pair_value(pair_value(numeral(2), boolean(True)), numeral(3))
        kind = ("pair", ("pair", "natural", "boolean"), "natural")
        result = observe(value, kind, max_steps=26)
        self.assertEqual(result.status, "exhausted")
        self.assertEqual(result.steps, 26)
        self.assertIsNone(result.value)
        self.assertIn("result.second", result.diagnostic)

    def test_computed_pair_components_are_evaluated_by_projection_contexts(self) -> None:
        value = Lam("select", App(
            App(Var("select"), App(identity(), numeral(2))), boolean(True),
        ))
        result = observe(value, ("pair", "natural", "boolean"), max_steps=16)
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.value, (2, True))
        self.assertEqual(result.steps, 16)

    def test_malformed_left_component_has_a_data_path_and_no_partial_tuple(self) -> None:
        bad_natural = Lam("s", Lam("z", identity()))
        value = pair_value(bad_natural, boolean(True))
        result = observe(value, ("pair", "natural", "boolean"), max_steps=20)
        self.assertEqual(result.status, "malformed")
        self.assertIsNone(result.value)
        self.assertEqual(result.steps, 6)
        self.assertIn("result.first", result.diagnostic)

    def test_malformed_right_component_discards_the_decoded_left_component(self) -> None:
        bad_boolean = Lam("t", Lam("f", boolean(True)))
        value = pair_value(numeral(2), bad_boolean)
        result = observe(value, ("pair", "natural", "boolean"), max_steps=20)
        self.assertEqual(result.status, "malformed")
        self.assertIsNone(result.value)
        self.assertEqual(result.steps, 14)
        self.assertIn("result.second", result.diagnostic)

    def test_diverging_pair_projection_is_bounded(self) -> None:
        value = Lam("select", omega())
        result = observe(value, ("pair", "natural", "boolean"), max_steps=7)
        self.assertEqual(result.status, "exhausted")
        self.assertEqual(result.steps, 7)
        self.assertIsNone(result.value)
        self.assertIn("result.first.projection", result.diagnostic)

    def test_diverging_right_observation_uses_the_remaining_budget(self) -> None:
        value = pair_value(numeral(2), Lam("t", Lam("f", omega())))
        result = observe(value, ("pair", "natural", "boolean"), max_steps=15)
        self.assertEqual(result.status, "exhausted")
        self.assertEqual(result.steps, 15)
        self.assertIsNone(result.value)
        self.assertIn("result.second", result.diagnostic)

    def test_invalid_recursive_kind_is_rejected_before_evaluation(self) -> None:
        kinds = (
            ("pair", "natural"), ("pair", "natural", "invalid"),
            ("pair", ("pair", "natural"), "boolean"), ["pair", "natural", "boolean"],
        )
        for kind in kinds:
            with self.subTest(kind=kind):
                with patch("MySolution.observers.evaluate") as engine:
                    with self.assertRaisesRegex(ValueError, "expected_kind"):
                        observe(identity(), kind, max_steps=20)
                    engine.assert_not_called()

    def test_pair_budget_validation_does_not_turn_booleans_into_integer_limits(self) -> None:
        value = pair_value(numeral(2), boolean(True))
        with self.assertRaisesRegex(TypeError, "nonnegative integer"):
            observe(value, ("pair", "natural", "boolean"), max_steps=True)

    def test_nested_pair_observation_is_deterministic_and_preserves_input(self) -> None:
        value = pair_value(pair_value(numeral(2), boolean(True)), numeral(3))
        before = deepcopy(value)
        kind = ("pair", ("pair", "natural", "boolean"), "natural")
        for budget in (10, 27):
            with self.subTest(budget=budget):
                self.assertEqual(observe(value, kind, max_steps=budget), observe(value, kind, max_steps=budget))
                self.assertEqual(value, before)


if __name__ == "__main__":
    unittest.main()
