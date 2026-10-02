"""Model rules tested directly, without HTTP requests or a browser."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
import subprocess
import sys
from threading import Barrier

import pytest

from lambda_web.contracts import GeneratedArtifact, Operation, OperationResult, Outcome
from lambda_web.model import ApplicationModel, ModelStateError
from lambda_web.source_validation import MAX_SOURCE_BYTES, SourceValidationError

SOURCE = 'D0Eint(1)'


@pytest.fixture
def model():
    return ApplicationModel()


@pytest.fixture
def loaded(model):
    model.load_source(SOURCE, 'example.txt')
    return model


def complete(model, operation=Operation.LINT, outcome=Outcome.SUCCESS):
    request = model.begin_operation(operation)
    result = OperationResult(operation, request.source_revision, outcome, 'test result')
    model.finish_operation(request, result)
    return result


def test_initial_state_and_manual_input_without_upload(model):
    assert model.state.applied_source is None
    assert model.state.source_name is None
    assert model.state.draft == ''
    assert model.state.revision == 0
    assert not model.state.dirty
    assert not model.state.busy
    model.start_manual_input()
    model.set_draft(SOURCE)
    assert model.state.dirty
    assert model.state.applied_source is None
    model.apply_changes()
    assert model.state.applied_source == SOURCE
    assert model.state.source_name == 'Manual input'
    assert model.state.revision == 1
    assert not model.state.dirty


def test_model_import_does_not_load_language_tools_or_web_framework():
    root = Path(__file__).resolve().parents[1]
    script = (
        "import sys; sys.path.insert(0, sys.argv[1]); "
        "from lambda_web.model import ApplicationModel; "
        "model = ApplicationModel(); model.set_draft('D0Eint(1)'); "
        "model.apply_changes(); assert model.state.revision == 1; "
        "assert not {'fastapi', 'lambda_web.lambda1', 'lambda_web.backend', "
        "'lambda_web.constructor_reader'} & set(sys.modules)"
    )
    completed = subprocess.run(
        [sys.executable, '-I', '-c', script, str(root)],
        capture_output=True, text=True, timeout=10,
    )
    assert completed.returncode == 0, completed.stderr


def test_snapshots_are_immutable_and_old_snapshot_remains_stable(loaded):
    before = loaded.state
    with pytest.raises(FrozenInstanceError):
        before.revision = 100
    loaded.set_draft('D0Eint(2)')
    assert before.draft == SOURCE
    assert loaded.state.draft != before.draft


def test_apply_updates_source_not_previous_snapshot_and_clears_results(loaded):
    complete(loaded)
    before = loaded.state
    loaded.set_draft('D0Eint(2)')
    assert loaded.state.applied_source == SOURCE
    assert loaded.state.results == before.results
    loaded.apply_changes()
    assert loaded.state.applied_source == 'D0Eint(2)'
    assert loaded.state.source_name == 'example.txt'
    assert loaded.state.revision == 2
    assert loaded.state.results == ()
    assert loaded.state.artifact is None
    assert not loaded.state.dirty
    assert before.applied_source == SOURCE


def test_discard_restores_applied_source_without_new_revision(loaded):
    result = complete(loaded)
    loaded.set_draft('D0Eint(2)')
    loaded.discard_changes()
    assert loaded.state.draft == SOURCE
    assert loaded.state.revision == 1
    assert loaded.state.results == (result,)
    assert not loaded.state.dirty


def test_discard_initial_draft_restores_empty_editor(model):
    model.set_draft('not a valid program')
    model.discard_changes()
    assert model.state.applied_source is None
    assert model.state.draft == ''
    assert model.state.revision == 0


def test_reverting_draft_text_removes_dirty_state(loaded):
    loaded.set_draft('D0Eint(2)')
    loaded.set_draft(SOURCE)
    assert not loaded.state.dirty
    assert loaded.state.can_run(Operation.INTERPRET)
    with pytest.raises(ModelStateError, match='no unapplied changes'):
        loaded.apply_changes()


@pytest.mark.parametrize('name', ['upload.txt', 'Factorial', 'Fibonacci'])
def test_accepted_replacement_creates_revision_and_clears_results(loaded, name):
    complete(loaded)
    loaded.load_source('D0Eint(2)', name)
    assert loaded.state.applied_source == loaded.state.draft == 'D0Eint(2)'
    assert loaded.state.source_name == loaded.state.draft_name == name
    assert loaded.state.revision == 2
    assert loaded.state.results == ()
    assert loaded.state.artifact is None


def test_reloading_identical_source_still_creates_revision(loaded):
    loaded.load_source(SOURCE, 'example.txt')
    assert loaded.state.revision == 2


def test_manual_selection_opens_blank_draft_without_replacing_applied_source(loaded):
    result = complete(loaded)
    loaded.start_manual_input()
    assert loaded.state.draft == ''
    assert loaded.state.draft_name == 'Manual input'
    assert loaded.state.applied_source == SOURCE
    assert loaded.state.revision == 1
    assert loaded.state.results == (result,)
    assert loaded.state.dirty
    loaded.set_draft('D0Eint(3)')
    loaded.apply_changes()
    assert loaded.state.source_name == 'Manual input'
    assert loaded.state.revision == 2


def test_discard_manual_selection_restores_original_name(loaded):
    loaded.start_manual_input()
    loaded.discard_changes()
    assert loaded.state.draft_name == loaded.state.source_name == 'example.txt'
    assert loaded.state.draft == SOURCE


INVALID_SOURCES = ['', '   ', 'D0Eint(1)' + ' ' * MAX_SOURCE_BYTES, '\ud800']


@pytest.mark.parametrize('source', INVALID_SOURCES, ids=['empty', 'whitespace', 'oversized', 'invalid-unicode'])
def test_rejected_apply_keeps_invalid_draft_and_previous_applied_state(loaded, source):
    result = complete(loaded)
    loaded.set_draft(source)
    before = loaded.state
    with pytest.raises(SourceValidationError):
        loaded.apply_changes()
    assert loaded.state == before
    assert loaded.state.applied_source == SOURCE
    assert loaded.state.revision == 1
    assert loaded.state.results == (result,)
    assert loaded.state.draft == source
    loaded.set_draft('D0Eint(2)')
    loaded.apply_changes()
    assert loaded.state.revision == 2


@pytest.mark.parametrize('source', INVALID_SOURCES, ids=['empty', 'whitespace', 'oversized', 'invalid-unicode'])
def test_rejected_replacement_retains_text_for_correction(loaded, source):
    result = complete(loaded)
    with pytest.raises(SourceValidationError):
        loaded.load_source(source, 'rejected.txt')
    assert loaded.state.applied_source == SOURCE
    assert loaded.state.source_name == 'example.txt'
    assert loaded.state.revision == 1
    assert loaded.state.results == (result,)
    assert loaded.state.artifact is None
    assert loaded.state.draft == source
    assert loaded.state.draft_name == 'rejected.txt'
    loaded.set_draft('D0Eint(2)')
    loaded.apply_changes()
    assert loaded.state.source_name == 'rejected.txt'
    assert loaded.state.revision == 2


@pytest.mark.parametrize('source', ['', ' ', 'x' * (MAX_SOURCE_BYTES + 1)], ids=['empty', 'whitespace', 'oversized'])
def test_rejected_initial_apply_keeps_no_applied_source(model, source):
    model.set_draft(source)
    with pytest.raises(SourceValidationError):
        model.apply_changes()
    assert model.state.applied_source is None
    assert model.state.revision == 0
    assert model.state.draft == source


@pytest.mark.parametrize('name', ['', ' ', None])
def test_invalid_source_name_does_not_change_state(loaded, name):
    before = loaded.state
    with pytest.raises(SourceValidationError):
        loaded.load_source('D0Eint(2)', name)
    assert loaded.state == before


@pytest.mark.parametrize('source', [None, b'D0Eint(2)', 2])
def test_nontext_draft_or_replacement_does_not_change_state(loaded, source):
    before = loaded.state
    with pytest.raises(SourceValidationError):
        loaded.set_draft(source)
    with pytest.raises(SourceValidationError):
        loaded.load_source(source, 'invalid.txt')
    assert loaded.state == before


def test_size_limit_counts_utf8_bytes(model):
    source = 'x' * MAX_SOURCE_BYTES
    model.load_source(source, 'max.txt')
    assert model.state.applied_source == source
    model.set_draft('\u00e9' * (MAX_SOURCE_BYTES // 2 + 1))
    with pytest.raises(SourceValidationError, match='65536-byte'):
        model.apply_changes()
    assert model.state.applied_source == source
    assert model.state.revision == 1


def test_model_accepts_malformed_constructor_input_without_parsing(model):
    model.set_draft('D0Eint(')
    model.apply_changes()
    assert model.state.applied_source == 'D0Eint('


@pytest.mark.parametrize('action', [
    lambda model: model.load_source('D0Eint(2)', 'new.txt'),
    lambda model: model.start_manual_input(),
    *[lambda model, operation=operation: model.begin_operation(operation) for operation in Operation],
])
def test_dirty_state_blocks_actions_and_replacement(loaded, action):
    loaded.set_draft('D0Eint(3)')
    before = loaded.state
    with pytest.raises(ModelStateError, match='Apply or discard'):
        action(loaded)
    assert loaded.state == before


@pytest.mark.parametrize('operation', list(Operation))
def test_operations_require_applied_source(model, operation):
    assert not model.state.can_run(operation)
    with pytest.raises(ModelStateError, match='Apply or load source'):
        model.begin_operation(operation)


@pytest.mark.parametrize('operation', [Operation.LINT, Operation.INTERPRET, Operation.TYPECHECK, Operation.COMPILE])
def test_operation_request_captures_applied_source_and_revision(loaded, operation):
    assert loaded.state.can_run(operation)
    request = loaded.begin_operation(operation)
    assert request.operation is operation
    assert request.source == SOURCE
    assert request.source_revision == 1
    assert loaded.state.busy
    assert loaded.state.active_operation is operation
    assert not loaded.state.can_run(operation)


def test_execute_remains_unavailable(loaded):
    assert loaded.state.artifact is None
    assert not loaded.state.can_run(Operation.EXECUTE)
    before = loaded.state
    with pytest.raises(ModelStateError, match='no generated code'):
        loaded.begin_operation(Operation.EXECUTE)
    assert loaded.state == before


@pytest.mark.parametrize('action', [
    lambda model: model.set_draft('D0Eint(2)'),
    lambda model: model.apply_changes(),
    lambda model: model.discard_changes(),
    lambda model: model.load_source('D0Eint(2)', 'new.txt'),
    lambda model: model.start_manual_input(),
    *[lambda model, operation=operation: model.begin_operation(operation) for operation in Operation],
])
def test_busy_state_blocks_conflicting_changes_and_actions(loaded, action):
    loaded.begin_operation(Operation.INTERPRET)
    before = loaded.state
    with pytest.raises(ModelStateError, match='in progress'):
        action(loaded)
    assert loaded.state == before


@pytest.mark.parametrize('outcome', list(Outcome))
def test_operation_completion_records_result_and_preserves_source(loaded, outcome):
    result = complete(loaded, Operation.INTERPRET, outcome)
    assert loaded.state.results == (result,)
    assert loaded.state.applied_source == SOURCE
    assert loaded.state.revision == 1
    assert not loaded.state.busy
    assert loaded.state.can_run(Operation.INTERPRET)


def test_results_accumulate_for_current_revision_only(loaded):
    first = complete(loaded)
    second = complete(loaded, Operation.INTERPRET)
    assert loaded.state.results == (first, second)
    loaded.load_source(SOURCE, 'new.txt')
    assert loaded.state.results == ()


@pytest.mark.parametrize('result', [
    OperationResult(Operation.LINT, 0, Outcome.SUCCESS, 'stale'),
    OperationResult(Operation.INTERPRET, 1, Outcome.SUCCESS, 'wrong operation'),
    OperationResult(Operation.LINT, 1, Outcome.SUCCESS, 'unsupported artifact', artifact=GeneratedArtifact(1, 'code', 'format')),
    None,
])
def test_invalid_completion_cannot_change_state_and_can_be_aborted(loaded, result):
    request = loaded.begin_operation(Operation.LINT)
    before = loaded.state
    with pytest.raises(ModelStateError):
        loaded.finish_operation(request, result)
    assert loaded.state == before
    loaded.abort_operation(request)
    assert not loaded.state.busy
    assert loaded.state.applied_source == SOURCE
    complete(loaded)
    assert len(loaded.state.results) == 1


def test_completion_without_active_work_is_rejected(loaded):
    with pytest.raises(ModelStateError, match='No operation'):
        loaded.finish_operation(None, OperationResult(Operation.LINT, 1, Outcome.SUCCESS, 'unexpected'))
    assert loaded.state.results == ()


def test_cleanup_after_failure_is_idempotent_and_allows_retry(loaded):
    before = loaded.state
    request = loaded.begin_operation(Operation.INTERPRET)
    loaded.abort_operation(request)
    loaded.abort_operation(request)
    assert loaded.state == before
    complete(loaded, Operation.INTERPRET)
    assert not loaded.state.busy


def test_unknown_operation_does_not_set_busy(loaded):
    with pytest.raises(ModelStateError, match='Unknown operation'):
        loaded.begin_operation('unknown')
    assert not loaded.state.busy


def test_concurrent_starts_allow_only_one_operation(loaded):
    barrier = Barrier(2)
    def start():
        barrier.wait(timeout=5)
        try:
            return loaded.begin_operation(Operation.INTERPRET)
        except ModelStateError:
            return None
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: start(), range(2)))
    assert sum(result is not None for result in results) == 1
    assert loaded.state.busy
    loaded.abort_operation(next(result for result in results if result is not None))


def test_old_cleanup_cannot_clear_new_request_busy_state(loaded):
    first = loaded.begin_operation(Operation.INTERPRET)
    result = OperationResult(Operation.INTERPRET, 1, Outcome.SUCCESS, 'first')
    loaded.finish_operation(first, result)
    second = loaded.begin_operation(Operation.INTERPRET)
    loaded.abort_operation(first)
    assert loaded.state.busy
    loaded.finish_operation(second, replace(result, output='second'))
    assert len(loaded.state.results) == 2


def test_aborted_request_cannot_complete_new_work_at_same_revision(loaded):
    first = loaded.begin_operation(Operation.LINT)
    loaded.abort_operation(first)
    second = loaded.begin_operation(Operation.LINT)
    result = OperationResult(Operation.LINT, 1, Outcome.SUCCESS, 'late result')
    before = loaded.state
    with pytest.raises(ModelStateError, match='active request'):
        loaded.finish_operation(first, result)
    assert loaded.state == before
    loaded.abort_operation(first)
    assert loaded.state.busy
    loaded.finish_operation(second, result)
    assert not loaded.state.busy
