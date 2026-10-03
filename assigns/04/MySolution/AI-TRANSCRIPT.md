# AI assistance record

## Tools

OpenAI Codex assisted with planning and implementation. This record summarizes
important prompts and suggestions; it is not a verbatim conversation export.

## Important prompts and suggestions

- User: review `Assign04.md` and explain its requirements.
- User: develop incremental, separately committable steps, explain each step
  before implementation, and stay within the assignment specification.
- User selected FastAPI for the web framework.
- User: implement one step, do not commit, and wait for permission to continue.
- Codex proposed controller-coordinated MVC, a restricted constructor reader,
  the supplied interpreter unchanged, and bounded backend execution.

## Step 1 review and validation

Implementation is limited to component boundaries, a landing route, dependency
setup, initial documentation, and foundation tests. No language processing or
source-editing features are claimed at this stage. Review included rereading
the assignment, checking the initial working tree and Python availability,
and checking the supplied interpreter interface.

Verification completed: interpreter SHA256 hashes match; all three foundation
tests passed; dependency consistency passed; and an actual loopback-server
request returned HTTP 200 with the expected page. The temporary verification
server was stopped. One test-client dependency deprecation warning is recorded
in `TESTING.md`. Dependencies and caches are excluded with a local `.gitignore`. User review and
commit selection remain separate from automated checks. No commit was made.

## Step 2 review and validation

- User: proceed to Step 2; prior instruction remains to explain scope and stop
  after each step without committing.
- Codex implemented an explicit constructor/field whitelist and AST traversal,
  rather than executing uploaded Python. Constructor definitions were checked
  against the unchanged supplied dataclasses, and Python's official AST
  documentation was consulted: https://docs.python.org/3.13/library/ast.html.
- Reader tests cover valid constructors and argument/encoding/size failures,
  rejected Python syntax, and absence of execution or interpretation side effects.
- The first test run caught a newline-escaping mistake in a test fixture; it was
  corrected. A test invocation used the wrong working directory; rerunning the
  documented command from `MySolution` resolved collection errors.
- The full suite passed 129 tests with the previously recorded dependency warning.
  The backend operations, model, HTTP actions, and view controls were not extended.
  User review and commit selection are still pending; no commit was made.

## Step 3 review and validation

- User authorized the next step after discussing the adapter's role in connecting
  `lambda1.py` functionality to application tools.
- Codex implemented real Lint/Interpret, neutral shared contracts, explicit
  Type-check/Compile placeholders, unavailable Execute, and five sample inputs.
  The supplied interpreter and reader were not modified.
- Shared types are separate from the concrete adapter so model/controller code
  can use the contract without importing interpreter implementation details.
- Tests exercise real lexical scope, arithmetic, factorial/Fibonacci and base
  cases, input/runtime errors, pair sentinels, and successful closure values.
  Injected backend failures verify failure classification and successful retry.
- The first run found misuse of the `d0val` type alias with `isinstance`; it was
  corrected to the concrete `D0V000` base class. Exact sentinel detection remains
  separate because all successful interpreter values inherit from that class.
- Final full suite: 199 passed, with the existing dependency warning. Interpreter
  SHA256 matches the supplied file. Timeout, MVC state, and HTTP/browser integration
  are left for their planned steps. Nothing was staged or committed.

## Step 4 review and validation

- User requested an explanation of model ownership versus language-tool logic,
  then explicitly authorized Step 4.
- Codex implemented immutable state snapshots and locked transitions for source,
  drafts, revisions, results, and busy state. The controller will coordinate tools;
  the model does not invoke them. Shared transport validation was extracted so
  the model does not import language code, preserving the reader's existing API.
- Review identified a stale-cleanup race. Operation completion and cleanup now
  require the original request object, preventing old work from affecting a newer
  request at the same source revision. Regression tests cover both cases.
- Tests verify isolated model imports, rejected edits/replacements, dirty/busy
  guards, revision invalidation, result association, failure recovery, and atomic
  concurrent starts. Oversized test identifiers were shortened after setup errors.
- Final verification: 276 tests passed with the existing dependency warning.
  No compiler or generated artifact extension was added. Browser/controller
  integration and timeouts remain pending. Nothing was staged or committed.

## Step 5 review and validation

- User explicitly authorized bounded language execution (Step 5).
- Codex added a fixed subprocess worker and JSON transport around the existing
  language adapter. Source remains data; no shell is invoked. Type-check/Compile
  and Execute behavior are inherited unchanged.
- Python's official documentation was checked for `subprocess.run` timeout cleanup
  and `asyncio.to_thread` waiting:
  https://docs.python.org/3.13/library/subprocess.html and
  https://docs.python.org/3.13/library/asyncio-task.html.
- Real tests cover worker language results, a slow-program timeout, a nonterminating
  expression that reaches the recursion limit, event-loop responsiveness, preserved
  model state, successful retry, and reaped workers/closed pipes. Failures are injected
  only for crash/transport/error recovery checks, not to replace real language tools.
- Final suite: 319 tests passed with the existing dependency warning. HTTP integration
  and browser checks remain pending. No staging or commits were performed.

## Step 6 review and validation

- User authorized HTTP controller integration, paused work, and then explicitly
  resumed Step 6 with a request to explain its status and remaining scope first.
- Codex connected an injected model/backend to source, state, and action routes.
  The default backend is bounded; uploaded bytes are decoded strictly as UTF-8
  with the existing size limit. No browser controls or new language tools were added.
- Tests cover real tools through HTTP, substituted backend dispatch, independent
  state, input/conflict guards, revision invalidation, malformed backend responses,
  cancellation, upload races, and retry. Controller work uses a thread and a
  shielded task; cleanup waits for actual completion, not just the HTTP request.
- The paused run had 363 passes and a fixture failure before invalid Unicode
  reached the application. The resumed implementation uses escaped JSON for that
  fixture. Shutdown cleanup also runs through a `finally` block.
- Final suite: 364 passed with the existing dependency warning. A real loopback
  server verified source/action workflows, responsive busy-state requests, the
  five-second timeout, source preservation, and successful retry; it was stopped
  afterward. Browser checks remain for Step 7. Nothing was staged or committed.
