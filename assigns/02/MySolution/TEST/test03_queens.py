"""ATS2 reference and translated board-operation checks."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lambda0 import (
    T0Mint, T0Mbtf, T0Mstr, T0Mpair, T0Mpfst, T0Mpsnd, T0Mapp, T0Mop2,
    t0erm_cbv_evaluate0, t0erm_fvset,
)
from queens_lambda0 import (
    BOARD_GET, BOARD_SET, SAFETY_TEST1, SAFETY_TEST2,
    SEARCH, REVERSE_LIST, EMPTY_LIST, list_cons, build_queens_term, decode_result,
    make_board, tuple_term, tuple_item,
)

REFERENCE = Path(__file__).resolve().parents[1] / "reference" / "queens-ats-output.txt"


def parse_ats_output(text):
    """Return ordered boards, excluding the source's initial demonstration board."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    def read_board(rows):
        if len(rows) != 8:
            raise ValueError("Expected eight rows per board")
        columns = []
        for row in rows:
            cells = row.split()
            if len(cells) != 8 or cells.count("Q") != 1 or set(cells) - {"Q", "."}:
                raise ValueError("Expected eight cells and exactly one queen per row")
            columns.append(cells.index("Q"))
        return tuple(columns)

    if read_board(lines[:8]) != tuple(range(8)):
        raise ValueError("Expected the original source's initial demonstration board")
    boards = []
    for start in range(8, len(lines), 9):
        if lines[start] != f"Solution #{len(boards) + 1}:":
            raise ValueError("Expected consecutive solution numbers starting at one")
        boards.append(read_board(lines[start + 1:start + 9]))
    return boards


