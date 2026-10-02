"""Compose the FastAPI application without starting a server on import."""

from fastapi import FastAPI

from .controller import router


def create_app() -> FastAPI:
    """Create an independent application for the local server or tests."""
    app = FastAPI(title="LAMBDA Web Front-End")
    app.include_router(router)
    return app
