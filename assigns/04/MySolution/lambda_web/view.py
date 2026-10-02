"""Read the browser view without performing language analysis."""

from pathlib import Path

_PAGE_PATH = Path(__file__).resolve().parent / "templates" / "index.html"


def render_landing_page() -> str:
    """Load UTF-8 markup relative to this module, independent of server cwd."""
    return _PAGE_PATH.read_text(encoding="utf-8")
