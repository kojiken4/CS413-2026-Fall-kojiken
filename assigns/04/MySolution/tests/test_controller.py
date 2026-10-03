"""Controller workflows, backend substitution, and concurrent HTTP behavior."""

import asyncio
import json
from pathlib import Path
from threading import Event

import httpx
import pytest
from fastapi.testclient import TestClient
from starlette.datastructures import UploadFile

from lambda_web.app import create_app
from lambda_web.bounded_backend import BoundedBackend
from lambda_web.contracts import GeneratedArtifact, Operation, OperationResult, Outcome

SAMPLES = Path(__file__).resolve().parents[1] / "samples"


class TestBackend:
    __test__ = False

    def __init__(self):
        self.calls = []
        self.failure = None
        self.gate = None
        self.started = Event()

    def _result(self, operation, source, revision):
        self.calls.append((operation, source, revision))
        if self.gate is not None:
            self.started.set()
            if not self.gate.wait(timeout=5):
                raise RuntimeError("Test backend was not released")
        if self.failure is not None:
            raise self.failure
        outcome = Outcome.NOT_IMPLEMENTED if operation in (Operation.TYPECHECK, Operation.COMPILE) else Outcome.SUCCESS
        return OperationResult(operation, revision, outcome, "fixture output\n<script>literal</script>")

    def lint(self, source, revision):
        return self._result(Operation.LINT, source, revision)

    def interpret(self, source, revision):
        return self._result(Operation.INTERPRET, source, revision)

    def typecheck(self, source, revision):
        return self._result(Operation.TYPECHECK, source, revision)

    def compile(self, source, revision):
        return self._result(Operation.COMPILE, source, revision)

    def execute(self, artifact, revision):
        raise AssertionError("Execute must not reach the backend")


@pytest.fixture
def backend():
    return TestBackend()


@pytest.fixture
def client(backend):
    with TestClient(create_app(backend=backend)) as client:
        yield client


def apply(client, source="D0Eint(42)"):
    assert client.post("/api/source/draft", json={"source": source}).status_code == 200
    response = client.post("/api/source/apply")
    assert response.status_code == 200
    return response.json()


def test_initial_state_and_independent_applications(client):
    state = client.get("/api/state").json()
    assert state["applied_source"] is None
    assert state["revision"] == 0
    assert state["draft"] == ""
    assert not any(state["enabled_actions"].values())
    assert isinstance(client.app.state.controller.backend, TestBackend)
    with TestClient(create_app()) as other:
        assert isinstance(other.app.state.controller.backend, BoundedBackend)
        apply(client)
        assert other.get("/api/state").json()["revision"] == 0


def test_manual_input_edit_apply_and_discard(client):
    assert client.post("/api/source/manual").status_code == 200
    state = apply(client)
    assert state["source_name"] == "Manual input"
    assert state["revision"] == 1
    client.post("/api/actions/lint")
    draft = client.post("/api/source/draft", json={"source": "D0Eint(2)"}).json()
    assert draft["dirty"]
    assert draft["applied_source"] == "D0Eint(42)"
    restored = client.post("/api/source/discard").json()
    assert restored["draft"] == "D0Eint(42)"
    assert restored["revision"] == 1
    assert len(restored["results"]) == 1
    state = apply(client, "D0Eint(3)")
    assert state["revision"] == 2
    assert state["results"] == []


@pytest.mark.parametrize("operation", ["lint", "interpret", "typecheck", "compile"])
def test_dispatch_with_substituted_backend_and_unchanged_view(client, backend, operation):
    page_before = client.get("/").text
    apply(client)
    response = client.post(f"/api/actions/{operation}")
    assert response.status_code == 200
    result = response.json()["result"]
    assert backend.calls == [(Operation(operation), "D0Eint(42)", 1)]
    assert result["operation"] == operation
    assert result["source_revision"] == 1
    assert result["outcome"] == ("not_implemented" if operation in {"typecheck", "compile"} else "success")
    assert result["output"] == "fixture output\n<script>literal</script>"
    assert response.json()["state"]["results"] == [result]
    assert not response.json()["state"]["busy"]
    assert client.get("/").text == page_before


