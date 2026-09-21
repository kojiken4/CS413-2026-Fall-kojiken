"""Tests for pair and projection extensions; requires Python 3.12+."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lambda0 import (
    T0Mint, T0Mvar, T0Mlam, T0Mfix, T0Mapp, T0Mop2,
    T0Mpair, T0Mpfst, T0Mpsnd, t0erm_size, t0erm_fvset,
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
