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
