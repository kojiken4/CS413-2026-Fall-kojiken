"""Real subprocess execution, transport failures, time bounds, and recovery."""

import asyncio
import json
from pathlib import Path
import subprocess
import sys
import time

import pytest

from lambda_web import bounded_backend as bounded_module
from lambda_web.bounded_backend import BoundedBackend, DEFAULT_TIMEOUT_SECONDS
from lambda_web.contracts import Operation, OperationResult, Outcome
from lambda_web.model import ApplicationModel, ModelStateError
from lambda_web.worker_protocol import WorkerProtocolError, decode_result, encode_result

SAMPLES = Path(__file__).resolve().parents[1] / 'samples'


@pytest.fixture
def processes(monkeypatch):
    launched = []
    real_popen = subprocess.Popen
    def capture(*args, **kwargs):
        assert kwargs.get('shell') is False
        process = real_popen(*args, **kwargs)
        launched.append(process)
        return process
    monkeypatch.setattr(subprocess, 'Popen', capture)
    yield launched
    for process in launched:
        assert process.poll() is not None, 'Worker must be reaped'
        assert all(stream is None or stream.closed for stream in (process.stdin, process.stdout, process.stderr))


def test_default_timeout_is_five_seconds():
    assert BoundedBackend().timeout_seconds == DEFAULT_TIMEOUT_SECONDS == 5.0


@pytest.mark.parametrize('timeout', [0, -1, float('inf'), float('nan'), True, None, '5'])
def test_invalid_timeout_rejected(timeout):
    with pytest.raises(ValueError, match='positive finite'):
        BoundedBackend(timeout)


@pytest.mark.parametrize('operation, source, outcome, diagnostic', [
    (Operation.LINT, 'D0Eint(1)', Outcome.SUCCESS, 'No free variables'),
    (Operation.LINT, 'D0Epair(D0Evar("z"), D0Evar("a"))', Outcome.LANGUAGE_ERROR, "'a', 'z'"),
    (Operation.LINT, 'D0Eop2("/", D0Eint(1), D0Eint(0))', Outcome.SUCCESS, 'No free variables'),
    (Operation.INTERPRET, 'D0Eop2("+", D0Eint(20), D0Eint(22))', Outcome.SUCCESS, 'D0Vint(arg1=42)'),
    (Operation.INTERPRET, 'D0Epair(D0Eint(1), D0Evar("x"))', Outcome.RUNTIME_ERROR, 'D0V000()'),
    (Operation.INTERPRET, 'D0Eop2("/", D0Eint(1), D0Eint(0))', Outcome.RUNTIME_ERROR, 'ZeroDivisionError'),
    (Operation.INTERPRET, 'D0Eint()', Outcome.INVALID_INPUT, 'Missing arguments'),
])
def test_real_worker_language_results(processes, operation, source, outcome, diagnostic):
    result = getattr(BoundedBackend(), operation.value)(source, 17)
    assert result.operation is operation
    assert result.source_revision == 17
    assert result.outcome is outcome
    assert diagnostic in result.output
    assert result.artifact is None
    assert len(processes) == 1
    assert processes[0].args == [sys.executable, '-m', 'lambda_web.worker']
    assert source not in processes[0].args
    if operation is Operation.LINT:
        assert isinstance(result.free_variables, frozenset)


@pytest.mark.parametrize('filename, output', [
    ('factorial.txt', 'D0Vint(arg1=120)'), ('fibonacci.txt', 'D0Vint(arg1=8)'),
])
def test_recursive_examples_through_actual_worker(processes, filename, output):
    source = (SAMPLES / filename).read_text(encoding='utf-8')
    result = BoundedBackend().interpret(source, 2)
    assert result.outcome is Outcome.SUCCESS
    assert result.output == output


