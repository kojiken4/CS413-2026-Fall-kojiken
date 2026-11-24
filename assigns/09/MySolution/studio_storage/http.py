"""Flask transport for the v1 storage API."""

import json
from typing import NoReturn

from flask import Flask, Response, jsonify, request
from werkzeug.exceptions import HTTPException

from .errors import ApiError, invalid_request
from .models import Program
from .service import StorageService, revision_tag
from .store import MemoryStore, Store
from .validation import page_parameters, program_write, record_id

MAX_BODY_BYTES = 262_144

HTTP_ERRORS = {
    400: ("invalid_request", "The request is invalid."),
    404: ("record_not_found", "The requested route does not exist."),
    405: ("method_not_allowed", "The method is unsupported on this route."),
    413: ("request_too_large", f"The HTTP request body must be at most {MAX_BODY_BYTES} bytes."),
    500: ("internal_error", "An unexpected server failure occurred."),
}


def _reject_json_constant(value: str) -> NoReturn:
    raise ValueError(f"{value} is not a JSON number")


def _read_json() -> object:
    if request.mimetype != "application/json":
        raise ApiError(415, "unsupported_media_type", "Use Content-Type: application/json.")
    try:
        return json.loads(request.get_data().decode("utf-8"), parse_constant=_reject_json_constant)
    except (ValueError, RecursionError):
        raise invalid_request("The request body must be valid UTF-8 JSON.") from None


def _program_response(program: Program, status: int = 200) -> Response:
    response = jsonify(program=program.to_dict())
    response.status_code = status
    response.headers["ETag"] = revision_tag(program.revision)
    return response


def _error_response(error: ApiError) -> Response:
    fields: dict[str, str | int] = {"code": error.code, "message": str(error)}
    if error.current_revision is not None:
        fields["current_revision"] = error.current_revision
    response = jsonify(error=fields)
    response.status_code = error.status
    return response


def create_app(store: Store | None = None) -> Flask:
    app = Flask(__name__, static_folder=None)
    app.config.update(MAX_CONTENT_LENGTH=MAX_BODY_BYTES, PROVIDE_AUTOMATIC_OPTIONS=False)
    service = StorageService(store if store is not None else MemoryStore())

    @app.errorhandler(ApiError)
    def handle_api_error(error: ApiError) -> Response:
        return _error_response(error)

    @app.errorhandler(HTTPException)
    def handle_http_error(error: HTTPException) -> Response:
        status = error.code
        if status not in HTTP_ERRORS:
            status = 500
        code, message = HTTP_ERRORS[status]
        response = _error_response(ApiError(status, code, message))
        if status == 405:
            response.headers["Allow"] = error.get_response().headers["Allow"]
        return response

    @app.get("/api/v1/health")
    def health() -> Response:
        return jsonify(status="ok", version="1.0")

    @app.post("/api/v1/programs")
    def create_program() -> Response:
        program = service.create_program(program_write(_read_json()))
        return _program_response(program, status=201)

    @app.get("/api/v1/programs")
    def list_programs() -> Response:
        limit, cursor = page_parameters(request.args.to_dict(flat=False))
        items, next_cursor = service.list_programs(limit, cursor)
        return jsonify(items=[program.to_dict() for program in items], next_cursor=next_cursor)

    @app.get("/api/v1/programs/<program_id>")
    def get_program(program_id: str) -> Response:
        return _program_response(service.get_program(record_id(program_id)))

    @app.put("/api/v1/programs/<program_id>")
    def update_program(program_id: str) -> Response:
        program_id = record_id(program_id)
        if_match = request.headers.get("If-Match")
        # Check preconditions before reading the body. The write checks again
        # under the same lock as the mutation in case another caller won.
        service.check_program_revision(program_id, if_match)
        program = service.update_program(program_id, if_match, program_write(_read_json()))
        return _program_response(program)

    @app.delete("/api/v1/programs/<program_id>")
    def delete_program(program_id: str) -> Response:
        service.delete_program(record_id(program_id), request.headers.get("If-Match"))
        return Response(status=204)

    return app
