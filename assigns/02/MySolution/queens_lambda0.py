"""Translate queens.dats into LAMBDA0 and display its interpreted solutions.

Python loops here construct finite ASTs. Runtime board access and updates use
LAMBDA0 conditionals and projections executed by t0erm_cbv_evaluate0.
"""

from lambda0 import (
    t0erm, T0Mint, T0Mbtf, T0Mvar, T0Mlam, T0Mfix, T0Mapp,
    T0Mpair, T0Mpfst, T0Mpsnd, T0Mif0, T0Mop1, T0Mop2,
    t0erm_fvset, t0erm_cbv_evaluate0,
)


BOARD_SIZE = 8


def tuple_term(*fields: t0erm) -> t0erm:
    """Build pair(a, pair(b, ...)); the final field has no wrapper."""
    if len(fields) < 2:
        raise ValueError("A bundled tuple needs at least two fields")
    result = fields[-1]
    for field in reversed(fields[:-1]):
        result = T0Mpair(field, result)
    return result


def tuple_item(term: t0erm, index: int, size: int) -> t0erm:
    """Build projections for a fixed field; do not inspect or evaluate term."""
    if size < 2 or not 0 <= index < size:
        raise ValueError("Expected a valid field index in a tuple of size >= 2")
    result = term
    for _ in range(index):
        result = T0Mpsnd(result)
    return result if index == size - 1 else T0Mpfst(result)


def make_board(columns: tuple[int, ...]) -> t0erm:
    """Encode eight integer literals; this does not check queen conflicts."""
    if len(columns) != BOARD_SIZE:
        raise ValueError("A board must contain exactly eight columns")
    if any(type(column) is not int for column in columns):
        raise TypeError("Board columns must be integers")
    return tuple_term(*(T0Mint(column) for column in columns))


def _build_board_get() -> t0erm:
    args = T0Mvar("get_args")
    board = T0Mpfst(args)
    index = T0Mpsnd(args)
    body = T0Mint(0)  # ATS2 returns zero for an out-of-range index.
    for position in reversed(range(BOARD_SIZE)):
        body = T0Mif0(
            T0Mop2("==", index, T0Mint(position)),
            tuple_item(board, position, BOARD_SIZE),
            body,
        )
    return T0Mlam("get_args", body)


def _build_board_set() -> t0erm:
    args = T0Mvar("set_args")
    board = T0Mpfst(args)
    index = T0Mpfst(T0Mpsnd(args))
    column = T0Mpsnd(T0Mpsnd(args))
    fields = [tuple_item(board, position, BOARD_SIZE) for position in range(BOARD_SIZE)]
    body = board  # ATS2 returns the unchanged board for an out-of-range index.
    for position in reversed(range(BOARD_SIZE)):
        updated_fields = fields.copy()
        updated_fields[position] = column
        body = T0Mif0(
            T0Mop2("==", index, T0Mint(position)),
            tuple_term(*updated_fields),
            body,
        )
    return T0Mlam("set_args", body)


# Closed function ASTs, called with T0Mapp and one bundled argument.
BOARD_GET = _build_board_get()
BOARD_SET = _build_board_set()


def _abs_term(value: t0erm) -> t0erm:
    """Build absolute value using existing LAMBDA0 operations."""
    return T0Mif0(T0Mop2("<", value, T0Mint(0)), T0Mop1("-", value), value)


def _build_safety_test1() -> t0erm:
    args = T0Mvar("safe1_args")
    row, column, previous_row, previous_column = (
        tuple_item(args, position, 4) for position in range(4)
    )
    different_diagonals = T0Mop2(
        "!=",
        _abs_term(T0Mop2("-", row, previous_row)),
        _abs_term(T0Mop2("-", column, previous_column)),
    )
    # ATS2 andalso: do not evaluate the diagonal check after a column conflict.
    body = T0Mif0(
        T0Mop2("!=", column, previous_column),
        different_diagonals,
        T0Mbtf(False),
    )
    return T0Mlam("safe1_args", body)


SAFETY_TEST1 = _build_safety_test1()


def _build_safety_test2() -> t0erm:
    args = T0Mvar("safe2_args")
    row, column, board, previous_row = (
        tuple_item(args, position, 4) for position in range(4)
    )
    previous_column = T0Mapp(BOARD_GET, tuple_term(board, previous_row))
    safe = T0Mapp(SAFETY_TEST1, tuple_term(row, column, previous_row, previous_column))
    remaining = T0Mapp(
        T0Mvar("safe2"),
        tuple_term(row, column, board, T0Mop2("-", previous_row, T0Mint(1))),
    )
    body = T0Mif0(
        T0Mop2(">=", previous_row, T0Mint(0)),
        T0Mif0(safe, remaining, T0Mbtf(False)),
        T0Mbtf(True),
    )
    return T0Mfix("safe2", "safe2_args", body)


SAFETY_TEST2 = _build_safety_test2()


EMPTY_LIST = T0Mpair(T0Mbtf(False), T0Mint(0))


def list_cons(head: t0erm, tail: t0erm) -> t0erm:
    """Build a tagged list node without evaluating its contents."""
    return T0Mpair(T0Mbtf(True), T0Mpair(head, tail))


