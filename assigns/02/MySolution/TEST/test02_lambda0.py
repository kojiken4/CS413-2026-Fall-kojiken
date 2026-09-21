"""Tests for pair and projection extensions; requires Python 3.12+."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lambda0 import (
    T0Mint, T0Mbtf, T0Mstr, T0Mvar, T0Mlam, T0Mfix, T0Mapp, T0Mop2,
    T0Mpair, T0Mpfst, T0Mpsnd, t0erm_size, t0erm_fvset, t0erm_subst0,
    t0erm_cbv_evaluate0,
)


class TestPairAnalysis(unittest.TestCase):
    def test_literal_pair(self):
        term = T0Mpair(T0Mint(1), T0Mint(2))
        self.assertEqual(t0erm_size(term), 3)
        self.assertEqual(t0erm_fvset(term), frozenset())

    def test_pair_collects_both_components(self):
        term = T0Mpair(T0Mvar("x"), T0Mvar("y"))
        self.assertEqual(t0erm_fvset(term), frozenset({"x", "y"}))

    def test_duplicate_variables(self):
        term = T0Mpair(T0Mvar("x"), T0Mvar("x"))
        self.assertEqual(t0erm_size(term), 3)
        self.assertEqual(t0erm_fvset(term), frozenset({"x"}))

    def test_projections_analyze_entire_operand(self):
        for projection in (T0Mpfst, T0Mpsnd):
            with self.subTest(projection=projection.__name__):
                term = projection(T0Mpair(T0Mvar("x"), T0Mvar("y")))
                self.assertEqual(t0erm_size(term), 4)
                self.assertEqual(t0erm_fvset(term), frozenset({"x", "y"}))

    def test_projection_analysis_does_not_evaluate(self):
        for projection in (T0Mpfst, T0Mpsnd):
            with self.subTest(projection=projection.__name__):
                term = projection(T0Mvar("p"))
                self.assertEqual(t0erm_size(term), 2)
                self.assertEqual(t0erm_fvset(term), frozenset({"p"}))

    def test_nested_pairs_and_projections(self):
        term = T0Mpsnd(T0Mpair(
            T0Mpfst(T0Mpair(T0Mvar("x"), T0Mint(0))),
            T0Mpair(T0Mvar("y"), T0Mvar("x")),
        ))
        self.assertEqual(t0erm_size(term), 9)
        self.assertEqual(t0erm_fvset(term), frozenset({"x", "y"}))

    def test_lambda_binding_is_local_to_its_body(self):
        term = T0Mpair(
            T0Mlam("x", T0Mpair(T0Mvar("x"), T0Mvar("y"))),
            T0Mvar("x"),
        )
        self.assertEqual(t0erm_size(term), 6)
        self.assertEqual(t0erm_fvset(term.arg1), frozenset({"y"}))
        self.assertEqual(t0erm_fvset(term), frozenset({"x", "y"}))

    def test_recursive_function_binds_name_and_parameter(self):
        term = T0Mfix("f", "x", T0Mpair(
            T0Mapp(T0Mvar("f"), T0Mvar("x")),
            T0Mpfst(T0Mvar("outside")),
        ))
        self.assertEqual(t0erm_size(term), 7)
        self.assertEqual(t0erm_fvset(term), frozenset({"outside"}))

    def test_projections_inside_arithmetic(self):
        term = T0Mop2("+",
            T0Mpfst(T0Mpair(T0Mvar("x"), T0Mint(1))),
            T0Mpsnd(T0Mpair(T0Mint(2), T0Mvar("y"))),
        )
        self.assertEqual(t0erm_size(term), 9)
        self.assertEqual(t0erm_fvset(term), frozenset({"x", "y"}))


class TestPairSubstitution(unittest.TestCase):
    def test_replaces_both_components(self):
        term = T0Mpair(T0Mvar("x"), T0Mvar("x"))
        self.assertEqual(t0erm_subst0(term, "x", T0Mint(7)),
                         T0Mpair(T0Mint(7), T0Mint(7)))
        self.assertEqual(term, T0Mpair(T0Mvar("x"), T0Mvar("x")))

    def test_preserves_unrelated_variables_and_constants(self):
        term = T0Mpair(T0Mvar("y"), T0Mint(3))
        self.assertEqual(t0erm_subst0(term, "x", T0Mint(7)), term)

    def test_projection_preserves_constructor_without_evaluating(self):
        replacement = T0Mpair(T0Mint(1), T0Mint(2))
        for projection in (T0Mpfst, T0Mpsnd):
            with self.subTest(projection=projection.__name__):
                self.assertEqual(
                    t0erm_subst0(projection(T0Mvar("p")), "p", replacement),
                    projection(replacement),
                )

    def test_nested_pairs_and_projections(self):
        term = T0Mpair(
            T0Mpfst(T0Mpair(T0Mvar("x"), T0Mvar("y"))),
            T0Mpsnd(T0Mpair(T0Mint(0), T0Mvar("x"))),
        )
        expected = T0Mpair(
            T0Mpfst(T0Mpair(T0Mint(7), T0Mvar("y"))),
            T0Mpsnd(T0Mpair(T0Mint(0), T0Mint(7))),
        )
        self.assertEqual(t0erm_subst0(term, "x", T0Mint(7)), expected)

    def test_substitutes_free_variable_under_lambda(self):
        term = T0Mlam("y", T0Mpair(T0Mvar("x"), T0Mpfst(T0Mvar("y"))))
        expected = T0Mlam("y", T0Mpair(T0Mint(7), T0Mpfst(T0Mvar("y"))))
        self.assertEqual(t0erm_subst0(term, "x", T0Mint(7)), expected)

    def test_lambda_shadowing_does_not_block_sibling(self):
        bound = T0Mlam("x", T0Mpair(T0Mvar("x"), T0Mint(0)))
        term = T0Mpair(bound, T0Mvar("x"))
        self.assertEqual(t0erm_subst0(term, "x", T0Mint(7)),
                         T0Mpair(bound, T0Mint(7)))

    def test_substitutes_free_variable_under_recursive_binder(self):
        term = T0Mfix("f", "n", T0Mpair(
            T0Mapp(T0Mvar("f"), T0Mvar("n")), T0Mpsnd(T0Mvar("p")),
        ))
        replacement = T0Mpair(T0Mint(1), T0Mint(2))
        expected = T0Mfix("f", "n", T0Mpair(
            T0Mapp(T0Mvar("f"), T0Mvar("n")), T0Mpsnd(replacement),
        ))
        self.assertEqual(t0erm_subst0(term, "p", replacement), expected)

    def test_recursive_binder_protects_name_and_parameter(self):
        bound = T0Mfix("f", "n", T0Mpair(T0Mvar("f"), T0Mvar("n")))
        for name in ("f", "n"):
            with self.subTest(name=name):
                term = T0Mpair(bound, T0Mvar(name))
                self.assertEqual(t0erm_subst0(term, name, T0Mint(7)),
                                 T0Mpair(bound, T0Mint(7)))

    def test_closed_function_replacement(self):
        replacement = T0Mlam("z", T0Mpair(T0Mvar("z"), T0Mint(0)))
        self.assertEqual(t0erm_fvset(replacement), frozenset())
        term = T0Mpair(T0Mvar("x"), T0Mint(1))
        self.assertEqual(t0erm_subst0(term, "x", replacement),
                         T0Mpair(replacement, T0Mint(1)))


class TestPairEvaluation(unittest.TestCase):
    def test_evaluates_both_components(self):
        term = T0Mpair(
            T0Mop2("+", T0Mint(2), T0Mint(3)),
            T0Mop2("*", T0Mint(4), T0Mint(5)),
        )
        self.assertEqual(t0erm_cbv_evaluate0(term), T0Mpair(T0Mint(5), T0Mint(20)))

    def test_both_projections(self):
        pair = T0Mpair(T0Mint(1), T0Mop2("+", T0Mint(2), T0Mint(3)))
        for projection, expected in ((T0Mpfst, 1), (T0Mpsnd, 5)):
            with self.subTest(projection=projection.__name__):
                self.assertEqual(t0erm_cbv_evaluate0(projection(pair)), T0Mint(expected))

    def test_nested_mixed_values(self):
        term = T0Mpair(T0Mstr("hello"), T0Mpair(
            T0Mbtf(True), T0Mop2("+", T0Mint(2), T0Mint(3)),
        ))
        expected = T0Mpair(T0Mstr("hello"), T0Mpair(T0Mbtf(True), T0Mint(5)))
        self.assertEqual(t0erm_cbv_evaluate0(term), expected)
        self.assertEqual(t0erm_cbv_evaluate0(T0Mpsnd(T0Mpsnd(term))), T0Mint(5))

    def test_function_body_is_not_evaluated_in_pair(self):
        function = T0Mlam("x", T0Mop2("/", T0Mint(1), T0Mint(0)))
        pair = T0Mpair(function, T0Mint(2))
        self.assertEqual(t0erm_cbv_evaluate0(pair), pair)
        self.assertIs(t0erm_cbv_evaluate0(T0Mpfst(pair)), function)

    def test_projected_function_can_be_called(self):
        function = T0Mlam("x", T0Mop2("+", T0Mvar("x"), T0Mint(1)))
        term = T0Mapp(T0Mpfst(T0Mpair(function, T0Mint(0))), T0Mint(6))
        self.assertEqual(t0erm_cbv_evaluate0(term), T0Mint(7))

    def test_function_accepts_and_returns_pair(self):
        swap = T0Mlam("p", T0Mpair(T0Mpsnd(T0Mvar("p")), T0Mpfst(T0Mvar("p"))))
        term = T0Mapp(swap, T0Mpair(T0Mint(1), T0Mop2("+", T0Mint(2), T0Mint(3))))
        self.assertEqual(t0erm_cbv_evaluate0(term), T0Mpair(T0Mint(5), T0Mint(1)))

    def test_projection_evaluates_function_call_operand(self):
        make_pair = T0Mlam("x", T0Mpair(T0Mvar("x"), T0Mint(9)))
        call = T0Mapp(make_pair, T0Mint(7))
        for projection, expected in ((T0Mpfst, 7), (T0Mpsnd, 9)):
            with self.subTest(projection=projection.__name__):
                self.assertEqual(t0erm_cbv_evaluate0(projection(call)), T0Mint(expected))

    def test_recursive_function_value_in_pair(self):
        function = T0Mfix("f", "p", T0Mpair(T0Mpsnd(T0Mvar("p")), T0Mvar("f")))
        call = T0Mapp(function, T0Mpair(T0Mint(1), T0Mint(2)))
        self.assertEqual(t0erm_cbv_evaluate0(call), T0Mpair(T0Mint(2), function))

    def test_projections_reject_non_pairs(self):
        values = (T0Mint(1), T0Mbtf(True), T0Mstr("bad"),
                  T0Mlam("x", T0Mvar("x")), T0Mfix("f", "x", T0Mvar("x")))
        for projection in (T0Mpfst, T0Mpsnd):
            for value in values:
                with self.subTest(projection=projection.__name__, value=value):
                    with self.assertRaises(TypeError):
                        t0erm_cbv_evaluate0(projection(value))
            with self.subTest(projection=projection.__name__, operand="computed integer"):
                with self.assertRaises(TypeError):
                    t0erm_cbv_evaluate0(projection(T0Mop2("+", T0Mint(1), T0Mint(2))))

    def test_pair_evaluates_left_before_right(self):
        division_error = T0Mop2("/", T0Mint(1), T0Mint(0))
        type_error = T0Mop2("+", T0Mstr("bad"), T0Mint(1))
        for left, right, error in ((division_error, type_error, ZeroDivisionError),
                                   (type_error, division_error, TypeError)):
            with self.subTest(error=error.__name__):
                with self.assertRaises(error):
                    t0erm_cbv_evaluate0(T0Mpair(left, right))

    def test_projection_evaluates_unselected_component(self):
        bad = T0Mop2("/", T0Mint(1), T0Mint(0))
        terms = (T0Mpfst(T0Mpair(T0Mint(1), bad)),
                 T0Mpsnd(T0Mpair(bad, T0Mint(1))))
        for term in terms:
            with self.subTest(term=term):
                with self.assertRaises(ZeroDivisionError):
                    t0erm_cbv_evaluate0(term)

    def test_projection_propagates_operand_error(self):
        for projection in (T0Mpfst, T0Mpsnd):
            with self.subTest(projection=projection.__name__):
                with self.assertRaises(ZeroDivisionError):
                    t0erm_cbv_evaluate0(projection(T0Mop2("/", T0Mint(1), T0Mint(0))))


if __name__ == "__main__":
    unittest.main(verbosity=2)
