# Assignment 09 verification

## Observed results

On November 25, 2026, verification used a clean copy of `MySolution/` outside
the repository and a new virtual environment. The environment was macOS
27.2.1 on arm64, Python 3.15.2, Flask 3.1.3, Werkzeug 3.1.9, Playwright 1.65.2,
and Chrome 158.0.8127.37.

| Check | Result |
| --- | --- |
| Install `requirements-dev.txt` and run `python -m pip check` | Dependencies installed successfully and `pip check` reported no broken requirements. |
| `python -B -m unittest discover -s tests -v` | 21 passed through Flask's HTTP test client. |
| `ASSIGN09_BROWSER_CHANNEL=chrome python -B -m unittest discover -s tests/browser -v` | 9 passed in headless Chrome. Collection run tests used the packaged Assign07 service in a separate loopback process. |
| CLI startup and storage restart | Both documented service commands started. The studio relayed `6 * 7` and received `42`. After restarting storage, both lists were empty, requests for old IDs returned `404`, and old cursors returned `400 invalid_request`. LAMBDA3 remained available through the restart. |
| OpenAPI validation | `openapi-spec-validator` accepted `openapi.json`. |

The browser integration run reported three passes and two intentional
failures. The formatted value, syntax error, and type error matched. A
trailing-space mismatch and an unexpected LAMBDA3 failure were reported as
failures, and the subsequent cases ran to completion.

The browser suite used installed Chrome on macOS. The Windows and Linux
setup variants and Playwright's bundled Chromium were outside this run.

## HTTP API coverage

Tests create their data through the public HTTP interface.
[Program tests](tests/test_program_api.py) · [Collection tests](tests/test_collection_api.py)

| Behavior | Test names |
| --- | --- |
| Health, routing, and required status codes, including doubled-slash paths | `test_health_missing_route_and_unsupported_method` |
| Content types, malformed JSON, declared-length and chunked body limits, and redacted server errors | `test_content_type_malformed_json_and_body_limit`<br>`test_internal_error_is_json_and_does_not_expose_details` |
| Program and collection CRUD, UTC timestamps, version fields, and metadata-only collection edits | `test_program_crud_preserves_source_and_sets_version_fields`<br>`test_collection_crud_includes_cases_and_updates_only_metadata` |
| Case add, edit, and delete preserve IDs and remaining order, with the parent ETag updated | `test_case_mutations_keep_ids_and_order_and_advance_the_parent_revision` |
| Missing, wrongly typed, blank, oversized, and unknown fields, including invalid expectations | `test_validation_rejects_invalid_fields_and_accepts_exact_field_limits`<br>`test_validation_rejects_invalid_collection_case_and_expectation_fields` |
| Trimmed, case-sensitive names and uniqueness scopes | `test_trimmed_name_conflicts_are_case_sensitive_and_leave_state_unchanged`<br>`test_trimmed_names_are_unique_only_inside_their_scope` |
| Missing IDs, malformed or missing preconditions, stale writes, and unchanged state on failure | `test_missing_malformed_and_stale_preconditions_leave_state_unchanged`<br>`test_conditional_failures_leave_the_collection_unchanged` |
| Cursor boundaries, replay, stable record contents, and resource binding | `test_page_validation_and_cursor_replay`<br>`test_snapshot_pages_keep_updated_and_deleted_representations`<br>`test_collection_cursor_retains_old_case_contents_and_excludes_new_records` |
| Page size, per-collection capacity, global capacity, and capacity recovery on deletion | `test_default_page_size_and_capacity_recovery`<br>`test_case_limit_and_capacity_recovery`<br>`test_global_capacity_counts_cases_and_collection_deletion_frees_them` |
| Exactly one same-revision write succeeds | `test_concurrent_updates_recheck_revision_at_write_time`<br>`test_concurrent_case_append_and_metadata_edit_share_the_parent_revision` |
| Collection deletion removes its cases and program deletion preserves case snapshots | `test_global_capacity_counts_cases_and_collection_deletion_frees_them`<br>`test_program_edits_and_deletion_leave_saved_case_source_unchanged` |

## Browser coverage

| Behavior | Test names |
| --- | --- |
| Save and reopen programs, preserve drafts, and reload after a conflict | `test_save_reopen_and_reload_after_a_conflict`<br>`test_validation_and_network_failure_preserve_the_draft` |
| List subsequent program pages and preserve saved source line endings | `test_list_follows_cursors_and_metadata_edits_preserve_stored_source` |
| Create, edit, delete, and reopen ordered cases | `test_create_edit_delete_and_reopen_ordered_cases` |
| Preserve case drafts after stale and rejected saves | `test_stale_case_save_preserves_draft_and_reloads_the_newer_case`<br>`test_rejected_case_save_preserves_input_without_changing_order` |
| Reload a program in a fresh browser context, create a collection, and run it against real LAMBDA3 | `test_program_reload_and_real_collection_run_continues_after_failures` |
| Keep the original source and case ID when the case changes during a run | `test_edit_during_run_keeps_original_case_source_and_id_on_result` |
| Treat transport failures as failed cases and continue execution | `test_transport_failure_is_not_an_expected_error_and_run_continues` |
