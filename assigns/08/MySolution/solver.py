"""Load the fixed LAMBDA3 solver and translate its event stream."""

import sys
from importlib import import_module
from pathlib import Path


# As in Assign07, load the supplied interpreter from this assignment's
# directory so its top-level import of the sibling basics0 module resolves.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "LAMBDA3"))
L = import_module("lambda3")

type Board = tuple[int, ...]
type Event = dict[str, str | int | Board]

MIN_SIZE = 4
MAX_SIZE = 10

_EVENT_NAMES = {0: "try", 1: "place", 2: "reject", 3: "backtrack", 4: "solution", 5: "done"}
_FORCE_CURSOR = L.D0Eop1("lazy_eval", L.D0Evar("cursor"))


class InvalidBoardSize(ValueError):
    """The requested size is outside the supported integer range."""


class QueensSolver:
    """Load and type-check the entry point once for any number of streams."""

    def __init__(self) -> None:
        source = Path(__file__).with_name("queens.lam").read_text(encoding="utf-8")
        declarations = L.d0cls_parse(source)
        entry = L.D0Elets(declarations, L.D0Evar("queens_open"))
        integer = L.TSint()
        event = L.TTuple((integer, integer, integer, L.TList(integer)))
        expected = L.TFun(integer, L.TLazy(L.TStcn(event)))
        if L.d0exp_typecheck(entry) != expected:
            raise TypeError("Unexpected LAMBDA3 solver entry point type")
        self._environment = L.ENVcns("queens_open", L.d0exp_evaluate(entry), L.ENVnil())

    def open(self, size: object) -> L.D0Vlazy:
        """Construct a fresh cursor without forcing its first event."""
        if type(size) is not int or not MIN_SIZE <= size <= MAX_SIZE:
            raise InvalidBoardSize("Board size must be an integer from 4 through 10")
        call = L.D0Eapp(L.D0Evar("queens_open"), L.D0Eint(size))
        cursor = L.d0exp_evaluate(call, self._environment)
        if not isinstance(cursor, L.D0Vlazy):
            raise TypeError("Expected a lazy LAMBDA3 stream")
        return cursor


def force_event(cursor: L.D0Vlazy) -> tuple[Event, L.D0Vlazy] | None:
    """Return the current event and its suspended tail, or None at stream end."""
    env = L.ENVcns("cursor", cursor, L.ENVnil())
    node = L.d0exp_evaluate(_FORCE_CURSOR, env)
    if not isinstance(node, L.D0Vstcn):
        raise TypeError("Expected a LAMBDA3 stream cell")
    if not node.is_cons:
        return None
    if node.tail is None:
        raise TypeError("LAMBDA3 event cell is missing its tail")
    return _decode_event(node.head), node.tail


def _decode_event(value: L.d0val | None) -> Event:
    match value:
        case L.D0Vtupl((L.D0Vint(kind), L.D0Vint(row), L.D0Vint(column), L.D0Vlist(items))):
            name = _EVENT_NAMES.get(kind)
            if name is None:
                raise ValueError("Unknown LAMBDA3 event kind")
        case _:
            raise TypeError("Malformed LAMBDA3 event")

    if name == "done":
        return {"event": name}

    columns = []
    while isinstance(items, L.fnlist_cons):
        if not isinstance(items.arg1, L.D0Vint):
            raise TypeError("Expected an integer queen column")
        columns.append(items.arg1.arg1)
        items = items.arg2
    if not isinstance(items, L.fnlist_nil):
        raise TypeError("Malformed LAMBDA3 board list")

    board = tuple(reversed(columns))
    if name == "solution":
        return {"event": name, "board": board}
    return {"event": name, "row": row, "column": column, "board": board}
