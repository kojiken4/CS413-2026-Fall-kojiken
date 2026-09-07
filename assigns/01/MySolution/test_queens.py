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



if __name__ == "__main__":
    unittest.main()