# Assign08 design

## Architecture

```text
Browser (RPC client + playback + board renderer)
  | POST /rpc with JSON-RPC 2.0
  v
HTTP endpoint -> RPC dispatcher -> Queens handlers -> Stream table
                                                          |
                                          open a cursor / force one cell
                                                          v
                                                  LAMBDA3 adapter
                                                    /           \
                                             CPS solver ---> Lazy event stream
```

The HTTP layer parses JSON and maps dispatcher results to status codes. The
dispatcher validates envelopes and routes the four fixed methods. The stream
table owns cursors and their lifetimes. The adapter loads and type-checks the
fixed LAMBDA3 solver and converts one stream cell at a time to plain event data.
The browser consumes that data through RPC. The solver has no dependency on
HTTP or browser code.

## Search and continuations

The search state contains the board size, the next row, the column being tried,
and an immutable partial board. Rows and columns start at zero. At row `r`,
the board contains exactly `r` columns for rows `0` through `r - 1`. Each
column is in bounds, and for any two entries `i < j`, the columns differ and
their absolute difference differs from `j - i`. The one-queen-per-row property
follows from extending the board only at its next row. The LAMBDA3 list stores
the most recent queen first so it can add a queen at the head and check earlier
queens in order of distance. Event boards expose the columns in row order.

| Continuation | Signature | Role |
| --- | --- | --- |
| `on_solution` | `(Board, unit -> Strm[Event]) -> Strm[Event]` | Emit the solution and suspend the supplied search continuation. |
| `on_exhausted` | `unit -> Strm[Event]` | Leave the current branch, or emit `done` at the root. |
| `on_safe` | `unit -> Strm[Event]` | Extend the board and emit `place`. |
| `on_conflict` | `unit -> Strm[Event]` | Emit `reject` and suspend the next column attempt. |

```text
search(row, board, on_solution, on_exhausted):
    if row == size:
        return on_solution(board, on_exhausted)
    return try_column(row, 0, board, on_solution, on_exhausted)

try_column(row, col, board, on_solution, on_exhausted):
    if col == size:
        return on_exhausted()

    next_column() = try_column(row, col + 1, board, on_solution, on_exhausted)
    leave_branch() = emit(backtrack(row, col, board), next_column)

    on_safe():
        extended = extend(board, col)
        return emit(place(row, col, extended),
                    () => search(row + 1, extended, on_solution, leave_branch))

    on_conflict() = emit(reject(row, col, board), next_column)
    return emit(try(row, col, board),
                () => check_safe(col, 1, board, on_safe, on_conflict))

check_safe(col, distance, previous, on_safe, on_conflict):
    if previous is empty:
        return on_safe()
    if head(previous) == col or abs(head(previous) - col) == distance:
        return on_conflict()
    return check_safe(col, distance + 1, tail(previous), on_safe, on_conflict)

on_solution(board, resume) = emit(solution(board), resume)
root_exhausted() = emit(done, empty_stream)
open(size) = suspend(() => search(0, empty_board, on_solution, root_exhausted))
```

Each continuation call is the final action of its search or safety helper.
After a placement the solver descends into the next row before trying a
sibling column. Both row exhaustion and resumption after a solution use the
captured branch continuation. It restores the parent snapshot, emits
`backtrack`, and defers the next sibling attempt. Each complete board has
one path through this tree. The ordering yields 92 distinct boards for 8×8.

In `queens.lam`, one recursive `try_column` function handles both row entry
at column zero and subsequent candidates. The supplied `eight_queens_stream.lam`
illustrates the newest-first list and delayed stream primitives used here.
The event search defines its own CPS safety and branch continuations. The
Python adapter follows Assign07's interpreter import pattern to resolve the
supplied `basics0` sibling module.

## Lazy cells and event schema

`Strm[Event]` is `Lazy[Stcn[Event]]` in LAMBDA3. The adapter opens a stream by
creating the suspended root. `suspend(thunk)` creates a lazy cell whose force
calls `thunk` and forwards the first cell of the returned stream. `emit(event,
resume)` creates a lazy cell containing `event` with `suspend(resume)` as its
tail. Both use the supplied lazy primitives. The tail closure is stored when
the current cell is produced and invoked when that tail is forced.

Forcing the root produces the first `try` event. Forcing its tail performs
the safety check and yields `place` or `reject`. After a `solution`, forcing
the tail resumes the saved branch. Forcing the tail after `done` would yield
an empty stream. The RPC layer stops on `done` and releases that tail without
forcing it. Tests will observe candidate checks and stream-cell creation in
the interpreter, including zero work at open and unforced tails after bounded
reads on 9×9 and 10×10.

