# Assignment 08 testing

Run the commands in [README.md](README.md#tests) from `assigns/08/`.
Successful solver and HTTP tests exercise the supplied LAMBDA3 interpreter.
The tests also observe the interpreter's candidate checks and cell creation,
inject a clock for expiry, and inject a mid-batch failure to check that a
retry starts at the same cursor.

## Requirements and tests

| Requirement | Tests |
| --- | --- |
| Safety, same-row invariant, and both diagonal directions | `test_safety_continuations`, `test_event_coordinates_and_snapshots`. Search only tries the next unused row. The safety checker rejects same-column and diagonal collisions. |
| CPS success, failure, and resumption | `test_safety_continuations`, `test_solution_tail_backtracks_and_resumes_at_next_column` |
| Exactly 92 distinct 8×8 boards in deterministic order | `test_all_92_solutions_in_deterministic_order` compares the sequence with an independent permutation-based oracle. |
| All event types, coordinates, and board snapshots | `test_event_coordinates_and_snapshots` |
| Unforced open and tail, including bounded reads on larger boards | `test_open_and_bounded_forcing_do_no_extra_work` observes zero work on open and one constructed cell per delivered event on 9×9 and 10×10. |
| Close, expiry, cleanup, exhaustion, and repeated reads | `test_close_and_unknown_streams`, `test_completed_record_expires_after_its_last_read`, `test_successful_read_refreshes_deadline_and_operations_sweep`, `test_completion_releases_cursor_without_forcing_done_tail` |
| IDs, malformed requests, unknown methods, invalid parameters, notifications, and errors | `test_health_and_request_ids_including_explicit_null`, `test_parse_errors_and_wrong_content_type`, `test_invalid_envelopes_and_batch_arrays`, `test_unknown_methods_including_assign07_methods`, `test_invalid_params_do_not_consume_a_stream`, `test_notifications_dispatch_without_a_body`, `test_missing_closed_and_expired_ids_share_application_error`, `test_unexpected_solver_error_is_sanitized_and_cursor_is_retryable` |
| Limits of 1 and 32, independent cursors, atomic reads, and retry | `test_open_and_read_limits_leave_each_stream_independent`, `test_overlapping_reads_return_disjoint_consecutive_batches`, `test_failed_batch_leaves_cursor_and_deadline_for_retry` |
| Full 8×8 flow over HTTP through completion and close | `test_live_http_consumes_all_92_solutions_and_done` |
| Browser controls, rendering, pause and reset races, and error recovery | [Browser scenarios](tests/browser/client.test.js) include `Start, step, render snapshots, and reset`, `Play requests one event at a time and pause keeps an in-flight event`, `Next solution stops inside a batch, preserves later events, and allows restart`, `Reset closes a late open and ignores an earlier next response`, and `RPC and network failures are visible and reset restores controls`. |

## Observed results

Verified on macOS with Python 3.15.2, Flask 3.1.3, and Chrome.

| Check | Observed result |
| --- | --- |
| Assignment Python suite | 23 passed. The live HTTP test received 92 distinct solutions, one final `done`, and an empty follow-up read. |
| Supplied LAMBDA3 library suite | 26 passed. |
| Browser scenarios | 5 passed. |
| README setup, launch, and RPC examples | A fresh virtual environment installed the declared dependency. Both documented servers started, and all four curl requests returned their expected results. |
| Live Chrome run against Flask | Step and Play updated the board, Pause stopped playback, Next solution reached all 92 solutions, and completion allowed a fresh run. Both a closed stream and a stopped server produced visible errors. Reset and Start recovered once the service was available. |

## Live browser checklist

1. Start the local server and open the application. Confirm the board is
   empty, the count is zero, and only Start can begin a search.
2. Start, then Step. Confirm the first candidate is row 0, column 0. Step
   again and confirm the queen is placed. Change the speed, Play, then Pause
   and check that the board stops changing.
3. Click Next solution. Confirm eight queens are highlighted and the count
   increases by one. Reset and confirm the board and count clear.
4. To check completion in the browser, start and use Next solution through
   all 92 solutions. The following click should show `Search complete`.
   Start again and confirm a fresh empty board and count of zero.
5. To check live network failure, open a search, stop the server, then click
   Step. Confirm the error is visible and Reset is available. Restart the
   server, then use Reset and Start to open a fresh stream. The automated
   browser scenarios also inject both a network error and an RPC error.
