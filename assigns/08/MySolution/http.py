"""Flask transport for the Assign08 RPC endpoint, adapted from Assign07."""

import json
from typing import NoReturn

from flask import Flask, Response, jsonify, request

from .dispatcher import RpcError, dispatch, error_response
from .rpc import methods_for
from .streams import StreamTable


def _reject_non_json_number(token: str) -> NoReturn:
    raise ValueError(f"{token} is not a JSON number")


def create_app(*, streams: StreamTable | None = None) -> Flask:
    app = Flask(__name__, static_folder="web", static_url_path="/assets")
    methods = methods_for(streams if streams is not None else StreamTable())

    @app.get("/")
    def index() -> Response:
        return app.send_static_file("index.html")

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
