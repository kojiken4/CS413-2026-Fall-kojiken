"""HTTP source workflows and orchestration of replaceable language tools."""

import asyncio
import json
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Body, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse

from .contracts import LanguageBackend, Operation, OperationResult, Outcome
from .model import ApplicationModel, OperationRequest
from .source_validation import MAX_SOURCE_BYTES, SourceValidationError
from .view import render_landing_page

_SAMPLES = Path(__file__).resolve().parent.parent / "samples"
_CANNED = {"factorial": "factorial.txt", "fibonacci": "fibonacci.txt"}


class LiteralJSONResponse(JSONResponse):
    def render(self, content: object) -> bytes:
        # Escaping also preserves rejected drafts containing lone surrogates.
        return json.dumps(content, ensure_ascii=True, allow_nan=False).encode("utf-8")


def result_payload(result: OperationResult) -> dict:
    return {
        "operation": result.operation.value,
        "source_revision": result.source_revision,
        "outcome": result.outcome.value,
        "output": result.output,
        "free_variables": sorted(result.free_variables) if result.free_variables is not None else None,
        "artifact": None,
    }


class ApplicationController:
    def __init__(self, model: ApplicationModel, backend: LanguageBackend) -> None:
        self.model = model
        self.backend = backend
        self._work: set[asyncio.Task] = set()
        self.router = APIRouter(default_response_class=LiteralJSONResponse)
        self._register_routes()

    def snapshot(self) -> dict:
        state = self.model.state
        return {
            "applied_source": state.applied_source,
            "source_name": state.source_name,
            "draft": state.draft,
            "draft_name": state.draft_name,
            "revision": state.revision,
            "dirty": state.dirty,
            "busy": state.busy,
            "active_operation": state.active_operation.value if state.active_operation else None,
            "artifact_available": state.artifact is not None,
            "enabled_actions": {operation.value: state.can_run(operation) for operation in Operation},
            "results": [result_payload(result) for result in state.results],
        }

    async def wait_for_work(self) -> None:
        if self._work:
            await asyncio.gather(*tuple(self._work), return_exceptions=True)

    def _work_done(self, task: asyncio.Task) -> None:
        self._work.discard(task)
        if not task.cancelled():
            task.exception()

    def _run_and_record(self, request: OperationRequest) -> OperationResult:
        try:
            try:
                methods = {
                    Operation.LINT: self.backend.lint,
                    Operation.INTERPRET: self.backend.interpret,
                    Operation.TYPECHECK: self.backend.typecheck,
                    Operation.COMPILE: self.backend.compile,
                }
                result = methods[request.operation](request.source, request.source_revision)
                if (
                    not isinstance(result, OperationResult)
                    or not isinstance(result.outcome, Outcome)
                    or not isinstance(result.output, str)
                    or type(result.source_revision) is not int
                    or (result.free_variables is not None and (
                        not isinstance(result.free_variables, frozenset)
                        or any(not isinstance(name, str) for name in result.free_variables)
                    ))
                ):
                    raise ValueError("Backend returned an invalid operation result.")
                self.model.finish_operation(request, result)
            except Exception as error:
                result = OperationResult(
                    request.operation, request.source_revision, Outcome.BACKEND_FAILURE,
                    f"Backend failure ({type(error).__name__}): {error}",
                )
                self.model.finish_operation(request, result)
            return result
        finally:
            # Cleanup belongs to the worker thread, including cancelled HTTP waits.
            self.model.abort_operation(request)

    async def run_action(self, operation: Operation) -> dict:
        request = self.model.begin_operation(operation)
        task = asyncio.create_task(asyncio.to_thread(self._run_and_record, request))
        self._work.add(task)
        task.add_done_callback(self._work_done)
        result = await asyncio.shield(task)
        return {"state": self.snapshot(), "result": result_payload(result)}

    def _register_routes(self) -> None:
        router = self.router

        @router.get("/", response_class=HTMLResponse)
        def landing_page():
            return HTMLResponse(render_landing_page())

        @router.get("/api/state")
        def state():
            return self.snapshot()

        @router.post("/api/source/draft")
        def draft(source: Annotated[str, Body(embed=True, strict=True)]):
            self.model.set_draft(source)
            return self.snapshot()

        @router.post("/api/source/apply")
        def apply():
            self.model.apply_changes()
            return self.snapshot()

        @router.post("/api/source/discard")
        def discard():
            self.model.discard_changes()
            return self.snapshot()

        @router.post("/api/source/manual")
        def manual():
            self.model.start_manual_input()
            return self.snapshot()

        @router.post("/api/source/canned")
        def canned(name: Annotated[str, Body(embed=True, strict=True)]):
            if name not in _CANNED:
                raise HTTPException(404, "Unknown canned source.")
            self.model.check_source_replacement()
            source = (_SAMPLES / _CANNED[name]).read_text(encoding="utf-8")
            self.model.load_source(source, name.capitalize())
            return self.snapshot()

        @router.post("/api/source/upload")
        async def upload(file: UploadFile):
            try:
                self.model.check_source_replacement()
                raw = await file.read(MAX_SOURCE_BYTES + 1)
                if len(raw) > MAX_SOURCE_BYTES:
                    # A prefix is not the uploaded program: never replace the draft with it.
                    raise SourceValidationError(f"Source exceeds the {MAX_SOURCE_BYTES}-byte UTF-8 limit.")
                try:
                    source = raw.decode("utf-8", errors="strict")
                except UnicodeDecodeError as error:
                    raise SourceValidationError("Uploaded file must be valid UTF-8 text.") from error
                self.model.load_source(source, file.filename or "Uploaded source")
                return self.snapshot()
            finally:
                await file.close()

        @router.post("/api/actions/{operation}")
        async def action(operation: Operation):
            return await self.run_action(operation)
