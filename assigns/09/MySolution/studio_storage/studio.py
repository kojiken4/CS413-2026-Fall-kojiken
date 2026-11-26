"""Serve the browser client, its storage API, and the LAMBDA3 relay."""

import json
from http.client import HTTPConnection, HTTPException
from pathlib import Path

from flask import Flask, Response, request, send_from_directory

from .errors import ApiError, invalid_request
from .http import create_app as create_storage_app

WEB_ROOT = Path(__file__).with_name("web")
LAMBDA3_PORT = 8000
LAMBDA3_RELAY_TIMEOUT = 4


def _interpretation_request(payload: object) -> bytes:
    match payload:
        case {
            "jsonrpc": "2.0", "method": "lambda.interpret", "id": str() as request_id,
            "params": {"source": str() as source},
        }:
            return json.dumps({
                "jsonrpc": "2.0", "method": "lambda.interpret", "id": request_id,
                "params": {"source": source},
            }).encode("utf-8")
    raise invalid_request("Send one LAMBDA3 interpretation request with a source and request ID.")


def _relay_interpretation(port: int, body: bytes) -> Response:
    connection = HTTPConnection("127.0.0.1", port, timeout=LAMBDA3_RELAY_TIMEOUT)
    try:
        connection.request("POST", "/rpc", body=body, headers={"Content-Type": "application/json"})
        upstream = connection.getresponse()
        if upstream.status != 200 or upstream.headers.get_content_type() != "application/json":
            raise ApiError(502, "lambda3_unavailable", "LAMBDA3 returned an unexpected response.")
        return Response(upstream.read(), mimetype="application/json")
    except TimeoutError:
        raise ApiError(504, "lambda3_timeout", "LAMBDA3 did not respond in time.") from None
    except (OSError, HTTPException):
        raise ApiError(502, "lambda3_unavailable", "Could not reach the LAMBDA3 service.") from None
    finally:
        connection.close()


def create_app(*, lambda3_port: int = LAMBDA3_PORT) -> Flask:
    app = create_storage_app()

    @app.get("/")
    def index() -> Response:
        return send_from_directory(WEB_ROOT, "index.html")

    @app.get("/studio/<path:filename>")
    def studio_asset(filename: str) -> Response:
        return send_from_directory(WEB_ROOT, filename)

    @app.post("/studio/interpret")
    def interpret() -> Response:
        if request.mimetype != "application/json":
            raise ApiError(415, "unsupported_media_type", "Use Content-Type: application/json.")
        return _relay_interpretation(lambda3_port, _interpretation_request(request.get_json()))

    return app
