# AI assistance transcript

## AI use and manual review

I used OpenAI Codex to review the assignment, plan the work, and help implement
and test the animated N-Queens solver. Before making each commit, I manually
reviewed and audited all changes for that milestone, including the source code,
tests, and documentation. I made the commits myself and told Codex when to move
on to the next step.

## Important prompts and suggestions

- I asked Codex to explain the assignment and divide the work into steps that I
  could review and commit separately.
- I asked it to stay within the assignment requirements, explain each step
  before implementing it, and suggest a commit message when it finished.
- Codex suggested releasing the solver state when a stream ends and keeping
  enough information to answer later requests for that stream.

## Implementation and testing

Codex helped with the LAMBDA3 search and lazy streams, the JSON-RPC service,
the browser animation, and the tests and documentation. During my review,
I checked the implementation against the assignment requirements, including
how the solver resumes its search and how the browser requests events.

The automated checks supported my manual review. They verified lazy stream
consumption, all 92 solutions, and browser playback and error handling.
See [TESTING.md](TESTING.md) for the test coverage and results.
