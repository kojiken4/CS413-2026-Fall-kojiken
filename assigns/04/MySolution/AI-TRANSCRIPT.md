# AI assistance record

## Tools and scope

OpenAI Codex assisted with architecture, implementation, and documentation, while acknowledging what parts need additional manual
verification. This record summarizes important requests, suggestions, and review.

The implementation stays within [Assign04.md](../Assign04.md): a local MVC
front-end using the unchanged supplied interpreter, real Lint/Interpret,
Type-check/Compile placeholders, and unavailable generated-code execution.

## Important requests

- Review the assignment and explain its requirements.
- Keep implementation within the specification and explain the purpose of changes.
- Clarify the model's state ownership and the backend's language-tool role to acknowledge the distinction between two backend
  services operating under this application's MVC architecture.

## Suggestions adopted

| Area | AI suggestion and implementation |
| --- | --- |
| Architecture | FastAPI with plain HTML/CSS/JavaScript; controller-coordinated tools; framework-independent model |
| Input | Explicit constructor/field allowlist and restricted AST traversal rather than Python execution |
| Language tools | Real supplied free-variable analysis/evaluation behind a replaceable protocol; explicit placeholders |
| State | Immutable snapshots and locked transitions; source revisions; draft and busy guards |
| Recovery | Completion/cleanup tied to the original request to prevent stale work affecting newer operations |
| Execution bounds | Fixed trusted subprocess worker, validated JSON transport, five-second timeout |
| Controller | Injected model/backend, strict uploads, asynchronous waiting and failure results |
| View | Serialized draft requests, preserved newer typing, literal text rendering, labeled controls |
| Verification | Direct model tests, substituted controller backend, real-tool tests, browser checks, fresh checkout |

No uploaded Python or shell code is executed. No type checker, compiler, mock
compiler fixture system, or generated-code executor was added.

## Review and corrections

Generated output was reviewed against the assignment with manual review and oversight.
I analyzed the functional requirements, scope of the task, supplied dataclasses and
tool interfaces, actual state transitions, and tests. The supplied interpreter
was compared byte-for-byte with its source.

| Finding | Correction and verification |
| --- | --- |
| Runtime use of a language type alias | Use the concrete `D0V000` class; detect exact sentinels separately because successful values inherit from it |
| Stale-operation cleanup race | Require original request ownership; regression tests reject stale completion/cleanup |
| Test fixture escaping/encoding errors | Correct newline fixtures and use escaped JSON for lone surrogates so requests reach the application |
| Browser diagnostic/delay/deadline expectations | Match actual messages, delay responses correctly, and allow time beyond the worker deadline |
| Compiler extension description | State that future compilation needs model/controller artifact support as well as backend methods |

Tests exercise real lexical scope, arithmetic, factorial/Fibonacci and base
cases, input/runtime errors, pair sentinels, state guards, timeout cleanup, and
retry. Failure injection verifies dispatch/recovery and literal multiline output;
it does not substitute for real language tools. Browser checks also verify
rapid typing, network-error preservation, keyboard activation, and disabled Execute.

## Documentation consulted

- [Python AST](https://docs.python.org/3.13/library/ast.html): restricted constructor reading.
- [Python subprocess](https://docs.python.org/3.13/library/subprocess.html):
  timeout and child-process cleanup.
- [Python asyncio tasks](https://docs.python.org/3.13/library/asyncio-task.html):
  thread waiting and cancellation.
- [Python venv](https://docs.python.org/3.13/library/venv.html): environment paths.
- [MDN Response.ok](https://developer.mozilla.org/en-US/docs/Web/API/Response/ok)
  and [Node.textContent](https://developer.mozilla.org/en-US/docs/Web/API/Node/textContent):
  request errors and literal rendering.
- [Playwright browsers](https://playwright.dev/python/docs/browsers):
  browser installation and installed-Edge testing.

## Verification evidence and limits

A fresh local checkout of commit `669b4d4` on Windows/Python 3.13.14 installed
the documented dependencies and passed **364 default tests**, with seven opt-in
browser tests skipped. All **seven browser tests passed** separately with freshly
installed Chromium 140.0.7339.16. An additional browser run passed on Edge
154.0.4258.53. Desktop/narrow-screen rendering was visually inspected.

An existing server on port 8000 was preserved; independent startup, static assets,
and real interpretation were verified on port 8001. Documentation links, fenced
blocks, the 249-word reflection, interpreter bytes, and tracked submission files
were checked. Verification servers and browsers were stopped.

[TESTING.md](TESTING.md) records observed results and requirement mappings.
The Starlette/HTTPX warning remains documented. macOS commands were reviewed,
not executed on a Mac; manual screen-reader use is also unverified.
