# Copyright (C) 2011 Hongwei Xi, ATS Trustful Software, Inc.
# 
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
# 
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.

# Python translation of Hongwei Xi's Eight Queens Puzzle example.
N = 8  # The original board has exactly eight rows and columns.


def print_dots(i: int) -> None:
    """Print i dots with trailing spaces; nonpositive counts print nothing."""
    while i > 0:
        print(". ", end="")
        i -= 1


def print_row(i: int) -> None:
    """Print a row with its queen at column i."""
    print_dots(i)
    print("Q ", end="")
    print_dots(N - i - 1)
    print()


def print_board(bd: tuple) -> None:
    """Print the eight rows followed by a blank line."""
    for i in range(N):
        print_row(bd[i])
    print()


def board_get(bd: tuple, i: int) -> int:
    """Return a row's column, or 0 for an out-of-range row."""
    return bd[i] if 0 <= i < N else 0


def board_set(bd: tuple, i: int, j: int) -> tuple:
    """Return an updated tuple; an out-of-range row leaves bd unchanged."""
    if 0 <= i < N:
        return bd[:i] + (j,) + bd[i + 1:]
    return bd


def safety_test1(i0: int, j0: int, i: int, j: int) -> bool:
    """Check column and diagonal conflicts, as in the original predicate."""
    return j0 != j and abs(i0 - i) != abs(j0 - j)


def safety_test2(i0: int, j0: int, bd: tuple, i: int) -> bool:
    """Check the candidate against rows i down through 0."""
    while i >= 0:
        if not safety_test1(i0, j0, i, board_get(bd, i)):
            return False
        i -= 1
    return True


def search(bd: tuple, i: int, j: int, nsol: int) -> int:
    """Print solutions in depth-first order and return the updated count."""
    # Each iteration replaces one tail call without growing Python's stack.
    while True:
        if j < N:
            if safety_test2(i, j, bd, i - 1):
                bd1 = board_set(bd, i, j)
                if i + 1 == N:
                    print(f"Solution #{nsol + 1}:\n")
                    print_board(bd1)
                    j += 1
                    nsol += 1
                else:
                    bd, i, j = bd1, i + 1, 0
            else:
                j += 1
        elif i > 0:
            i -= 1
            j = board_get(bd, i) + 1
        else:
            return nsol


def main0() -> None:
    print_board((0, 1, 2, 3, 4, 5, 6, 7))
    nsol = search((0, 0, 0, 0, 0, 0, 0, 0), 0, 0, 0)
    if nsol != 92:
        raise AssertionError("nsol must equal 92")


if __name__ == "__main__":
    main0()