def _build_reverse_list() -> t0erm:
    args = T0Mvar("reverse_args")
    remaining, accumulated = T0Mpfst(args), T0Mpsnd(args)
    payload = T0Mpsnd(remaining)
    body = T0Mif0(
        T0Mpfst(remaining),
        T0Mapp(T0Mvar("reverse"), tuple_term(
            T0Mpsnd(payload), list_cons(T0Mpfst(payload), accumulated),
        )),
        accumulated,
    )
    return T0Mfix("reverse", "reverse_args", body)


REVERSE_LIST = _build_reverse_list()


def _build_search() -> t0erm:
    args = T0Mvar("search_args")
    board, row, column, count, solutions = (
        tuple_item(args, position, 5) for position in range(5)
    )
    next_column = T0Mop2("+", column, T0Mint(1))
    next_row = T0Mop2("+", row, T0Mint(1))
    previous_row = T0Mop2("-", row, T0Mint(1))

    def recur(bd, i, j, nsol, found):
        # Build a recursive call AST; Python never performs the search.
        return T0Mapp(T0Mvar("search"), tuple_term(bd, i, j, nsol, found))

    updated = T0Mvar("updated_board")
    safe_placement = T0Mapp(
        T0Mlam("updated_board", T0Mif0(
            T0Mop2("==", next_row, T0Mint(BOARD_SIZE)),
            recur(board, row, next_column, T0Mop2("+", count, T0Mint(1)),
                  list_cons(updated, solutions)),
            recur(updated, next_row, T0Mint(0), count, solutions),
        )),
        T0Mapp(BOARD_SET, tuple_term(board, row, column)),
    )
    try_column = T0Mif0(
        T0Mapp(SAFETY_TEST2, tuple_term(row, column, board, previous_row)),
        safe_placement,
        recur(board, row, next_column, count, solutions),
    )
    backtrack_or_finish = T0Mif0(
        T0Mop2(">", row, T0Mint(0)),
        recur(board, previous_row,
              T0Mop2("+", T0Mapp(BOARD_GET, tuple_term(board, previous_row)), T0Mint(1)),
              count, solutions),
        T0Mpair(count, T0Mapp(REVERSE_LIST, tuple_term(solutions, EMPTY_LIST))),
    )
    return T0Mfix("search", "search_args", T0Mif0(
        T0Mop2("<", column, T0Mint(BOARD_SIZE)), try_column, backtrack_or_finish,
    ))


SEARCH = _build_search()


def build_queens_term() -> t0erm:
    """Return the closed eight-queens program, starting with the ATS2 state."""
    return T0Mapp(SEARCH, tuple_term(
        make_board((0,) * BOARD_SIZE), T0Mint(0), T0Mint(0), T0Mint(0), EMPTY_LIST,
    ))


def _decode_board(value: t0erm) -> tuple[int, ...]:
    columns = []
    for _ in range(BOARD_SIZE - 1):
        if not isinstance(value, T0Mpair) or not isinstance(value.arg1, T0Mint):
            raise ValueError("Expected an eight-integer board value")
        columns.append(value.arg1.arg1)
        value = value.arg2
    if not isinstance(value, T0Mint):
        raise ValueError("Expected an integer in the final board field")
    columns.append(value.arg1)
    return tuple(columns)


def decode_result(value: t0erm) -> tuple[int, list[tuple[int, ...]]]:
    """Decode returned values only; no search or list reversal happens here."""
    if not isinstance(value, T0Mpair) or not isinstance(value.arg1, T0Mint):
        raise ValueError("Expected a pair containing the count and solution list")
    count, remaining = value.arg1.arg1, value.arg2
    if count < 0:
        raise ValueError("Solution count must be nonnegative")
    boards = []
    while True:
        if not isinstance(remaining, T0Mpair) or not isinstance(remaining.arg1, T0Mbtf):
            raise ValueError("Expected a boolean-tagged list value")
        if not remaining.arg1.arg1:
            if remaining.arg2 != T0Mint(0):
                raise ValueError("Expected zero padding in the empty list")
            break
        payload = remaining.arg2
        if not isinstance(payload, T0Mpair):
            raise ValueError("Expected a board and tail in the list payload")
        boards.append(_decode_board(payload.arg1))
        remaining = payload.arg2
    if len(boards) != count:
        raise ValueError("Solution count does not match the returned list length")
    return count, boards


def print_board(columns: tuple[int, ...]) -> None:
    for column in columns:
        print(". " * column + "Q " + ". " * (BOARD_SIZE - column - 1))
    print()


def main() -> None:
    term = build_queens_term()
    if t0erm_fvset(term):
        raise ValueError("The complete queens term must be closed")
    count, boards = decode_result(t0erm_cbv_evaluate0(term))
    if count != 92:
        raise ValueError(f"Expected 92 solutions, got {count}")
    # Match the original source's demonstration board and presentation.
    print_board(tuple(range(BOARD_SIZE)))
    for number, board in enumerate(boards, start=1):
        print(f"Solution #{number}:\n")
        print_board(board)


if __name__ == "__main__":
    main()
