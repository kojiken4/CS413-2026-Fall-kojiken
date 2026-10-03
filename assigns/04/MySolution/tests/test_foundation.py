"""Verify the initial server composition and supplied language import."""

from fastapi.testclient import TestClient

from lambda_web.app import create_app
from lambda_web import lambda1


def test_landing_page():
    with TestClient(create_app()) as client:
        response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert '<html lang="en">' in response.text
    assert "LAMBDA Web Front-End" in response.text
    assert 'id="source-editor"' in response.text
    assert 'src="/static/app.js"' in response.text


def test_unknown_route_is_not_a_tool_action():
    with TestClient(create_app()) as client:
        assert client.get("/interpret").status_code == 404


def test_supplied_interpreter_import_and_arithmetic():
    expression = lambda1.D0Eop2("+", lambda1.D0Eint(20), lambda1.D0Eint(22))
    assert lambda1.d0exp_fvset(expression) == frozenset()
    assert lambda1.d0exp_evaluate(expression, lambda1.ENVnil()) == lambda1.D0Vint(42)
