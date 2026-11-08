"""Validate and dispatch JSON-RPC requests independently of HTTP."""

import logging
from collections.abc import Callable, Mapping
from math import isfinite


Handler = Callable[[dict], dict]
logger = logging.getLogger(__name__)


class RpcError(Exception):
    """An RPC failure whose message and data are safe to send to clients."""

    def __init__(self, code: int, message: str, data: dict | None = None):
        super().__init__(message)
        self.code = code
        self.data = data


def error_response(request_id: object, error: RpcError) -> dict:
    details = {"code": error.code, "message": str(error)}
    if error.data is not None:
        details["data"] = error.data
    return {"jsonrpc": "2.0", "id": request_id, "error": details}


def dispatch(payload: object, methods: Mapping[str, Handler]) -> dict | list | None:
    if not isinstance(payload, list):
        return _dispatch_request(payload, methods)
    if not payload:
        return error_response(None, RpcError(-32600, "Invalid Request"))

    replies = []
    for item in payload:
        reply = _dispatch_request(item, methods)
        if reply is not None:
            replies.append(reply)
    return replies or None


def _valid_id(value: object) -> bool:
    if type(value) is float:
        return isfinite(value)
    return value is None or type(value) in (str, int)


def _dispatch_request(payload: object, methods: Mapping[str, Handler]) -> dict | None:
    if (
        not isinstance(payload, dict)
        or payload.get("jsonrpc") != "2.0"
        or not isinstance(payload.get("method"), str)
        or not _valid_id(payload.get("id"))
    ):
        return error_response(None, RpcError(-32600, "Invalid Request"))

    request_id = payload.get("id")
    method = payload["method"]
    try:
        handler = methods.get(method)
        if handler is None:
            raise RpcError(-32601, "Method not found")
        params = payload.get("params")
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
