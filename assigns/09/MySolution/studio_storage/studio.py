"""Serve the browser client and its same-origin storage API."""

from pathlib import Path

from flask import Flask, Response, send_from_directory

from .http import create_app as create_storage_app

WEB_ROOT = Path(__file__).with_name("web")


def create_app() -> Flask:
    app = create_storage_app()

    @app.get("/")
    def index() -> Response:
        return send_from_directory(WEB_ROOT, "index.html")

    @app.get("/studio/<path:filename>")
    def studio_asset(filename: str) -> Response:
        return send_from_directory(WEB_ROOT, filename)

    return app