| `event` | Other JSON fields | Board snapshot |
| --- | --- | --- |
| `try` | `row`, `column`, `board` | Partial board before checking the candidate. |
| `place` | `row`, `column`, `board` | Partial board with the candidate added at `row`. |
| `reject` | `row`, `column`, `board` | Partial board before the conflicting candidate. |
| `backtrack` | `row`, `column`, `board` | Parent board after removing the placement at `row`. |
| `solution` | `board` | Complete board with one column per row. |
| `done` | None | No board field. The renderer can keep the last snapshot. |

Coordinates are integers. The `board` array has one integer per occupied row,
in order from row zero. A complete board is an eight-element tuple for an 8×8
run in Python and an eight-element array on the wire.

## RPC contract and lifecycle

Use `POST /rpc` with `Content-Type: application/json`. Each pair below shows
the request followed by its HTTP 200 response. The last three examples refer
to the same stream.

**`service.health`**

```jsonl
{"jsonrpc":"2.0","method":"service.health","params":{},"id":1}
{"jsonrpc":"2.0","id":1,"result":{"status":"ok","version":"1.0"}}
```

**`queens.open`**

```jsonl
{"jsonrpc":"2.0","method":"queens.open","params":{"size":8},"id":2}
{"jsonrpc":"2.0","id":2,"result":{"stream_id":"d87bd18c-8e81-4692-88f4-b43990e8c34b","size":8}}
```

**`queens.next`**

```jsonl
{"jsonrpc":"2.0","method":"queens.next","params":{"stream_id":"d87bd18c-8e81-4692-88f4-b43990e8c34b","limit":1},"id":3}
{"jsonrpc":"2.0","id":3,"result":{"events":[{"event":"try","row":0,"column":0,"board":[]}],"done":false}}
```

**`queens.close`**

```jsonl
{"jsonrpc":"2.0","method":"queens.close","params":{"stream_id":"d87bd18c-8e81-4692-88f4-b43990e8c34b"},"id":4}
{"jsonrpc":"2.0","id":4,"result":{"closed":true}}
```

- Validate method parameters before allocating or advancing a stream. Use
  parameter objects with the fields in the examples. Omitted `params` counts
  as an empty object. Board sizes are integers from 4 through 10, limits are
  integers from 1 through 32, and stream IDs are nonempty strings. JSON
  Booleans and floating-point values are invalid for size and limit.
- `open` allocates a fresh UUID and an unforced root cursor. `next` forces
  at most `limit` cells, stops at `done`, and publishes the advanced cursor
  only after assembling the response data. A lock covers lookup, advancement,
  and publication so overlapping reads cannot consume the same events and
  close cannot interleave with a read. A failed read leaves the published
  cursor unchanged.
- The batch containing `done` has `done: true` and may be shorter than
  `limit`. At that point the table discards the solver cursor and retains the
  ID and its expiry information. A later `next` on that ID returns
  `{"events":[],"done":true}`. `close` deletes an active or completed record.
- Active and completed records expire after five minutes of inactivity.
  Successful `next` calls refresh the deadline. The service checks and sweeps
  expired records during stream operations using a monotonic clock. State is
  process-local and a restart invalidates all IDs.
- A valid notification has no `id`. The server dispatches it and returns
  HTTP 204 with an empty body. Calls preserve their request IDs, including an
  explicit `null`. A parse error or invalid envelope uses `id: null`. Batch
  arrays receive an invalid-request error. Other media types receive HTTP 415.

| Error | Code |
| --- | --- |
| Parse error | `-32700` |
| Invalid request | `-32600` |
| Method not found | `-32601` |
| Invalid parameters | `-32602` |
| Internal error | `-32603` |
| Unknown, closed, or expired stream ID (`Stream not found`) | `-32004` |

Internal errors return a generic message. The response contains only the
documented result data or error fields.

## Browser playback

Start opens a stream for size 8 and shows an empty board ready for Step or
Play. Step consumes one event. Play schedules one `next` request at a time
with `limit: 1` at the selected speed. Pause stops scheduling requests. If a
request was already in flight, the client holds its event for the next Step or
Play so the renderer stays paused. Next solution advances incrementally until
the next `solution` or `done` event. The renderer uses the event snapshot and
highlights the candidate, placement, rejection, removal, or full solution as
appropriate. It increments the solution count only on `solution` and marks
search completion on `done`.

Reset stops playback, clears the board and count, and closes the current
stream. The client associates each request with a local run token so an
earlier request cannot change the restarted board. If an earlier `open`
returns after Reset, the client closes the stream from that response. Start
can open a fresh run after completion. A network or RPC failure stops
playback, shows an error, and leaves Reset available for recovery.
