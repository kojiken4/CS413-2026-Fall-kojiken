"""Errors shared by validation and storage operations."""


class ApiError(Exception):
    def __init__(
        self, status: int, code: str, message: str, *, current_revision: int | None = None
    ) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.current_revision = current_revision


def invalid_request(message: str) -> ApiError:
    return ApiError(400, "invalid_request", message)