@pytest.mark.parametrize("operation", ["lint", "interpret", "typecheck", "compile", "execute"])
def test_applied_source_required(client, backend, operation):
    assert client.post(f"/api/actions/{operation}").status_code == 409
    assert backend.calls == []


def test_execute_unavailable_and_never_dispatched(client, backend):
    apply(client)
    state = client.get("/api/state").json()
    assert not state["artifact_available"]
    assert not state["enabled_actions"]["execute"]
    response = client.post("/api/actions/execute")
    assert response.status_code == 409
    assert "no generated code" in response.json()["detail"]
    assert backend.calls == []


@pytest.mark.parametrize("endpoint, payload", [
    ("/api/source/manual", None),
    ("/api/source/canned", {"name": "factorial"}),
    ("/api/actions/lint", None),
    ("/api/actions/interpret", None),
    ("/api/actions/typecheck", None),
    ("/api/actions/compile", None),
    ("/api/actions/execute", None),
])
def test_dirty_state_blocks_actions_and_replacement(client, endpoint, payload):
    apply(client)
    client.post("/api/source/draft", json={"source": "D0Eint(2)"})
    before = client.get("/api/state").json()
    response = client.post(endpoint, json=payload)
    assert response.status_code == 409
    assert response.json()["state"] == before


def test_dirty_state_blocks_upload_without_losing_draft(client):
    apply(client)
    client.post("/api/source/draft", json={"source": "D0Eint(2)"})
    before = client.get("/api/state").json()
    response = client.post("/api/source/upload", files={"file": ("new.txt", b"D0Eint(9)")})
    assert response.status_code == 409
    assert client.get("/api/state").json() == before


@pytest.mark.parametrize("source", ["", " ", "x" * 65537, "\ud800"],
                         ids=["empty", "whitespace", "oversized", "invalid-unicode"])
