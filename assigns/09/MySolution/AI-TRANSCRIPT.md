# AI assistance transcript

## AI use and manual review

I used OpenAI Codex in the Codex desktop app to review the assignment, plan
the work, and help implement and test the in-memory storage service and
LAMBDA-studio integration. Before making each commit, I manually reviewed
and audited all changes for that milestone, including the source code,
tests, and documentation. I checked the changes against the assignment
requirements and confirmed they were ready before committing. I made the
commits myself and told Codex when to move on to the next step.

## Important prompts and suggestions

- I asked Codex to explain the assignment and divide the required work into
  steps that I could review and commit separately.
- I asked Codex to stay within the assignment scope, explain each step before
  implementing it, and pause with a suggested commit message so I could audit
  the changes.

## Implementation and testing

| Checkpoint | Significant assistance |
| --- | --- |
| API contract | Reviewed the assignment, proposed separately committable steps, and drafted the REST contract and OpenAPI description. |
| Programs | Implemented the Flask transport, input validation, in-memory program operations, conditional mutations, and cursor snapshots. Added HTTP tests. |
| Collections | Implemented collection CRUD and ordered case mutations. Added HTTP tests for expectation shapes, revision conflicts, capacity, and snapshots. |
| Program editor | Built the browser editor and storage adapter. Added browser tests for reopening, stale saves, and request failures. |
| Collection editor | Extended the adapter and UI for collection and case editing. Added browser tests for case order and draft recovery. |
| Collection runs | Packaged the existing Assign07 runtime, implemented the interpretation relay and result display, and added integration tests against real LAMBDA3. |
| Final verification | Prepared the submission documentation and checked setup, tests, and data clearing from a standalone copy. |

My review covered the REST contract and schemas, the in-memory storage
behavior, the revision checks and cursor snapshots, and the studio
workflows. I checked that the studio ran saved cases through the separate
LAMBDA3 service and that results stayed tied to the case ID and source
snapshot used for the run.

The automated checks supported my manual review. All 21 API tests and 9
browser tests passed in a standalone copy. The restart check confirmed that
saved records were cleared and cursor tokens became invalid. See
[TESTING.md](TESTING.md) for the test coverage and observed results.
