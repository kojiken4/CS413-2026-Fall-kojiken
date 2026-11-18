"""Exercise the real LAMBDA3 solver through its Python adapter."""

import unittest
from collections import Counter
from itertools import permutations
from unittest.mock import patch

from MySolution.solver import L, QueensSolver, force_event


class QueensSolverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.solver = QueensSolver()

    def events(self, size):
        cursor = self.solver.open(size)
        while (step := force_event(cursor)) is not None:
            event, cursor = step
            yield event

    def test_safety_continuations(self):
        decisions = {
            (event["row"], event["column"], attempt["board"]): event["event"]
            for attempt, event in self.adjacent_events(4)
            if attempt["event"] == "try"
        }
        self.assertEqual(decisions[1, 0, (0,)], "reject")  # Same column.
        self.assertEqual(decisions[1, 1, (0,)], "reject")  # Down and right.
        self.assertEqual(decisions[1, 0, (1,)], "reject")  # Down and left.
        self.assertEqual(decisions[1, 2, (0,)], "place")
        # Column 0 passes the nearest-queen check and conflicts with row zero.
        self.assertEqual(decisions[2, 0, (0, 2)], "reject")

    def adjacent_events(self, size):
        events = self.events(size)
        previous = next(events)
        for event in events:
            yield previous, event
            previous = event

    def test_solution_tail_backtracks_and_resumes_at_next_column(self):
        cursor = self.solver.open(4)
        while True:
            step = force_event(cursor)
            self.assertIsNotNone(step)
            event, cursor = step
            self.assertNotEqual(event["event"], "done")
            if event["event"] == "solution":
                break

        self.assertEqual(event, {"event": "solution", "board": (1, 3, 0, 2)})
        self.assertFalse(cursor.evaluated)
        backtrack, cursor = force_event(cursor)
        self.assertEqual(backtrack, {
            "event": "backtrack", "row": 3, "column": 2, "board": (1, 3, 0),
        })
        attempt, _ = force_event(cursor)
        self.assertEqual(attempt, {
            "event": "try", "row": 3, "column": 3, "board": (1, 3, 0),
        })

    def test_event_coordinates_and_snapshots(self):
        board = ()
        pending = None
        seen = set()
        last_kind = None
        for event in self.events(4):
            kind = event["event"]
            self.assertNotEqual(last_kind, "done")
            seen.add(kind)
            last_kind = kind
            if kind == "done":
                self.assertEqual(event, {"event": "done"})
                self.assertEqual(board, ())
                self.assertIsNone(pending)
                continue
            if kind == "solution":
                self.assertEqual(event, {"event": "solution", "board": board})
                self.assertEqual(len(board), 4)
                self.assertIsNone(pending)
                continue

            self.assertEqual(set(event), {"event", "row", "column", "board"})
            row, column = event["row"], event["column"]
            self.assertIn(row, range(4))
            self.assertIn(column, range(4))
            if kind == "try":
                self.assertIsNone(pending)
                self.assertEqual(row, len(board))
                pending = row, column
            elif kind in ("place", "reject"):
                self.assertEqual((row, column), pending)
                pending = None
                safe = all(
                    column != earlier and abs(column - earlier) != row - earlier_row
                    for earlier_row, earlier in enumerate(board)
                )
                self.assertEqual(kind, "place" if safe else "reject")
                if kind == "place":
                    board += (column,)
            elif kind == "backtrack":
                self.assertIsNone(pending)
                self.assertEqual(row, len(board) - 1)
                self.assertEqual(column, board[-1])
                board = board[:-1]
            self.assertEqual(event["board"], board)

        self.assertEqual(seen, {"try", "place", "reject", "backtrack", "solution", "done"})
        self.assertEqual(last_kind, "done")

    def test_all_92_solutions_in_deterministic_order(self):
        expected = [
            board for board in permutations(range(8))
            if len({row + column for row, column in enumerate(board)}) == 8
            and len({row - column for row, column in enumerate(board)}) == 8
        ]
        actual = []
        done = False
        for event in self.events(8):
            self.assertFalse(done, "done must be the last event")
            if event["event"] == "solution":
                actual.append(event["board"])
            elif event["event"] == "done":
                done = True

        self.assertTrue(done)
        self.assertEqual(len(actual), 92)
        self.assertEqual(len(set(actual)), 92)
        self.assertEqual(actual, expected)

    def test_open_and_bounded_forcing_do_no_extra_work(self):
        evaluate = L.d0exp_evaluate
        work = Counter()

        def observe(expression, environment):
            match expression:
                case L.D0Eop2("stcn_cons", _, _):
                    work["cell"] += 1
                case L.D0Eapp(L.D0Evar("search"), _):
                    work["search"] += 1
                case L.D0Eapp(L.D0Evar("check_safe"), L.D0Etupl((_, L.D0Eint(1), _, _, _))):
                    work["candidate_check"] += 1
            return evaluate(expression, environment)

        with patch.object(L, "d0exp_evaluate", observe):
            for size in (9, 10):
                with self.subTest(size=size):
                    work.clear()
                    cursor = self.solver.open(size)
                    self.assertFalse(cursor.evaluated)
                    self.assertEqual(work, {})

                    event, cursor = force_event(cursor)
                    self.assertEqual(event, {"event": "try", "row": 0, "column": 0, "board": ()})
                    self.assertFalse(cursor.evaluated)
                    self.assertEqual(work, {"search": 1, "cell": 1})

                    checks = 0
                    for delivered in range(2, 33):
                        event, cursor = force_event(cursor)
                        if event["event"] in ("place", "reject"):
                            checks += 1
                        self.assertFalse(cursor.evaluated)
                        self.assertEqual(work, {
                            "search": 1, "cell": delivered, "candidate_check": checks,
                        })

    def test_supported_board_size_bounds(self):
        for size in range(4, 11):
            with self.subTest(size=size):
                self.assertEqual(next(self.events(size)), {
                    "event": "try", "row": 0, "column": 0, "board": (),
                })
        for size in (3, 11, False, 8.0, "8"):
            with self.subTest(size=size):
                with self.assertRaises(ValueError):
                    self.solver.open(size)
