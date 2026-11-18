"""Validate and dispatch single JSON-RPC requests, adapted from Assign07."""

import logging
from collections.abc import Callable, Mapping
from math import isfinite


type JsonObject = dict[str, object]
type Handler = Callable[[JsonObject], JsonObject]
logger = logging.getLogger(__name__)


class RpcError(Exception):
    """An RPC failure whose message is safe to return to the caller."""

    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code


def error_response(request_id: object, error: RpcError) -> JsonObject:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": error.code, "message": str(error)}}


def _valid_id(value: object) -> bool:
    if type(value) is float:
        return isfinite(value)
    return value is None or type(value) in (str, int)


def dispatch(payload: object, methods: Mapping[str, Handler]) -> JsonObject | None:
    if (
        not isinstance(payload, dict)
        or payload.get("jsonrpc") != "2.0"
        or not isinstance(payload.get("method"), str)
        or not _valid_id(payload.get("id"))
    ):
        return error_response(None, RpcError(-32600, "Invalid Request"))

    request_id = payload.get("id")
    try:
        handler = methods.get(payload["method"])
        if handler is None:
            raise RpcError(-32601, "Method not found")
        params = payload.get("params", {})
        if not isinstance(params, dict):
            raise RpcError(-32602, "Invalid params")
        reply = {"jsonrpc": "2.0", "id": request_id, "result": handler(params)}
    except RpcError as error:
        reply = error_response(request_id, error)
    except Exception:
        logger.exception("Unexpected RPC handler failure")
        reply = error_response(request_id, RpcError(-32603, "Internal error"))

    if "id" in payload:
        return reply
    return None
