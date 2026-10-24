"""Encoded operations compute through beta reduction, independently of compilation."""

from copy import deepcopy
import unittest
from unittest.mock import patch

from MySolution import encodings as church
from MySolution.evaluator import evaluate
from MySolution.observers import observe
from MySolution.target import (
    App, FreshNameGenerator, Lam, Var, all_names, alpha_equivalent, free_vars,
)


OPERATIONS = (
    church.pair, church.first, church.second,
    church.successor, church.predecessor, church.is_zero,
    church.add, church.subtract, church.multiply,
    church.negation, church.conjunction, church.disjunction,
    church.less_than, church.less_equal, church.greater_than, church.greater_equal,
    church.equal, church.not_equal,
)


def apply(fn, *arguments):
    for argument in arguments:
        fn = App(fn, argument)
    return fn


def omega():
    delta = Lam("x", App(Var("x"), Var("x")))
    return App(delta, delta)


class EncodedOperationTests(unittest.TestCase):
    def assert_decoded(self, term, kind, expected) -> None:
        execution = evaluate(term, max_steps=50000)
        self.assertEqual(execution.status, "completed")
        result = observe(execution.value, kind, max_steps=50000)
        self.assertEqual(result.status, "completed", result.diagnostic)
        self.assertIs(type(result.value), type(expected))
        self.assertEqual(result.value, expected)

    def test_every_combinator_is_closed_and_contains_only_target_nodes(self) -> None:
        for builder in OPERATIONS:
            with self.subTest(builder=builder.__name__):
                term = builder()
                self.assertEqual(free_vars(term), frozenset())
                pending = [term]
                while pending:
                    current = pending.pop()
                    self.assertIn(type(current), (Var, Lam, App))
                    if isinstance(current, Lam):
                        pending.append(current.body)
                    elif isinstance(current, App):
                        pending.extend((current.fn, current.arg))

    def test_combinator_builders_are_deterministic(self) -> None:
        for builder in OPERATIONS:
            with self.subTest(builder=builder.__name__):
                self.assertEqual(builder(), builder())

    def test_shared_names_avoid_surrounding_and_previous_combinator_names(self) -> None:
        reserved = {"m_1", "n_2", "p_3", "state_4", "s", "z", "t", "f", "x"}
        names = FreshNameGenerator(reserved)
        seen = set(reserved)
        for builder in OPERATIONS:
            with self.subTest(builder=builder.__name__):
                term = builder(names=names)
                self.assertFalse(all_names(term) & seen)
                seen.update(all_names(term))
                self.assertEqual(free_vars(term), frozenset())

    def test_pair_matches_required_representation(self) -> None:
        expected = Lam("a", Lam("b", Lam("p", apply(Var("p"), Var("a"), Var("b")))))
        self.assertTrue(alpha_equivalent(church.pair(), expected))

    def test_successor(self) -> None:
        for number, expected in ((0, 1), (3, 4)):
            with self.subTest(number=number):
                self.assert_decoded(apply(church.successor(), church.numeral(number)), "natural", expected)

    def test_predecessor_including_zero_and_one(self) -> None:
        for number, expected in ((0, 0), (1, 0), (4, 3)):
            with self.subTest(number=number):
                self.assert_decoded(apply(church.predecessor(), church.numeral(number)), "natural", expected)

    def test_zero_test(self) -> None:
        for number, expected in ((0, True), (1, False), (4, False)):
            with self.subTest(number=number):
                self.assert_decoded(apply(church.is_zero(), church.numeral(number)), "boolean", expected)

    def test_addition(self) -> None:
        for left, right, expected in ((0, 0, 0), (0, 3, 3), (3, 0, 3), (2, 3, 5)):
            with self.subTest(left=left, right=right):
                self.assert_decoded(
                    apply(church.add(), church.numeral(left), church.numeral(right)), "natural", expected,
                )

    def test_truncated_subtraction(self) -> None:
        for left, right, expected in ((0, 0, 0), (0, 3, 0), (2, 5, 0), (5, 2, 3), (3, 3, 0)):
            with self.subTest(left=left, right=right):
                self.assert_decoded(
                    apply(church.subtract(), church.numeral(left), church.numeral(right)), "natural", expected,
                )

    def test_multiplication(self) -> None:
        for left, right, expected in ((0, 3, 0), (3, 0, 0), (1, 4, 4), (3, 4, 12)):
            with self.subTest(left=left, right=right):
                self.assert_decoded(
                    apply(church.multiply(), church.numeral(left), church.numeral(right)), "natural", expected,
                )

    def test_every_comparison_on_zero_equal_and_unequal_operands(self) -> None:
        operands = ((0, 0), (0, 1), (1, 0), (2, 3), (3, 2), (2, 2))
        cases = (
            (church.less_than, (False, True, False, True, False, False)),
            (church.less_equal, (True, True, False, True, False, True)),
            (church.greater_than, (False, False, True, False, True, False)),
            (church.greater_equal, (True, False, True, False, True, True)),
            (church.equal, (True, False, False, False, False, True)),
            (church.not_equal, (False, True, True, True, True, False)),
        )
        for builder, answers in cases:
            for (left, right), answer in zip(operands, answers):
                with self.subTest(builder=builder.__name__, left=left, right=right):
                    self.assert_decoded(
                        apply(builder(), church.numeral(left), church.numeral(right)), "boolean", answer,
                    )

    def test_boolean_negation(self) -> None:
        for value, expected in ((False, True), (True, False)):
            with self.subTest(value=value):
                self.assert_decoded(apply(church.negation(), church.boolean(value)), "boolean", expected)

    def test_boolean_conjunction_and_disjunction_truth_tables(self) -> None:
        cases = (
            (False, False, False, False), (False, True, False, True),
            (True, False, False, True), (True, True, True, True),
        )
        for left, right, conjunction, disjunction in cases:
            for builder, answer in ((church.conjunction, conjunction), (church.disjunction, disjunction)):
                with self.subTest(builder=builder.__name__, left=left, right=right):
                    self.assert_decoded(
                        apply(builder(), church.boolean(left), church.boolean(right)), "boolean", answer,
                    )

    def test_boolean_combinators_do_not_change_call_by_value_argument_rules(self) -> None:
        # The compiler must supply thunks for source short-circuiting in Step 7.
        for builder, left in ((church.conjunction, False), (church.disjunction, True)):
            with self.subTest(builder=builder.__name__):
                result = evaluate(apply(builder(), church.boolean(left), omega()), max_steps=15)
                self.assertEqual(result.status, "exhausted")
                self.assertEqual(result.steps, 15)

    def test_both_pair_projections(self) -> None:
        term = apply(church.pair(), church.numeral(2), church.boolean(True))
        self.assert_decoded(apply(church.first(), term), "natural", 2)
        self.assert_decoded(apply(church.second(), term), "boolean", True)

    def test_pair_construction_is_strict_in_both_components(self) -> None:
        terms = (
            apply(church.pair(), omega(), church.boolean(True)),
            apply(church.pair(), church.numeral(2), omega()),
        )
        for term in terms:
            with self.subTest(term=term):
                result = evaluate(term, max_steps=15)
                self.assertEqual(result.status, "exhausted")
                self.assertEqual(result.steps, 15)

    def test_composed_arithmetic_example(self) -> None:
        product = apply(church.multiply(), church.numeral(3), church.numeral(4))
        self.assert_decoded(apply(church.add(), church.numeral(2), product), "natural", 14)

    def test_alpha_renamed_numeral_operands(self) -> None:
        two = Lam("n_1", Lam("p_2", App(Var("n_1"), App(Var("n_1"), Var("p_2")))))
        self.assert_decoded(apply(church.add(), two, two), "natural", 4)

    def test_execution_preserves_combinators_and_arguments(self) -> None:
        operation, left, right = church.subtract(), church.numeral(5), church.numeral(2)
        before = deepcopy((operation, left, right))
        self.assert_decoded(apply(operation, left, right), "natural", 3)
        self.assertEqual((operation, left, right), before)

    def test_builders_do_not_run_the_evaluator(self) -> None:
        with patch("MySolution.evaluator.evaluate", side_effect=AssertionError("builder execution")):
            for builder in OPERATIONS:
                self.assertIsInstance(builder(), Lam)

    def test_encoded_arithmetic_does_not_call_source_arithmetic(self) -> None:
        with patch(
            "MySolution.evaluator._apply_source_binary",
            side_effect=AssertionError("source arithmetic shortcut"),
        ):
            self.assert_decoded(
                apply(church.multiply(), church.numeral(3), church.numeral(4)), "natural", 12,
            )


if __name__ == "__main__":
    unittest.main()
