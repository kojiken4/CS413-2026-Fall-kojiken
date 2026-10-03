"""Compose independent MVC state and a replaceable bounded language backend."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from .bounded_backend import BoundedBackend
from .contracts import LanguageBackend
from .controller import ApplicationController, LiteralJSONResponse
from .model import ApplicationModel, ModelStateError
from .source_validation import SourceValidationError


def create_app(
    model: ApplicationModel | None = None,
    backend: LanguageBackend | None = None,
) -> FastAPI:
    """Create an independent application for the local server or tests."""
    controller = ApplicationController(
        model if model is not None else ApplicationModel(),
        backend if backend is not None else BoundedBackend(),
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        try:
            yield
        finally:
            await controller.wait_for_work()

    app = FastAPI(title="LAMBDA Web Front-End", lifespan=lifespan)
    app.state.controller = controller
    app.include_router(controller.router)

    @app.exception_handler(ModelStateError)
    async def state_error(request, error):
        return LiteralJSONResponse(
            {"detail": str(error), "state": controller.snapshot()}, status_code=409,
        )

    @app.exception_handler(SourceValidationError)
    async def source_error(request, error):
        return LiteralJSONResponse(
            {"detail": str(error), "state": controller.snapshot()}, status_code=400,
        )

    @app.exception_handler(RequestValidationError)
    async def request_error(request, error):
        return LiteralJSONResponse(
            {"detail": "Invalid request fields or JSON.", "state": controller.snapshot()},
            status_code=422,
        )

    return app
