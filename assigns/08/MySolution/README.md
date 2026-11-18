# Assignment 08 · Animated N-Queens search

The browser animates an 8×8 search one event at a time. The fixed LAMBDA3
solver uses continuation-passing style to produce a lazy stream of attempts,
placements, rejections, backtracks, and solutions. The Python service advances
each stream through JSON-RPC. A complete 8×8 run yields 92 distinct solutions.

## Setup and run

Use Python 3.12 or later, a modern browser, and curl for the RPC examples.
Flask 3.1 is the only direct Python dependency. Run the commands from
`assigns/08/`. In Bash or Zsh, create a virtual environment in a temporary
directory outside the submission.

```sh
assign08_env=$(mktemp -d)
python3 -m venv "$assign08_env"
source "$assign08_env/bin/activate"
python -m pip install -r MySolution/requirements.txt
```

Start the local server in that environment.

```sh
python -B -m flask --app MySolution.http:create_app run --host 127.0.0.1 --port 8000
```

Open [the N-Queens board](http://127.0.0.1:8000/) while the server is running.

## Controls

| Control | Behavior |
| --- | --- |
| Start | Open a fresh 8×8 stream and leave it ready for playback. Use it again after completion to restart. |
| Step | Display one event. |
| Play / Pause | Advance one event at a time at the selected playback speed, or pause. |
| Next solution | Advance until the next solution or search completion. Fetch at most 32 events per request and retain any unused events for subsequent playback. |
| Reset | Stop playback, close the current stream, and clear the board and solution count. |

Board coordinates are zero-based. The status describes the current event and
shows why a candidate was rejected. `Solution found` shows a complete board.
`Search complete` means the stream reached its final event. For a service
error during playback, Reset and Start open a fresh search.

## Tests

Run the Python suite in the active virtual environment. It starts its own
loopback server for the full 92-solution HTTP test.

```sh
python -B -m unittest discover -s MySolution/tests -v
```

To run the supplied LAMBDA3 library tests as well, use the same directory.

```sh
env PYTHONPATH=LAMBDA3 python -B -m unittest discover -s LAMBDA3/mylib/TEST -v
```

For the automated JavaScript scenarios, serve the assignment directory in a
separate terminal.

```sh
python3 -B -m http.server 18008 --bind 127.0.0.1
```

Open [the browser test page](http://127.0.0.1:18008/MySolution/tests/browser/).
It runs five scenarios and prints `PASS` or `FAIL` for each. The scenarios
use a test transport and do not require the Flask server. For the live
browser checklist and observed results, see [TESTING.md](TESTING.md).

## RPC examples

Run the following in a second terminal from `assigns/08/` while Flask is
running. The open command saves the returned ID for the next and close calls.

```sh
curl -fsS http://127.0.0.1:8000/rpc \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"service.health","params":{}}'

assign08_stream_id=$(curl -fsS http://127.0.0.1:8000/rpc \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":2,"method":"queens.open","params":{"size":8}}' \
  | python3 -c 'import json, sys; print(json.load(sys.stdin)["result"]["stream_id"])')

curl -fsS http://127.0.0.1:8000/rpc \
  -H 'Content-Type: application/json' \
  -d "{\"jsonrpc\":\"2.0\",\"id\":3,\"method\":\"queens.next\",\"params\":{\"stream_id\":\"$assign08_stream_id\",\"limit\":1}}"

curl -fsS http://127.0.0.1:8000/rpc \
  -H 'Content-Type: application/json' \
  -d "{\"jsonrpc\":\"2.0\",\"id\":4,\"method\":\"queens.close\",\"params\":{\"stream_id\":\"$assign08_stream_id\"}}"
```

The first event on a fresh stream is `try` at row 0, column 0 with an empty
board. Use `queens.next` with a limit of 1–32. The response containing the
final `done` event sets `done` to `true`. Later reads on that stream return
`{"events":[],"done":true}` while the completion record is active.
See [DESIGN.md](DESIGN.md#rpc-contract-and-lifecycle) for complete exchanges
and the error codes.

## Limitations

- The browser uses an 8×8 board. The solver and RPC accept sizes 4–10.
- Streams live in one server process and expire after five minutes of
  inactivity. Restarting the server or refreshing the page requires a fresh
  search. The service sweeps expired records during stream operations.
- This is a local, single-process service for the fixed queens solver.
  JSON-RPC batch requests and arbitrary LAMBDA3 input are outside its API.
