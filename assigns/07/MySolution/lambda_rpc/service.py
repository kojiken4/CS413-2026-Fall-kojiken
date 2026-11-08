"""Adapt the supplied LAMBDA3 implementation to the RPC method contract."""

import sys
from importlib import import_module
from pathlib import Path

from .dispatcher import RpcError


# The supplied module imports its sibling basics0 as a top-level module.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "LAMBDA3"))
lambda3 = import_module("lambda3")

MAX_SOURCE_BYTES = 16_384
COMPILERS = {
    "python": lambda3.d0exp_compile,
    "javascript": lambda3.d0exp_compile_js,
}


def validated_source(params: dict) -> str:
    source = params.get("source")
    if not isinstance(source, str) or not source.strip():
        raise RpcError(-32602, "Invalid params")
    try:
        size = len(source.encode("utf-8"))
    except UnicodeEncodeError as error:
        raise RpcError(-32602, "Invalid params") from error
    if size > MAX_SOURCE_BYTES:
        raise RpcError(-32602, "Invalid params")
    return source


def parse_and_typecheck(source: str) -> tuple[lambda3.d0exp, lambda3.simple_type]:
    try:
        return lambda3.d0exp_parse_and_typecheck(source)
    except lambda3.LambdaSyntaxError as error:
        location = None
        if error.lineno is not None and error.offset is not None:
            location = {"line": error.lineno, "column": error.offset}
        raise RpcError(-32010, error.msg, location) from error
    except lambda3.TypeCheckError as error:
        raise RpcError(-32011, str(error)) from error


def typecheck(params: dict) -> dict:
    _, inferred_type = parse_and_typecheck(validated_source(params))
    return {"type": lambda3.format_type(inferred_type)}


def compile_source(params: dict) -> dict:
    source = validated_source(params)
    target = params.get("target")
    if not isinstance(target, str) or target not in COMPILERS:
        raise RpcError(-32602, "Invalid params")
    expression, _ = parse_and_typecheck(source)
    return {"target": target, "code": COMPILERS[target](expression)}
