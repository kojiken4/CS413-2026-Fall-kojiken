# AI assistance record

## Tools

OpenAI Codex assisted with planning and implementation. This record summarizes
important prompts and suggestions; it is not a verbatim conversation export.

## Important prompts and suggestions

- User: review `Assign04.md` and explain its requirements.
- User: develop incremental, separately committable steps, explain each step
  before implementation, and stay within the assignment specification.
- Implementation uses FastAPI with plain browser HTML/CSS/JavaScript.
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

## Step 7 review and validation

- User authorized Step 7 after reviewing the controller/model/backend relationship.
  Codex explained the interface scope before editing and kept language operations,
  model rules, and generated-code behavior unchanged.
- Added plain HTML/CSS/JavaScript controls for source selection, draft editing,
  Apply/Discard, ordered actions, textual status, and literal revision-associated
  results. FastAPI serves fixed static assets; the view performs no language analysis.
- Draft requests are serialized and newer typing is preserved over older responses.
  Apply waits for synchronization. Dirty/busy controls reflect state without
  replacing the server model's guards. Network failures retain local text.
- MDN guidance was checked for Fetch response handling and DOM text rendering:
  https://developer.mozilla.org/en-US/docs/Web/API/Response/ok and
  https://developer.mozilla.org/en-US/docs/Web/API/Node/textContent.
  Playwright's official Python browser documentation informed installed-Edge testing:
  https://playwright.dev/python/docs/browsers.
- Added pinned test-only Playwright and seven opt-in browser smoke tests using
  real local servers/tools. Injection is limited to network/delay and multiline
  rendering checks. Initial failures were corrected test expectations/timing,
  not substitutes for required language implementations.
- Default suite: 364 passed, 7 browser tests skipped. Separate browser suite:
  all 7 passed on Edge 154.0.4258.53. Desktop/narrow-screen rendering was visually
  inspected; dependency and JavaScript syntax checks passed. The supplied
  interpreter remains unchanged. Nothing was staged or committed.

## Step 8 documentation review

- User authorized final documentation (Step 8). Codex explained the scope and
  limited edits to README, ARCHITECTURE, TESTING, and this assistance record.
- README was condensed and completed with reproducible commands, verified
  dependency versions, the four required demonstrations, limitations, and a
  249-word MVC reflection. The reflection describes actual boundaries and
  synchronization difficulties; it does not claim future compiler support exists.
- Architecture was checked against implementation and shortened to approximately
  904 words excluding its diagram. Future compilation explicitly requires changing
  current artifact rejection and wiring Execute, not only replacing backend methods.
- Historical testing entries were distinguished from current evidence. Local
  links, fenced blocks, and reflection length were checked. Demonstration outcomes
  were verified against real bounded tools through controller requests. One
  temporary diagnostic assertion was corrected to match the supplied evaluator's
  actual ZeroDivisionError wording; no code changes were necessary.
- Clean-checkout verification remains for Step 9. No implementation extension,
  test changes, staging, or commits were performed.

## macOS instructions before Step 9

- User requested Macintosh equivalents for the documented commands.
- Added macOS Terminal setup/start, default test/dependency, and opt-in browser
  commands beside the PowerShell versions. Python's venv and Playwright browser
  documentation were consulted for paths and browser setup.
- Documentation explicitly states that the macOS commands were reviewed, not
  executed on a Mac. Application behavior and dependencies were unchanged;
  Step 9 was not started. Nothing was staged or committed.
