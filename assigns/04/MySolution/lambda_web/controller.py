"""HTTP controller; source transitions and backend dispatch follow later."""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from .view import render_landing_page

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def landing_page() -> HTMLResponse:
    """Return the initial view without invoking language tools."""
    return HTMLResponse(render_landing_page())
