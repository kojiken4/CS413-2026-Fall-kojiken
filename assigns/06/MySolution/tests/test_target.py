"""Target operations, including open-term scope and capture hazards."""

from copy import deepcopy
from dataclasses import FrozenInstanceError
import unittest

from MySolution.source_ast import ast
from MySolution.target import (
    App, FreshNameGenerator, Lam, Var,
    all_names, alpha_equivalent, free_vars, pretty, substitute,
)


class TargetRepresentationTests(unittest.TestCase):
    def test_exact_print_formats(self) -> None:
        cases = [
            (Var("x"), "x"),
            (Lam("x", Var("x")), "(lam x. x)"),
            (App(Var("f"), Var("x")), "(f x)"),
            (Lam("f", Lam("x", App(Var("f"), Var("x")))),
             "(lam f. (lam x. (f x)))"),
            (App(App(Var("f"), Var("x")), Var("y")), "((f x) y)"),
            (App(Var("f"), App(Var("x"), Var("y"))), "(f (x y))"),
        ]
        for term, expected in cases:
            with self.subTest(term=term):
                self.assertEqual(pretty(term), expected)

    def test_target_nodes_are_separate_from_source_nodes(self) -> None:
        for term in (Var("x"), Lam("x", Var("x")), App(Var("f"), Var("x"))):
            with self.subTest(term=term):
                self.assertNotIsInstance(term, ast.D0E000)

    def test_all_node_fields_are_immutable(self) -> None:
        cases = [
            (Var("x"), "name", "y"),
            (Lam("x", Var("x")), "name", "y"),
            (Lam("x", Var("x")), "body", Var("y")),
            (App(Var("f"), Var("x")), "fn", Var("g")),
            (App(Var("f"), Var("x")), "arg", Var("y")),
        ]
        for term, field, value in cases:
            with self.subTest(term=term, field=field):
                with self.assertRaises(FrozenInstanceError):
                    setattr(term, field, value)

    def test_identifiers_follow_the_assignment_convention(self) -> None:
        for name in ("x", "_", "_x2", "s", "z", "t", "f", "Z_42"):
            with self.subTest(valid=name):
                self.assertEqual(Var(name).name, name)
                self.assertEqual(Lam(name, Var(name)).name, name)
        for name in ("", "2x", "x-y", "a b", "x\n", "λ", "é"):
            with self.subTest(invalid=name):
                with self.assertRaises(ValueError):
                    Var(name)
                with self.assertRaises(ValueError):
                    Lam(name, Var("x"))
        with self.assertRaises(TypeError):
            Var(3)


class NameAnalysisTests(unittest.TestCase):
    def test_free_variables_respect_nested_binders(self) -> None:
        term = Lam("x", App(Var("x"), Lam("y", App(Var("x"), Var("z")))))
        self.assertEqual(free_vars(term), frozenset({"z"}))
        self.assertEqual(free_vars(Lam("x", Var("x"))), frozenset())
        self.assertEqual(free_vars(App(Var("x"), Var("y"))), frozenset({"x", "y"}))

    def test_all_names_includes_unused_binders(self) -> None:
        term = Lam("unused", App(Var("s"), Lam("x_1", Var("s"))))
        self.assertEqual(free_vars(term), frozenset({"s"}))
        self.assertEqual(all_names(term), frozenset({"unused", "s", "x_1"}))

    def test_fresh_names_skip_collisions_deterministically(self) -> None:
        reserved = {"x_1", "x_2", "y_4"}
        for _ in range(2):
            generator = FreshNameGenerator(reserved)
            self.assertEqual(generator.fresh("x"), "x_3")
            self.assertEqual(generator.fresh("y"), "y_5")
            self.assertEqual(generator.fresh("x"), "x_6")
        self.assertEqual(reserved, {"x_1", "x_2", "y_4"})

    def test_fresh_names_do_not_repeat_returned_names(self) -> None:
        generator = FreshNameGenerator()
        self.assertEqual(generator.fresh(), "v_1")
        self.assertEqual(generator.fresh(), "v_2")
        with self.assertRaises(ValueError):
            generator.fresh("not-valid")


