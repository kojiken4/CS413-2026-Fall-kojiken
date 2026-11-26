# AI assistance

**Tool** OpenAI Codex in the Codex desktop app. Codex used workspace tools to
inspect and edit the repository and ran verification through Python unittest,
Flask, and Playwright.

| Checkpoint | Significant assistance |
| --- | --- |
| API contract | Reviewed the assignment, proposed separately committable steps, and drafted the REST contract and OpenAPI description. |
| Programs | Implemented the Flask transport, input validation, in-memory program operations, conditional mutations, and cursor snapshots. Added HTTP tests. |
| Collections | Implemented collection CRUD and ordered case mutations. Added HTTP tests for expectation shapes, revision conflicts, capacity, and snapshots. |
| Program editor | Built the browser editor and storage adapter. Added browser tests for reopening, stale saves, and request failures. |
| Collection editor | Extended the adapter and UI for collection and case editing. Added browser tests for case order and draft recovery. |
| Collection runs | Packaged the existing Assign07 runtime, implemented the interpretation relay and result display, and added integration tests against real LAMBDA3. |
| Final verification | Prepared the submission documentation and checked setup, tests, and data clearing from a standalone copy. |

## Review process

I directed the work one checkpoint at a time and kept each implementation
step separate in Git. Codex described the scope before each step, reported
what it verified, and left the changes uncommitted with a suggested commit
message. The repository history records the first six checkpoints.

Verification compared the route table and schemas with the assignment,
exercised the service through its public HTTP interface, and tested the
browser workflows against local services. The integration tests checked
LAMBDA3 outcomes and verified that edits made during a run did not change
the displayed result's source. [TESTING.md](TESTING.md) records the final
checks and their observed results.
