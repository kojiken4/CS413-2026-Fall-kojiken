# Assignment 07 testing

## Architecture

```text
Client
  |
  v
Flask HTTP transport (http.py)
  |
  v
JSON-RPC dispatcher (dispatcher.py)
  |
  v
LAMBDA3 service adapter (service.py)
  |                                  |
  | type-check and compile           | interpret with a 2-second deadline
  v                                  v
Provided LAMBDA3 module           Worker subprocess (worker.py)
                                     |
                                     v
                                  Provided LAMBDA3 module
```

The Flask route handles HTTP status and JSON decoding. The dispatcher handles
envelopes, IDs, batches, notifications, and errors. The adapter validates
language parameters and calls the supplied parser, checker, and compilers.
The worker uses the same parser and checker before evaluating and formatting
an interpretation result.

## Coverage

Tests below are in [tests/test_rpc.py](tests/test_rpc.py). Successful language
tests call the provided LAMBDA3 implementation. Test doubles are used at
dispatch and worker boundaries to observe notification dispatch and exercise
failure cases. The timeout test launches a real slow subprocess, verifies it
exited, and makes a successful follow-up request.

| Required behavior | Solution tests |
| --- | --- |
| Health returns the status, version, and request ID | `test_health_preserves_call_ids` |
| Type-checking returns formatted types | `test_typecheck_returns_formatted_types` |
| Interpretation returns formatted arithmetic, factorial, tuple, and collection results | `test_interpret_returns_formatted_values_and_types`, `test_interpret_factorial`, `test_interpret_uses_provided_list_library` |
| Both compilers return the requested target and exact generated source | `test_compile_returns_both_compilers_output_unchanged` |
| Syntax and type errors use distinct codes and safe diagnostics | `test_language_syntax_and_type_errors` |
| Malformed JSON, invalid envelopes, and unknown methods are classified separately | `test_malformed_json`, `test_invalid_envelope_gets_null_id`, `test_unknown_method_is_case_sensitive` |
| Invalid parameters, blank source, the UTF-8 size boundary, and unsupported media types | `test_invalid_health_params`, `test_source_parameter_validation_for_language_methods`, `test_source_limit_counts_utf8_bytes`, `test_compile_validates_target`, `test_unsupported_media_type_is_a_transport_error` |
| Function values use the formatter and program output stays out of the reply | `test_interpret_returns_formatted_values_and_types` |
| Failures and timeouts preserve IDs and keep internal diagnostics off the wire | `test_unexpected_failure_is_logged_and_redacted`, `test_interpret_worker_failure_is_logged_and_redacted`, `test_interpret_rejects_invalid_worker_reply`, `test_interpret_timeout_stops_worker_and_allows_next_request` |
| The checker rejects an unbound variable | `test_typecheck_rejects_unbound_variable` |
| Mixed and empty batches, invalid members, and empty notification responses | `test_mixed_batch_preserves_ids_and_omits_notifications`, `test_empty_batch_returns_one_error_object`, `test_notifications_are_dispatched_without_replies` |

## Observed results

Verified from `assigns/07/` on Windows PowerShell with a fresh virtual
environment using Python 3.14.7 and Flask 3.1.3.

| Check | Observed result |
| --- | --- |
| `python -B -m unittest discover -s MySolution/tests -v` | 23 passed |
| `python -B -m unittest discover -s TEST -v` with the documented Flask server running on `127.0.0.1:8000` | 15 passed |
| Draft 2020-12 schema validation during the contract milestone | 15 JSON examples and 10 edge cases passed |

All five [README curl demonstrations](README.md#try-the-rpc-methods) returned
HTTP `200` with the original request ID. Health returned `ok` and version
`1.0`. Type-checking returned `sint`, and factorial returned `sint` with
value `720`. Compilation returned nonempty JavaScript source. The
unbound-variable call returned RPC error `-32011` with
`unbound variable 'missing'`.