class SubstitutionTests(unittest.TestCase):
    def test_variable_and_application_cases(self) -> None:
        replacement = Lam("z", Var("z"))
        self.assertEqual(substitute(Var("x"), "x", replacement), replacement)
        self.assertEqual(substitute(Var("y"), "x", replacement), Var("y"))
        self.assertEqual(
            substitute(App(Var("x"), Var("x")), "x", replacement),
            App(replacement, replacement),
        )

    def test_shadowing_stops_substitution(self) -> None:
        term = App(Var("x"), Lam("x", App(Var("x"), Var("y"))))
        self.assertEqual(
            substitute(term, "x", Var("z")),
            App(Var("z"), Lam("x", App(Var("x"), Var("y")))),
        )

    def test_substitution_under_an_unrelated_binder(self) -> None:
        self.assertEqual(
            substitute(Lam("z", App(Var("x"), Var("z"))), "x", Var("y")),
            Lam("z", App(Var("y"), Var("z"))),
        )

    def test_open_replacement_is_not_captured(self) -> None:
        result = substitute(Lam("y", Var("x")), "x", Var("y"))
        self.assertEqual(result, Lam("y_1", Var("y")))
        self.assertTrue(alpha_equivalent(result, Lam("fresh", Var("y"))))
        self.assertEqual(free_vars(result), frozenset({"y"}))

    def test_nested_same_named_binders_are_renamed_in_their_own_scopes(self) -> None:
        term = Lam("y", App(Var("x"), Lam("y", App(Var("y"), Var("x")))))
        expected = Lam("y_1", App(Var("y"), Lam("y_2", App(Var("y_2"), Var("y")))))
        self.assertEqual(substitute(term, "x", Var("y")), expected)

    def test_fresh_name_avoids_unused_and_used_binders_in_input(self) -> None:
        term = Lam("y", App(Var("x"), Lam("y_1", Var("y"))))
        expected = Lam("y_2", App(Var("y"), Lam("y_1", Var("y_2"))))
        self.assertEqual(substitute(term, "x", Var("y")), expected)

    def test_fresh_name_avoids_bound_names_in_replacement(self) -> None:
        replacement = App(Var("y"), Lam("y_1", Var("y_1")))
        self.assertEqual(
            substitute(Lam("y", Var("x")), "x", replacement),
            Lam("y_2", replacement),
        )

    def test_absent_variable_does_not_trigger_unnecessary_renaming(self) -> None:
        term = Lam("y", Var("z"))
        self.assertEqual(substitute(term, "x", Var("y")), term)

    def test_replacement_is_inserted_once_without_evaluation(self) -> None:
        replacement = App(Lam("z", Var("z")), App(Var("x"), Var("y")))
        self.assertEqual(substitute(Var("x"), "x", replacement), replacement)

    def test_repeated_substitution_is_deterministic_and_preserves_inputs(self) -> None:
        term = Lam("y", App(Var("x"), Var("y")))
        replacement = App(Var("y"), Var("y_1"))
        term_before, replacement_before = deepcopy(term), deepcopy(replacement)
        first = substitute(term, "x", replacement)
        second = substitute(term, "x", replacement)
        self.assertEqual(first, Lam("y_2", App(replacement, Var("y_2"))))
        self.assertEqual(first, second)
        self.assertEqual(term, term_before)
        self.assertEqual(replacement, replacement_before)

    def test_substitution_free_variable_law(self) -> None:
        terms = [
            Var("x"), Var("y"), Lam("x", Var("x")), Lam("y", Var("x")),
            Lam("y", App(Var("x"), Lam("x", Var("y")))),
            App(Lam("y", Var("x")), Var("z")),
        ]
        replacements = [Var("x"), Var("y"), Lam("x", Var("x")), App(Var("y"), Var("z"))]
        for term in terms:
            for replacement in replacements:
                with self.subTest(term=term, replacement=replacement):
                    expected = free_vars(term)
                    if "x" in expected:
                        expected = (expected - {"x"}) | free_vars(replacement)
                    self.assertEqual(free_vars(substitute(term, "x", replacement)), expected)

    def test_invalid_substitution_identifier_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            substitute(Var("x"), "bad-name", Var("y"))


class AlphaEquivalenceTests(unittest.TestCase):
    def test_bound_renaming_and_shadowing(self) -> None:
        cases = [
            (Lam("x", Var("x")), Lam("y", Var("y"))),
            (Lam("x", Lam("y", App(Var("x"), Var("y")))),
             Lam("a", Lam("b", App(Var("a"), Var("b"))))),
            (Lam("x", Lam("x", Var("x"))), Lam("a", Lam("b", Var("b")))),
            (Lam("x", App(Var("x"), Var("free"))),
             Lam("y", App(Var("y"), Var("free")))),
        ]
        for left, right in cases:
            with self.subTest(left=left, right=right):
                self.assertTrue(alpha_equivalent(left, right))
                self.assertTrue(alpha_equivalent(right, left))
                self.assertTrue(alpha_equivalent(left, left))
                self.assertNotEqual(left, right)

    def test_free_names_bound_status_and_binding_depth_must_match(self) -> None:
        cases = [
            (Var("x"), Var("y")),
            (Lam("x", Var("x")), Lam("y", Var("x"))),
            (Lam("x", Lam("y", Var("x"))), Lam("a", Lam("b", Var("b")))),
            (Lam("x", Lam("y", Var("x"))), Lam("a", Lam("a", Var("a")))),
            (Var("x"), Lam("x", Var("x"))),
        ]
        for left, right in cases:
            with self.subTest(left=left, right=right):
                self.assertFalse(alpha_equivalent(left, right))
                self.assertFalse(alpha_equivalent(right, left))

    def test_a_binder_does_not_leak_into_a_sibling(self) -> None:
        left = App(Lam("x", Var("x")), Var("x"))
        equivalent = App(Lam("y", Var("y")), Var("x"))
        different = App(Lam("y", Var("y")), Var("y"))
        self.assertTrue(alpha_equivalent(left, equivalent))
        self.assertFalse(alpha_equivalent(left, different))


if __name__ == "__main__":
    unittest.main()
