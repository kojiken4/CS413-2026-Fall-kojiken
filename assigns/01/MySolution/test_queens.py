import unittest
from queens import safety_test1, board_get



class TestQueens(unittest.TestCase):

    # testing safety test 1 with queens on same diagonal, should be false
    def test_safety_test1_reject_same_diagonal(self):
        self.assertFalse(safety_test1(i0=1, j0=1, i=0, j=0))
        self.assertFalse(safety_test1(i0=7, j0=5, i=4, j=2))

    # testing safety test 1 with queens on same column, should be false
    def test_safety_test1_reject_same_column(self):
        self.assertFalse(safety_test1(i0=1, j0=1, i=0, j=1))
        self.assertFalse(safety_test1(i0=7, j0=5, i=1, j=5))

    # testing invalid input when retrieving queen position
    def test_board_get_invalid_row(self):
        bd = (0, 1, 2, 3, 4, 5, 6, 7)
        self.assertEqual(board_get(bd, 8), 0)
        self.assertEqual(board_get(bd, -1), 0)

    # testing valid input when retrieving queen position
    def test_board_get_valid_row(self):
        bd = (0, 1, 2, 3, 4, 5, 6, 7)
        self.assertEqual(board_get(bd, 1), 1)
        self.assertEqual(board_get(bd, 6), 6)


if __name__ == "__main__":
    unittest.main()