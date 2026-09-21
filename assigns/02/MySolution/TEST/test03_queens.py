"""ATS2 reference checks; translation comparisons will be added later."""

import unittest
from pathlib import Path


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


if __name__ == "__main__":
    unittest.main(verbosity=2)
