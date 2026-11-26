"""Flask transport for the v1 storage API."""

import json
from typing import NoReturn

from flask import Flask, Response, jsonify, request
from werkzeug.exceptions import HTTPException, RequestEntityTooLarge

from .errors import ApiError, invalid_request
from .models import Collection, Program
from .service import StorageService, revision_tag
from .store import MemoryStore, Store
from .validation import case_write, collection_write, page_parameters, program_write, record_id

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


def _record_response(key: str, record: Program | Collection, status: int = 200) -> Response:
    response = jsonify({key: record.to_dict()})
    response.status_code = status
    response.headers["ETag"] = revision_tag(record.revision)
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
    app.url_map.merge_slashes = False
    service = StorageService(store if store is not None else MemoryStore())

    @app.before_request
    def enforce_api_body_limit() -> None:
        if request.url_rule is None or not request.path.startswith("/api/v1/"):
            return
        if request.content_length is not None:
            if request.content_length > MAX_BODY_BYTES:
                raise RequestEntityTooLarge()
        elif request.environ.get("wsgi.input_terminated"):
            # Read one extra byte to distinguish a full body from a truncated one.
            request.max_content_length = MAX_BODY_BYTES + 1
            if len(request.get_data()) > MAX_BODY_BYTES:
                raise RequestEntityTooLarge()

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
        return _record_response("program", program, status=201)

    @app.get("/api/v1/programs")
    def list_programs() -> Response:
        limit, cursor = page_parameters(request.args.to_dict(flat=False))
        items, next_cursor = service.list_programs(limit, cursor)
        return jsonify(items=[program.to_dict() for program in items], next_cursor=next_cursor)

    @app.get("/api/v1/programs/<program_id>")
    def get_program(program_id: str) -> Response:
        return _record_response("program", service.get_program(record_id(program_id)))

    @app.put("/api/v1/programs/<program_id>")
    def update_program(program_id: str) -> Response:
        program_id = record_id(program_id)
        if_match = request.headers.get("If-Match")
        # Check preconditions before parsing the payload. The write checks again
        # under the same lock as the mutation in case another caller won.
        service.check_program_revision(program_id, if_match)
        program = service.update_program(program_id, if_match, program_write(_read_json()))
        return _record_response("program", program)

    @app.delete("/api/v1/programs/<program_id>")
    def delete_program(program_id: str) -> Response:
        service.delete_program(record_id(program_id), request.headers.get("If-Match"))
        return Response(status=204)

    @app.post("/api/v1/collections")
    def create_collection() -> Response:
        collection = service.create_collection(collection_write(_read_json()))
        return _record_response("collection", collection, status=201)

    @app.get("/api/v1/collections")
    def list_collections() -> Response:
        limit, cursor = page_parameters(request.args.to_dict(flat=False))
        items, next_cursor = service.list_collections(limit, cursor)
        return jsonify(items=[collection.to_dict() for collection in items], next_cursor=next_cursor)

    @app.get("/api/v1/collections/<collection_id>")
    def get_collection(collection_id: str) -> Response:
        return _record_response("collection", service.get_collection(record_id(collection_id)))

    @app.put("/api/v1/collections/<collection_id>")
    def update_collection(collection_id: str) -> Response:
        collection_id = record_id(collection_id)
        if_match = request.headers.get("If-Match")
        service.check_collection_revision(collection_id, if_match)
        collection = service.update_collection(collection_id, if_match, collection_write(_read_json()))
        return _record_response("collection", collection)

    @app.delete("/api/v1/collections/<collection_id>")
    def delete_collection(collection_id: str) -> Response:
        service.delete_collection(record_id(collection_id), request.headers.get("If-Match"))
        return Response(status=204)

    @app.post("/api/v1/collections/<collection_id>/cases")
    def append_case(collection_id: str) -> Response:
        collection_id = record_id(collection_id)
        if_match = request.headers.get("If-Match")
        service.check_collection_revision(collection_id, if_match)
        collection = service.append_case(collection_id, if_match, case_write(_read_json()))
        return _record_response("collection", collection, status=201)

    @app.put("/api/v1/collections/<collection_id>/cases/<case_id>")
    def update_case(collection_id: str, case_id: str) -> Response:
        collection_id = record_id(collection_id)
        case_id = record_id(case_id)
        if_match = request.headers.get("If-Match")
        service.check_case_revision(collection_id, case_id, if_match)
        collection = service.update_case(collection_id, case_id, if_match, case_write(_read_json()))
        return _record_response("collection", collection)

    @app.delete("/api/v1/collections/<collection_id>/cases/<case_id>")
    def delete_case(collection_id: str, case_id: str) -> Response:
        collection = service.delete_case(
            record_id(collection_id), record_id(case_id), request.headers.get("If-Match"),
        )
        return _record_response("collection", collection)

    return app
