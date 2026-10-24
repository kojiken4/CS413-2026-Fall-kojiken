"""Basic encoding shapes, purity, closedness, and deterministic builder names."""

import unittest

from MySolution.encodings import boolean, identity, numeral
from MySolution.target import (
    App, FreshNameGenerator, Lam, Var, all_names, alpha_equivalent, free_vars,
)


class BasicEncodingTests(unittest.TestCase):
    def assert_pure_closed(self, term) -> None:
        pending = [term]
        while pending:
            current = pending.pop()
            self.assertIn(type(current), (Var, Lam, App))
            if isinstance(current, Lam):
                pending.append(current.body)
            elif isinstance(current, App):
                pending.extend((current.fn, current.arg))
        self.assertEqual(free_vars(term), frozenset())

    def test_numerals_match_required_representations(self) -> None:
        cases = [
            (0, Lam("s", Lam("z", Var("z")))),
            (1, Lam("s", Lam("z", App(Var("s"), Var("z"))))),
            (2, Lam("s", Lam("z", App(Var("s"), App(Var("s"), Var("z")))))),
        ]
        for number, expected in cases:
            with self.subTest(number=number):
                term = numeral(number)
                self.assertTrue(alpha_equivalent(term, expected))
                self.assert_pure_closed(term)

    def test_booleans_and_identity_match_required_representations(self) -> None:
        cases = [
            (boolean(True), Lam("t", Lam("f", Var("t")))),
            (boolean(False), Lam("t", Lam("f", Var("f")))),
            (identity(), Lam("w", Var("w"))),
        ]
        for actual, expected in cases:
            with self.subTest(actual=actual):
                self.assertTrue(alpha_equivalent(actual, expected))
                self.assert_pure_closed(actual)

    def test_zero_and_false_have_the_same_representation(self) -> None:
        self.assertTrue(alpha_equivalent(numeral(0), boolean(False)))

    def test_default_builders_are_deterministic_across_calls(self) -> None:
        for builder in (lambda: numeral(3), lambda: boolean(True), identity):
            with self.subTest(builder=builder):
                first = builder()
                numeral(5)
                self.assertEqual(first, builder())

    def test_shared_name_generator_avoids_surrounding_and_generated_names(self) -> None:
        reserved = {"s_1", "z_3", "t_5", "f_7", "w_9", "s", "z", "t", "f", "x"}
        names = FreshNameGenerator(reserved)
        terms = [numeral(2, names=names), boolean(True, names=names), identity(names=names)]
        seen = set(reserved)
        for term in terms:
            self.assertFalse(all_names(term) & seen)
            seen.update(all_names(term))
            self.assert_pure_closed(term)
        self.assertEqual(reserved, {"s_1", "z_3", "t_5", "f_7", "w_9", "s", "z", "t", "f", "x"})

    def test_negative_numeral_literal_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "negative numeral literal: -1"):
            numeral(-1)

    def test_noninteger_numeral_literals_including_booleans_are_rejected(self) -> None:
        for literal in (True, False, 1.0, "2", None):
            with self.subTest(literal=literal):
                with self.assertRaisesRegex(TypeError, "nonnegative integer"):
                    numeral(literal)

    def test_boolean_builder_requires_a_boolean_literal(self) -> None:
        for literal in (0, 1, "true", None):
            with self.subTest(literal=literal):
                with self.assertRaisesRegex(TypeError, "True or False"):
                    boolean(literal)


if __name__ == "__main__":
    unittest.main()
