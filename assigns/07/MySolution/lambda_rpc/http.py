"""Flask transport for the JSON-RPC endpoint."""

import json
from typing import NoReturn

from flask import Flask, Response, jsonify, request

from . import service
from .dispatcher import RpcError, dispatch, error_response


def health(params: dict) -> dict:
    if params:
        raise RpcError(-32602, "Invalid params")
    return {"status": "ok", "version": "1.0"}


def _reject_non_json_number(token: str) -> NoReturn:
    raise ValueError(f"{token} is not a JSON number")


def create_app() -> Flask:
    app = Flask(__name__, static_folder=None)
    methods = {
        "service.health": health,
        "lambda.typecheck": service.typecheck,
        "lambda.compile": service.compile_source,
    }

    @app.post("/rpc")
    def rpc() -> Response:
        if request.mimetype != "application/json":
            return Response(status=415)

        try:
            payload = json.loads(
                request.get_data().decode("utf-8"),
                parse_constant=_reject_non_json_number,
            )
        except (ValueError, RecursionError):
            return jsonify(error_response(None, RpcError(-32700, "Parse error")))

        reply = dispatch(payload, methods)
        if reply is None:
            return Response(status=204)
        return jsonify(reply)

    return app
