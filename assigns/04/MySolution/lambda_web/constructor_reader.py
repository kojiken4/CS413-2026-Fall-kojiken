"""Read validated LAMBDA constructor data without executing Python code."""

import ast

from . import lambda1

from .source_validation import (
    MAX_SOURCE_BYTES,
    SourceValidationError,
    validate_source as _validate_source,
)


class ConstructorInputError(ValueError):
    """Source cannot be read as a supported LAMBDA constructor expression."""


# Only these concrete expression constructors may be called. Field names and
# types match the supplied dataclasses; neither globals nor getattr is consulted.
_CONSTRUCTORS: dict[
    str, tuple[type[lambda1.d0exp], tuple[tuple[str, type], ...]]
] = {
    "D0Eint": (lambda1.D0Eint, (("arg1", int),)),
    "D0Ebtf": (lambda1.D0Ebtf, (("arg1", bool),)),
    "D0Evar": (lambda1.D0Evar, (("arg1", str),)),
    "D0Eop1": (lambda1.D0Eop1, (("name", str), ("arg1", lambda1.d0exp))),
    "D0Eop2": (
        lambda1.D0Eop2,
        (("name", str), ("arg1", lambda1.d0exp), ("arg2", lambda1.d0exp)),
    ),
    "D0Elam": (lambda1.D0Elam, (("arg1", str), ("arg2", lambda1.d0exp))),
    "D0Efix": (
        lambda1.D0Efix,
        (("arg1", str), ("arg2", str), ("arg3", lambda1.d0exp)),
    ),
    "D0Eapp": (
        lambda1.D0Eapp, (("arg1", lambda1.d0exp), ("arg2", lambda1.d0exp))
    ),
    "D0Eif0": (
        lambda1.D0Eif0,
        (("arg1", lambda1.d0exp), ("arg2", lambda1.d0exp), ("arg3", lambda1.d0exp)),
    ),
    "D0Elet": (
        lambda1.D0Elet,
        (("arg1", str), ("arg2", lambda1.d0exp), ("arg3", lambda1.d0exp)),
    ),
    "D0Epair": (
        lambda1.D0Epair, (("arg1", lambda1.d0exp), ("arg2", lambda1.d0exp))
    ),
    "D0Epfst": (lambda1.D0Epfst, (("arg1", lambda1.d0exp),)),
    "D0Epsnd": (lambda1.D0Epsnd, (("arg1", lambda1.d0exp),)),
}


def validate_source(source: str) -> None:
    """Preserve the reader API while sharing transport checks with the model."""
    try:
        _validate_source(source)
    except SourceValidationError as error:
        raise ConstructorInputError(str(error)) from error


def read_constructor(source: str) -> lambda1.d0exp:
    """Return one validated expression; never evaluate source or the expression.

    Accept constructor calls with positional/keyword arguments, scalar literals,
    and signed integer literals. Everything else is rejected by default.
    """
    validate_source(source)
    try:
        tree = ast.parse(source.strip(), mode="eval")
        return _read_call(tree.body)
    except SyntaxError as error:
        location = f" at line {error.lineno}, column {error.offset}" if error.lineno else ""
        raise ConstructorInputError(f"Invalid constructor syntax{location}: {error.msg}") from error
    except RecursionError as error:
        raise ConstructorInputError("Constructor input is nested too deeply.") from error


def _read_call(node: ast.expr) -> lambda1.d0exp:
    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
        raise ConstructorInputError("Expected a named LAMBDA constructor call.")
    name = node.func.id
    if name not in _CONSTRUCTORS:
        raise ConstructorInputError(f"Unsupported constructor: {name}.")
    constructor, fields = _CONSTRUCTORS[name]
    if any(isinstance(argument, ast.Starred) for argument in node.args):
        raise ConstructorInputError("Argument expansion is not allowed.")
    if len(node.args) > len(fields):
        raise ConstructorInputError(f"{name} expects {len(fields)} arguments.")

    arguments = {field[0]: argument for field, argument in zip(fields, node.args)}
    field_names = {field[0] for field in fields}
    for keyword in node.keywords:
        if keyword.arg is None:
            raise ConstructorInputError("Argument expansion is not allowed.")
        if keyword.arg not in field_names:
            raise ConstructorInputError(f"Unknown argument {keyword.arg} for {name}.")
        if keyword.arg in arguments:
            raise ConstructorInputError(f"Duplicate argument {keyword.arg} for {name}.")
        arguments[keyword.arg] = keyword.value
    missing = [field[0] for field in fields if field[0] not in arguments]
    if missing:
        raise ConstructorInputError(f"Missing arguments for {name}: {', '.join(missing)}.")

    values = [
        _read_argument(arguments[field], expected, f"{name}.{field}")
        for field, expected in fields
    ]
    return constructor(*values)


def _read_argument(node: ast.expr, expected: type, label: str) -> object:
    if expected is lambda1.d0exp:
        return _read_call(node)
    # Exact types prevent Python's bool subclass from passing as a LAMBDA int.
    if isinstance(node, ast.Constant) and type(node.value) is expected:
        return node.value
    if (
        expected is int
        and isinstance(node, ast.UnaryOp)
        and isinstance(node.op, (ast.UAdd, ast.USub))
        and isinstance(node.operand, ast.Constant)
        and type(node.operand.value) is int
    ):
        return -node.operand.value if isinstance(node.op, ast.USub) else node.operand.value
    raise ConstructorInputError(f"{label} must be a {expected.__name__} literal.")
