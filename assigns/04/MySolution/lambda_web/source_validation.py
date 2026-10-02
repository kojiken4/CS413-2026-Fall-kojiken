"""Source transport checks shared by the model and constructor reader."""

MAX_SOURCE_BYTES = 64 * 1024


class SourceValidationError(ValueError):
    """Text cannot be accepted as applied source."""


def validate_source(source: str) -> None:
    """Validate text/encoding/size without parsing or modifying source."""
    if not isinstance(source, str):
        raise SourceValidationError("Source must be text.")
    try:
        size = len(source.encode("utf-8"))
    except UnicodeEncodeError as error:
        raise SourceValidationError("Source must be valid UTF-8 text.") from error
    if size > MAX_SOURCE_BYTES:
        raise SourceValidationError(f"Source exceeds the {MAX_SOURCE_BYTES}-byte UTF-8 limit.")
    if not source.strip():
        raise SourceValidationError("Source must not be empty or whitespace-only.")
