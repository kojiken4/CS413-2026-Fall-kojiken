"""Build LAMBDA0 terms translating queens.dats; board and safety operations.

Python loops here construct finite ASTs. Runtime board access and updates use
LAMBDA0 conditionals and projections executed by t0erm_cbv_evaluate0.
"""

from lambda0 import (
    t0erm, T0Mint, T0Mbtf, T0Mvar, T0Mlam, T0Mfix, T0Mapp,
    T0Mpair, T0Mpfst, T0Mpsnd, T0Mif0, T0Mop1, T0Mop2,
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