def test_rejected_edits_preserve_source_results_and_correctable_draft(client, source):
    apply(client)
    client.post("/api/actions/lint")
    response = client.post(
        "/api/source/draft", content=json.dumps({"source": source}, ensure_ascii=True),
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 200
    rejected = client.post("/api/source/apply")
    assert rejected.status_code == 400
    state = rejected.json()["state"]
    assert state["applied_source"] == "D0Eint(42)"
    assert state["draft"] == source
    assert state["revision"] == 1
    assert len(state["results"]) == 1
    assert apply(client, "D0Eint(2)")["revision"] == 2


def test_upload_and_canned_replacement_increment_revisions(client, tmp_path):
    original = tmp_path / "original.txt"
    original.write_text("D0Eint(1)", encoding="utf-8")
    uploaded = client.post("/api/source/upload", files={"file": ("original.txt", original.read_bytes())})
    assert uploaded.status_code == 200
    assert uploaded.json()["source_name"] == "original.txt"
    assert uploaded.json()["revision"] == 1
    apply(client, "D0Eint(2)")
    assert original.read_text(encoding="utf-8") == "D0Eint(1)"
    client.post("/api/actions/lint")
    for revision, name in [(3, "factorial"), (4, "fibonacci"), (5, "fibonacci")]:
        response = client.post("/api/source/canned", json={"name": name})
        assert response.status_code == 200
        assert response.json()["revision"] == revision
        assert response.json()["source_name"] == name.capitalize()
        assert response.json()["draft"] == (SAMPLES / f"{name}.txt").read_text(encoding="utf-8")
        assert response.json()["results"] == []


@pytest.mark.parametrize("content", [b"\xff", b"x" * 65537], ids=["invalid-utf8", "oversized"])
def test_rejected_upload_preserves_complete_applied_state(client, content):
    apply(client)
    client.post("/api/actions/lint")
    before = client.get("/api/state").json()
    response = client.post("/api/source/upload", files={"file": ("rejected.txt", content)})
    assert response.status_code == 400
    assert response.json()["state"] == before


def test_empty_upload_retains_rejected_text_for_correction(client):
    apply(client)
    rejected = client.post("/api/source/upload", files={"file": ("empty.txt", b"")})
    assert rejected.status_code == 400
    assert rejected.json()["state"]["draft"] == ""
    assert rejected.json()["state"]["applied_source"] == "D0Eint(42)"
    state = apply(client, "D0Eint(2)")
    assert state["source_name"] == "empty.txt"


def test_upload_size_boundary_unicode_and_file_cleanup(client, monkeypatch):
    closed = []
    real_close = UploadFile.close

    async def close(file):
        await real_close(file)
        closed.append(file.file.closed)

    monkeypatch.setattr(UploadFile, "close", close)
    response = client.post("/api/source/upload", files={"file": ("max.txt", b"x" * 65536)})
    assert response.status_code == 200
    response = client.post("/api/source/upload", files={"file": ("unicode.txt", "D0Evar('é')".encode("utf-8"))})
    assert response.status_code == 200
    assert response.json()["applied_source"] == "D0Evar('é')"
    assert closed and all(closed)


@pytest.mark.parametrize("body", [{}, {"source": 42}, {"source": None}, {"source": ["x"]}])
def test_invalid_request_fields_do_not_change_state(client, body):
    before = client.get("/api/state").json()
    response = client.post("/api/source/draft", json=body)
    assert response.status_code == 422
    assert response.json()["state"] == before


def test_unknown_examples_actions_and_malformed_json(client):
    before = client.get("/api/state").json()
    assert client.post("/api/source/canned", json={"name": "../factorial"}).status_code == 404
    assert client.post("/api/actions/not-an-operation").status_code == 422
    assert client.post("/api/source/draft", content="{", headers={"content-type": "application/json"}).status_code == 422
    assert client.post("/api/source/upload").status_code == 422
    assert client.get("/api/state").json() == before


def test_backend_exception_is_recorded_and_retry_succeeds(client, backend):
    apply(client)
    backend.failure = RuntimeError("injected failure")
    failed = client.post("/api/actions/interpret")
    assert failed.status_code == 200
    assert failed.json()["result"]["outcome"] == "backend_failure"
    assert "injected failure" in failed.json()["result"]["output"]
    assert failed.json()["state"]["applied_source"] == "D0Eint(42)"
    assert not failed.json()["state"]["busy"]
    backend.failure = None
    assert client.post("/api/actions/interpret").json()["result"]["outcome"] == "success"


@pytest.mark.parametrize("result", [
    None,
    OperationResult(Operation.LINT, 99, Outcome.SUCCESS, "stale"),
    OperationResult(Operation.INTERPRET, 1, Outcome.SUCCESS, "wrong action"),
    OperationResult(Operation.LINT, 1, Outcome.SUCCESS, 42),
    OperationResult(Operation.LINT, 1, Outcome.SUCCESS, "artifact", artifact=GeneratedArtifact(1, "code", "format")),
])
def test_invalid_backend_completion_restores_availability(client, backend, result, monkeypatch):
    apply(client)
    monkeypatch.setattr(backend, "lint", lambda *args: result)
    response = client.post("/api/actions/lint")
    assert response.status_code == 200
    assert response.json()["result"]["outcome"] == "backend_failure"
    assert not response.json()["state"]["busy"]
    assert response.json()["state"]["enabled_actions"]["lint"]


def test_actual_backend_examples_errors_and_placeholders():
    with TestClient(create_app()) as client:
        for name, expected in [("factorial", "D0Vint(arg1=120)"), ("fibonacci", "D0Vint(arg1=8)")]:
            client.post("/api/source/canned", json={"name": name})
            assert client.post("/api/actions/lint").json()["result"]["outcome"] == "success"
            assert client.post("/api/actions/interpret").json()["result"]["output"] == expected
        apply(client, 'D0Evar("x")')
        assert client.post("/api/actions/lint").json()["result"]["free_variables"] == ["x"]
        assert client.post("/api/actions/interpret").json()["result"]["outcome"] == "runtime_error"
        apply(client, 'D0Eop2("/", D0Eint(1), D0Eint(0))')
        assert client.post("/api/actions/lint").json()["result"]["outcome"] == "success"
        assert client.post("/api/actions/interpret").json()["result"]["outcome"] == "runtime_error"
        apply(client, "D0Eint(")
        assert client.post("/api/actions/interpret").json()["result"]["outcome"] == "invalid_input"
        for operation in ["typecheck", "compile"]:
            result = client.post(f"/api/actions/{operation}").json()["result"]
            assert result["outcome"] == "not_implemented"
            assert result["artifact"] is None


async def wait_started(backend):
    assert await asyncio.to_thread(backend.started.wait, 2)


def test_concurrent_requests_keep_state_responsive_and_block_conflicts(backend):
    async def scenario():
        backend.gate = Event()
        app = create_app(backend=backend)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            await client.post("/api/source/draft", json={"source": "D0Eint(42)"})
            await client.post("/api/source/apply")
            action = asyncio.create_task(client.post("/api/actions/interpret"))
            try:
                await wait_started(backend)
                state_response = await asyncio.wait_for(client.get("/api/state"), timeout=1)
                assert state_response.json()["busy"]
                for endpoint, kwargs in [
                    ("/api/source/draft", {"json": {"source": "D0Eint(2)"}}),
                    ("/api/source/apply", {}),
                    ("/api/source/discard", {}),
                    ("/api/source/manual", {}),
                    ("/api/source/canned", {"json": {"name": "factorial"}}),
                    ("/api/source/upload", {"files": {"file": ("new.txt", b"D0Eint(2)")}}),
                    ("/api/actions/lint", {}),
                    ("/api/actions/interpret", {}),
                ]:
                    response = await asyncio.wait_for(client.post(endpoint, **kwargs), timeout=1)
                    assert response.status_code == 409
                    assert response.json()["state"]["busy"]
                assert len(backend.calls) == 1
            finally:
                backend.gate.set()
                response = await action
            assert response.json()["result"]["outcome"] == "success"
            assert not response.json()["state"]["busy"]
    asyncio.run(scenario())


def test_cancelled_http_wait_keeps_busy_until_worker_finishes(backend):
    async def scenario():
        backend.gate = Event()
        app = create_app(backend=backend)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            await client.post("/api/source/draft", json={"source": "D0Eint(42)"})
            await client.post("/api/source/apply")
            action = asyncio.create_task(client.post("/api/actions/interpret"))
            try:
                await wait_started(backend)
                action.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await action
                assert (await client.get("/api/state")).json()["busy"]
                assert (await client.post("/api/actions/lint")).status_code == 409
            finally:
                backend.gate.set()
                await app.state.controller.wait_for_work()
            state = (await client.get("/api/state")).json()
            assert not state["busy"]
            assert len(state["results"]) == 1
            assert (await client.post("/api/actions/lint")).status_code == 200
    asyncio.run(scenario())


def test_upload_does_not_overwrite_draft_changed_during_read(backend, monkeypatch):
    async def scenario():
        started, release = asyncio.Event(), asyncio.Event()
        real_read = UploadFile.read

        async def read(file, size=-1):
            started.set()
            await release.wait()
            return await real_read(file, size)

        monkeypatch.setattr(UploadFile, "read", read)
        app = create_app(backend=backend)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            await client.post("/api/source/draft", json={"source": "D0Eint(1)"})
            await client.post("/api/source/apply")
            upload = asyncio.create_task(client.post("/api/source/upload", files={"file": ("new.txt", b"D0Eint(2)")}))
            try:
                await asyncio.wait_for(started.wait(), 2)
                await client.post("/api/source/draft", json={"source": "D0Eint(3)"})
            finally:
                release.set()
            assert (await upload).status_code == 409
            state = (await client.get("/api/state")).json()
            assert state["draft"] == "D0Eint(3)"
            assert state["applied_source"] == "D0Eint(1)"
    asyncio.run(scenario())


def test_real_timeout_through_http_then_retry():
    with TestClient(create_app(backend=BoundedBackend(timeout_seconds=1))) as client:
        source = (SAMPLES / "fibonacci.txt").read_text(encoding="utf-8")
        source = "D0Eint(40)".join(source.rsplit("D0Eint(6)", 1))
        apply(client, source)
        response = client.post("/api/actions/interpret")
        assert response.status_code == 200
        assert response.json()["result"]["outcome"] == "backend_failure"
        assert "timed out" in response.json()["result"]["output"]
        assert response.json()["state"]["applied_source"] == source
        assert not response.json()["state"]["busy"]
        apply(client, "D0Eint(42)")
        assert client.post("/api/actions/interpret").json()["result"]["output"] == "D0Vint(arg1=42)"
