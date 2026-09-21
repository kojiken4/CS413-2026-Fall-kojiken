"""Stack-safety checks for evaluator tail positions; Python 3.12+."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lambda0 import (
    T0Mint, T0Mbtf, T0Mvar, T0Mlam, T0Mfix, T0Mapp, T0Mif0, T0Mop2,
    T0Mpair, T0Mpfst, T0Mpsnd, t0erm_cbv_evaluate0,
)


def countdown(base, through_lambda=False):
    n = T0Mvar("n")
    next_call = T0Mapp(T0Mvar("loop"), T0Mop2("-", n, T0Mint(1)))
    if through_lambda:
        next_call = T0Mapp(T0Mlam("unused", next_call), T0Mint(0))
    return T0Mfix("loop", "n", T0Mif0(
        T0Mop2("<=", n, T0Mint(0)), base, next_call,
    ))


class TestTailCalls(unittest.TestCase):
    def setUp(self):
        self.original_limit = sys.getrecursionlimit()
        self.steps = self.original_limit + 100

    def tearDown(self):
        self.assertEqual(sys.getrecursionlimit(), self.original_limit)

    def test_countdown_exceeds_python_recursion_limit(self):
        term = T0Mapp(countdown(T0Mint(42)), T0Mint(self.steps))
        self.assertEqual(t0erm_cbv_evaluate0(term), T0Mint(42))

    def test_tail_calls_through_ordinary_lambda(self):
        term = T0Mapp(countdown(T0Mint(42), through_lambda=True), T0Mint(self.steps))
        self.assertEqual(t0erm_cbv_evaluate0(term), T0Mint(42))

    def test_tail_recursive_pair_accumulator(self):
        state = T0Mvar("state")
        n, total = T0Mpfst(state), T0Mpsnd(state)
        function = T0Mfix("sum", "state", T0Mif0(
            T0Mop2(">", n, T0Mint(0)),
            T0Mapp(T0Mvar("sum"), T0Mpair(
                T0Mop2("-", n, T0Mint(1)), T0Mop2("+", total, n),
            )),
            total,
        ))
        term = T0Mapp(function, T0Mpair(T0Mint(self.steps), T0Mint(0)))
        expected = self.steps * (self.steps + 1) // 2
        self.assertEqual(t0erm_cbv_evaluate0(term), T0Mint(expected))

    def test_caller_resumes_pending_arithmetic(self):
        call = T0Mapp(countdown(T0Mint(42)), T0Mint(self.steps))
        self.assertEqual(t0erm_cbv_evaluate0(T0Mop2("+", call, T0Mint(5))), T0Mint(47))

    def test_deep_selected_conditional_branches(self):
        bad = T0Mop2("/", T0Mint(1), T0Mint(0))
        term = T0Mint(42)
        for index in range(self.steps):
            if index % 2:
                term = T0Mif0(T0Mbtf(True), term, bad)
            else:
                term = T0Mif0(T0Mbtf(False), bad, term)
        self.assertEqual(t0erm_cbv_evaluate0(term), T0Mint(42))

    def test_error_after_long_tail_call_chain(self):
        bad = T0Mop2("/", T0Mint(1), T0Mint(0))
        term = T0Mapp(countdown(bad), T0Mint(self.steps))
        with self.assertRaises(ZeroDivisionError):
            t0erm_cbv_evaluate0(term)


if __name__ == "__main__":
    unittest.main(verbosity=2)