class TestATSReference(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = REFERENCE.read_text(encoding="utf-8")
        cls.boards = parse_ats_output(cls.text)

    def test_count_and_uniqueness(self):
        self.assertEqual(len(self.boards), 92)
        self.assertEqual(len(set(self.boards)), 92)
        self.assertNotIn(tuple(range(8)), self.boards)

    def test_reference_order_endpoints(self):
        self.assertEqual(self.boards[0], (0, 4, 7, 5, 2, 6, 1, 3))
        self.assertEqual(self.boards[-1], (7, 3, 0, 2, 5, 1, 6, 4))

    def test_every_board_has_no_conflicts(self):
        for number, board in enumerate(self.boards, start=1):
            with self.subTest(solution=number):
                for row, column in enumerate(board):
                    for previous in range(row):
                        self.assertNotEqual(column, board[previous])
                        self.assertNotEqual(abs(column - board[previous]), row - previous)

    def test_parser_rejects_malformed_reference(self):
        corruptions = {
            "truncated board": "\n".join(self.text.rstrip().splitlines()[:-1]),
            "wrong numbering": self.text.replace("Solution #2:", "Solution #3:", 1),
            "invalid cell": self.text.replace("Q", "X", 1),
            "two queens in row": self.text.replace("Q .", "Q Q", 1),
        }
        for case, text in corruptions.items():
            with self.subTest(case=case):
                with self.assertRaises(ValueError):
                    parse_ats_output(text)


class TestBoardTerms(unittest.TestCase):
    columns = (0, 4, 7, 5, 2, 6, 1, 3)

    def setUp(self):
        self.board = make_board(self.columns)

    def assertBoardColumns(self, value, expected):
        # Inspect returned values directly, independently of translated board_get.
        for column in expected[:-1]:
            self.assertIsInstance(value, T0Mpair)
            self.assertEqual(value.arg1, T0Mint(column))
            value = value.arg2
        self.assertEqual(value, T0Mint(expected[-1]))

    def test_board_encoding(self):
        self.assertBoardColumns(self.board, self.columns)

    def test_tuple_helpers_build_ast_only(self):
        a, b, c = T0Mint(10), T0Mint(20), T0Mint(30)
        term = tuple_term(a, b, c)
        self.assertEqual(term, T0Mpair(a, T0Mpair(b, c)))
        self.assertEqual(tuple_item(term, 0, 3), T0Mpfst(term))
        self.assertEqual(tuple_item(term, 1, 3), T0Mpfst(T0Mpsnd(term)))
        self.assertEqual(tuple_item(term, 2, 3), T0Mpsnd(T0Mpsnd(term)))

    def test_builders_reject_invalid_shapes(self):
        for columns in ((), (1,) * 7, (1,) * 9):
            with self.subTest(columns=columns):
                with self.assertRaises(ValueError):
                    make_board(columns)
        for column in (True, "1", 1.5):
            with self.subTest(column=column):
                with self.assertRaises(TypeError):
                    make_board((column,) + (0,) * 7)
        for fields in ((), (T0Mint(0),)):
            with self.assertRaises(ValueError):
                tuple_term(*fields)
        for index, size in ((-1, 8), (8, 8), (0, 1)):
            with self.subTest(index=index, size=size):
                with self.assertRaises(ValueError):
                    tuple_item(self.board, index, size)

    def test_get_every_position(self):
        for index, expected in enumerate(self.columns):
            with self.subTest(index=index):
                call = T0Mapp(BOARD_GET, tuple_term(self.board, T0Mint(index)))
                self.assertEqual(t0erm_cbv_evaluate0(call), T0Mint(expected))

    def test_set_every_position_preserves_other_entries(self):
        for index in range(8):
            with self.subTest(index=index):
                call = T0Mapp(BOARD_SET, tuple_term(self.board, T0Mint(index), T0Mint(9)))
                expected = list(self.columns)
                expected[index] = 9
                self.assertBoardColumns(t0erm_cbv_evaluate0(call), expected)
                self.assertBoardColumns(self.board, self.columns)

    def test_out_of_range_matches_ats(self):
        for index in (-100, -1, 8, 100):
            with self.subTest(index=index):
                get = T0Mapp(BOARD_GET, tuple_term(self.board, T0Mint(index)))
                put = T0Mapp(BOARD_SET, tuple_term(self.board, T0Mint(index), T0Mint(9)))
                self.assertEqual(t0erm_cbv_evaluate0(get), T0Mint(0))
                self.assertBoardColumns(t0erm_cbv_evaluate0(put), self.columns)

    def test_computed_arguments_and_composed_calls(self):
        index = T0Mop2("+", T0Mint(1), T0Mint(1))
        column = T0Mop2("+", T0Mint(2), T0Mint(3))
        put = T0Mapp(BOARD_SET, tuple_term(self.board, index, column))
        get = T0Mapp(BOARD_GET, tuple_term(put, index))
        self.assertEqual(t0erm_cbv_evaluate0(get), T0Mint(5))

    def test_board_entries_are_unrestricted_integers_like_ats(self):
        columns = (-3, 10, 0, 0, 0, 0, 0, 0)
        board = make_board(columns)
        call = T0Mapp(BOARD_GET, tuple_term(board, T0Mint(0)))
        self.assertEqual(t0erm_cbv_evaluate0(call), T0Mint(-3))
        put = T0Mapp(BOARD_SET, tuple_term(board, T0Mint(7), T0Mint(-9)))
        self.assertBoardColumns(t0erm_cbv_evaluate0(put), columns[:-1] + (-9,))

    def test_terms_and_complete_calls_are_closed(self):
        for term in (BOARD_GET, BOARD_SET,
                     T0Mapp(BOARD_GET, tuple_term(self.board, T0Mint(2))),
                     T0Mapp(BOARD_SET, tuple_term(self.board, T0Mint(2), T0Mint(5)))):
            with self.subTest(term_type=type(term).__name__):
                self.assertEqual(t0erm_fvset(term), frozenset())


class TestSafetyTerms(unittest.TestCase):
    def check_one(self, row, column, previous_row, previous_column):
        args = tuple_term(*(T0Mint(n) for n in (row, column, previous_row, previous_column)))
        return t0erm_cbv_evaluate0(T0Mapp(SAFETY_TEST1, args))

    def check_previous(self, row, column, board, last_row):
        args = tuple_term(T0Mint(row), T0Mint(column), board, T0Mint(last_row))
        return t0erm_cbv_evaluate0(T0Mapp(SAFETY_TEST2, args))

    def test_single_queen_examples(self):
        cases = (
            ((1, 2, 0, 0), True),   # Safe.
            ((1, 0, 0, 0), False),  # Same column.
            ((1, 1, 0, 0), False),  # One diagonal direction.
            ((1, 0, 0, 1), False),  # Other diagonal direction.
            ((0, 0, 3, 3), False),  # Negative row and column differences.
            ((3, 1, 0, 5), True),
        )
        for coordinates, expected in cases:
            with self.subTest(coordinates=coordinates):
                self.assertEqual(self.check_one(*coordinates), T0Mbtf(expected))

    def test_all_candidate_pairs_on_eight_row_board(self):
        # Independent oracle: diagonal lines have equal row-column or row+column.
        for row in range(1, 8):
            for previous_row in range(row):
                for column in range(8):
                    for previous_column in range(8):
                        expected = (
                            column != previous_column
                            and row - column != previous_row - previous_column
                            and row + column != previous_row + previous_column
                        )
                        with self.subTest(coordinates=(row, column, previous_row, previous_column)):
                            self.assertEqual(self.check_one(row, column, previous_row, previous_column),
                                             T0Mbtf(expected))

    def test_every_candidate_against_reference_prefix(self):
        columns = parse_ats_output(REFERENCE.read_text(encoding="utf-8"))[0]
        board = make_board(columns)
        for row in range(8):
            for column in range(8):
                expected = all(
                    column != columns[previous]
                    and row - column != previous - columns[previous]
                    and row + column != previous + columns[previous]
                    for previous in range(row)
                )
                with self.subTest(row=row, column=column):
                    self.assertEqual(self.check_previous(row, column, board, row - 1),
                                     T0Mbtf(expected))

    def test_no_previous_rows(self):
        for last_row in (-1, -5):
            with self.subTest(last_row=last_row):
                # Deliberately unusable board proves the base case performs no lookup.
                self.assertEqual(self.check_previous(0, 0, T0Mint(0), last_row), T0Mbtf(True))

    def test_ignores_rows_after_last_row(self):
        board = make_board((0, 2, 4, 4, 4, 4, 4, 4))
        self.assertEqual(self.check_previous(2, 4, board, 1), T0Mbtf(True))

    def test_recursion_reaches_earliest_conflict(self):
        board = make_board((0, 2, 0, 0, 0, 0, 0, 0))
        # (2, 0) is safe against row 1, but conflicts with row 0's column.
        self.assertEqual(self.check_previous(2, 0, board, 1), T0Mbtf(False))

    def test_conflict_stops_before_next_row(self):
        # Invalid earlier value is a probe: visiting row 0 would raise TypeError.
        board = tuple_term(T0Mstr("must not visit"), T0Mint(4), *(T0Mint(0) for _ in range(6)))
        self.assertEqual(self.check_previous(2, 4, board, 1), T0Mbtf(False))

    def test_column_conflict_skips_diagonal_check(self):
        # Arguments are values, but row subtraction would fail if evaluated.
        args = tuple_term(T0Mstr("unused row"), T0Mint(4), T0Mint(0), T0Mint(4))
        self.assertEqual(t0erm_cbv_evaluate0(T0Mapp(SAFETY_TEST1, args)), T0Mbtf(False))

    def test_safety_terms_and_calls_are_closed(self):
        board = make_board((0,) * 8)
        for term in (SAFETY_TEST1, SAFETY_TEST2,
                     T0Mapp(SAFETY_TEST1, tuple_term(*(T0Mint(n) for n in (1, 2, 0, 0)))),
                     T0Mapp(SAFETY_TEST2, tuple_term(T0Mint(0), T0Mint(0), board, T0Mint(-1)))):
            with self.subTest(term_type=type(term).__name__):
                self.assertEqual(t0erm_fvset(term), frozenset())


class TestSearchHelpers(unittest.TestCase):
    def test_reverse_empty_single_and_multiple_entries(self):
        for entries in ((), (1,), (1, 2, 3)):
            with self.subTest(entries=entries):
                source = EMPTY_LIST
                expected = EMPTY_LIST
                for entry in reversed(entries):
                    source = list_cons(T0Mint(entry), source)
                for entry in entries:
                    expected = list_cons(T0Mint(entry), expected)
                call = T0Mapp(REVERSE_LIST, tuple_term(source, EMPTY_LIST))
                self.assertEqual(t0erm_cbv_evaluate0(call), expected)

    def test_exhausted_first_row_ends_search(self):
        state = tuple_term(make_board((0,) * 8), T0Mint(0), T0Mint(8), T0Mint(0), EMPTY_LIST)
        self.assertEqual(t0erm_cbv_evaluate0(T0Mapp(SEARCH, state)), T0Mpair(T0Mint(0), EMPTY_LIST))

    def test_complete_terms_are_closed(self):
        for term in (SEARCH, REVERSE_LIST, build_queens_term()):
            self.assertEqual(t0erm_fvset(term), frozenset())

    def test_decode_empty_result(self):
        self.assertEqual(decode_result(T0Mpair(T0Mint(0), EMPTY_LIST)), (0, []))

    def test_decode_rejects_malformed_result(self):
        board = make_board((0,) * 8)
        cases = (
            T0Mint(0),
            T0Mpair(T0Mbtf(False), EMPTY_LIST),
            T0Mpair(T0Mint(-1), EMPTY_LIST),
            T0Mpair(T0Mint(1), EMPTY_LIST),
            T0Mpair(T0Mint(0), T0Mpair(T0Mint(0), T0Mint(0))),
            T0Mpair(T0Mint(0), T0Mpair(T0Mbtf(False), T0Mint(1))),
            T0Mpair(T0Mint(1), list_cons(T0Mint(0), EMPTY_LIST)),
            T0Mpair(T0Mint(1), list_cons(board, T0Mint(0))),
        )
        for value in cases:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    decode_result(value)


class TestQueensSearch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.count, cls.boards = decode_result(t0erm_cbv_evaluate0(build_queens_term()))

    def test_count_and_unique_boards(self):
        self.assertEqual(self.count, 92)
        self.assertEqual(len(self.boards), 92)
        self.assertEqual(len(set(self.boards)), 92)

    def test_every_returned_board_is_valid(self):
        for number, board in enumerate(self.boards, start=1):
            with self.subTest(solution=number):
                self.assertEqual(len(board), 8)
                self.assertEqual(set(board), set(range(8)))
                self.assertEqual(len({row - col for row, col in enumerate(board)}), 8)
                self.assertEqual(len({row + col for row, col in enumerate(board)}), 8)

    def test_complete_order_matches_captured_ats_output(self):
        expected = parse_ats_output(REFERENCE.read_text(encoding="utf-8"))
        self.assertEqual(self.boards, expected)


if __name__ == "__main__":
    unittest.main(verbosity=2)