def test_worker_launch_is_independent_of_caller_directory(processes, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    result = BoundedBackend().interpret('D0Eint(42)', 3)
    assert result.outcome is Outcome.SUCCESS
    assert result.output == 'D0Vint(arg1=42)'


def test_unicode_literal_text_round_trips(processes):
    name = '<script>\u00e9</script>\n'
    result = BoundedBackend().lint(f'D0Evar({name!r})', 3)
    assert result.free_variables == frozenset({name})
    assert result.outcome is Outcome.LANGUAGE_ERROR


@pytest.mark.parametrize('source', ['', 'x' * 65537, '\ud800'], ids=['empty', 'oversized', 'invalid-unicode'])
def test_transport_rejection_does_not_launch_worker(processes, source):
    assert BoundedBackend().interpret(source, 3).outcome is Outcome.INVALID_INPUT
    assert processes == []


def test_genuinely_nonterminating_source_returns_a_diagnostic(processes):
    source = 'D0Eapp(D0Efix("loop", "x", D0Eapp(D0Evar("loop"), D0Evar("x"))), D0Eint(0))'
    result = BoundedBackend().interpret(source, 4)
    # This evaluator reaches Python's recursion limit before its worker timeout.
    assert result.outcome is Outcome.RUNTIME_ERROR
    assert 'RecursionError' in result.output


def test_real_timeout_model_recovery_retry_and_event_loop_responsiveness(processes):
    async def scenario():
        backend = BoundedBackend(timeout_seconds=1.0)
        model = ApplicationModel()
        source = (SAMPLES / 'fibonacci.txt').read_text(encoding='utf-8')
        slow_source = source.rsplit('D0Eint(6)', 1)
        model.load_source('D0Eint(40)'.join(slow_source), 'slow-fibonacci.txt')
        before = model.state
        request = model.begin_operation(Operation.INTERPRET)
        task = asyncio.create_task(asyncio.to_thread(backend.interpret, request.source, request.source_revision))
        started = time.monotonic()
        await asyncio.sleep(0.05)
        assert time.monotonic() - started < 0.75, 'Worker waiting must not block the event loop'
        assert not task.done()
        assert model.state.busy
        with pytest.raises(ModelStateError, match='in progress'):
            model.set_draft('D0Eint(42)')
        try:
            result = await task
            model.finish_operation(request, result)
        finally:
            model.abort_operation(request)
        assert result.outcome is Outcome.BACKEND_FAILURE
        assert 'timed out after 1 seconds' in result.output
        assert model.state.applied_source == before.applied_source
        assert model.state.revision == before.revision
        assert model.state.results == (result,)
        assert not model.state.busy
        assert model.state.can_run(Operation.INTERPRET)
        assert processes[0].poll() is not None
        # Retrying unchanged source succeeds for Lint; it never evaluates fib(40).
        lint_request = model.begin_operation(Operation.LINT)
        lint = await asyncio.to_thread(backend.lint, lint_request.source, lint_request.source_revision)
        model.finish_operation(lint_request, lint)
        assert lint.outcome is Outcome.SUCCESS
        model.load_source('D0Eint(42)', 'retry.txt')
        retry_request = model.begin_operation(Operation.INTERPRET)
        retry = await asyncio.to_thread(backend.interpret, retry_request.source, retry_request.source_revision)
        model.finish_operation(retry_request, retry)
        assert retry.outcome is Outcome.SUCCESS
        assert retry.output == 'D0Vint(arg1=42)'
        assert not model.state.busy
    asyncio.run(scenario())
    assert len(processes) == 3


def test_worker_crash_then_successful_retry(processes, monkeypatch):
    backend = BoundedBackend()
    real_run = subprocess.run
    def crash(command, **kwargs):
        return real_run([sys.executable, '-c', "raise RuntimeError('injected worker crash')"], **kwargs)
    monkeypatch.setattr(bounded_module.subprocess, 'run', crash)
    result = backend.interpret('D0Eint(1)', 8)
    assert result.outcome is Outcome.BACKEND_FAILURE
    assert result.source_revision == 8
    assert 'Worker exited with code' in result.output
    assert 'injected worker crash' in result.output
    monkeypatch.setattr(bounded_module.subprocess, 'run', real_run)
    assert backend.interpret('D0Eint(1)', 8).outcome is Outcome.SUCCESS


def test_process_creation_failure_returns_backend_failure(monkeypatch):
    def fail(*args, **kwargs):
        raise OSError('injected process creation failure')
    monkeypatch.setattr(bounded_module.subprocess, 'run', fail)
    result = BoundedBackend().lint('D0Eint(1)', 2)
    assert result.outcome is Outcome.BACKEND_FAILURE
    assert 'process creation failure' in result.output


def test_malformed_worker_output_is_backend_failure_and_reaped(processes, monkeypatch):
    real_run = subprocess.run
    def malformed(command, **kwargs):
        return real_run([sys.executable, '-c', "print('not JSON')"], **kwargs)
    monkeypatch.setattr(bounded_module.subprocess, 'run', malformed)
    result = BoundedBackend().interpret('D0Eint(1)', 2)
    assert result.outcome is Outcome.BACKEND_FAILURE
    assert 'Invalid worker response' in result.output


def test_placeholders_and_execute_do_not_launch_workers(processes):
    backend = BoundedBackend()
    assert backend.typecheck('invalid syntax', 1).outcome is Outcome.NOT_IMPLEMENTED
    assert backend.compile('invalid syntax', 1).outcome is Outcome.NOT_IMPLEMENTED
    assert backend.execute(None, 1).outcome is Outcome.UNAVAILABLE
    assert processes == []


def test_lint_transport_reconstructs_frozenset():
    result = OperationResult(Operation.LINT, 7, Outcome.LANGUAGE_ERROR, 'variables', frozenset({'z', 'a'}))
    encoded = encode_result(result)
    assert json.loads(encoded)['free_variables'] == ['a', 'z']
    assert decode_result(encoded, Operation.LINT, 7) == result


@pytest.mark.parametrize('changes', [
    {'operation': 'interpret'}, {'source_revision': 8}, {'source_revision': True},
    {'outcome': 'unknown'}, {'output': 1}, {'free_variables': [1]},
    {'free_variables': 'x'}, {'artifact': {'code': 'unwanted'}}, {'extra': 1},
])
def test_worker_response_validation(changes):
    data = json.loads(encode_result(OperationResult(Operation.LINT, 7, Outcome.SUCCESS, 'ok', frozenset())))
    data.update(changes)
    with pytest.raises(WorkerProtocolError):
        decode_result(json.dumps(data), Operation.LINT, 7)


@pytest.mark.parametrize('payload', ['not JSON', 'null', '[]', '{}'])
def test_invalid_worker_response_shapes(payload):
    with pytest.raises(WorkerProtocolError):
        decode_result(payload, Operation.LINT, 7)


def test_exception_while_communicating_stops_and_reaps_worker(processes, monkeypatch):
    capture_popen = subprocess.Popen
    def launch(*args, **kwargs):
        process = capture_popen(*args, **kwargs)
        def fail(*args, **kwargs):
            raise OSError('injected pipe failure')
        monkeypatch.setattr(process, 'communicate', fail)
        return process
    monkeypatch.setattr(subprocess, 'Popen', launch)
    result = BoundedBackend().interpret('D0Eint(1)', 2)
    assert result.outcome is Outcome.BACKEND_FAILURE
    assert 'pipe failure' in result.output
    assert len(processes) == 1
    assert processes[0].poll() is not None
