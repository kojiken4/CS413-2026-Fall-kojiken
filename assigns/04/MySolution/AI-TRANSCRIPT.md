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
