# Assignment 07 · LAMBDA3 JSON-RPC service

Use `POST http://127.0.0.1:8000/rpc` with `Content-Type: application/json`.
The service checks, interprets, and compiles expressions in the supplied
LAMBDA3 language. Compilation returns generated Python or JavaScript source
as text. The service never runs the generated code.

See [RPC.md](RPC.md) for the method contract, error codes, batch and notification
examples, and limits. [rpc.schema.json](rpc.schema.json) describes the request
and response envelopes.

## Setup

Use Python 3.12 or later and curl. The service requires Flask 3.1.x and was
verified with Python 3.14.7 and Flask 3.1.3. Run the commands below from
`assigns/07/` so the solution and the provided `LAMBDA3/` directory are both
available. The virtual environment lives outside the checkout.

### Windows PowerShell

```powershell
$assign07Env = Join-Path ([System.IO.Path]::GetTempPath()) 'cs413-assign07-venv'
python -m venv $assign07Env
& "$assign07Env\Scripts\Activate.ps1"
python -m pip install -r MySolution/requirements.txt
```

### Bash on macOS or Linux

```bash
assign07_env="$(mktemp -d)"
python3 -m venv "$assign07_env"
source "$assign07_env/bin/activate"
python -m pip install -r MySolution/requirements.txt
```

## Run and test

Run the solution's HTTP tests with the virtual environment active. These use
Flask's test client and can run before the server starts.

```text
python -B -m unittest discover -s MySolution/tests -v
```

Start the server and leave this terminal open.

```text
python -B -m flask --app MySolution.lambda_rpc.http:create_app run --host 127.0.0.1 --port 8000
```

In a second terminal in `assigns/07/`, run the supplied tests against the
running server. This suite uses Python's standard library.

```text
python -B -m unittest discover -s TEST -v
```

See [TESTING.md](TESTING.md) for the test coverage and observed results.

## Try the RPC methods

Run these from a second terminal while the server is running. In Bash, use
`curl` in place of `curl.exe`.

### Check service health

```powershell
echo '{"jsonrpc":"2.0","method":"service.health","params":{},"id":"health"}' |
  curl.exe --silent --show-error --include --header 'Content-Type: application/json' --data-binary '@-' http://127.0.0.1:8000/rpc
```

Expect HTTP `200` and `{"status":"ok","version":"1.0"}` in `result`.

### Type-check an expression

```powershell
echo '{"jsonrpc":"2.0","method":"lambda.typecheck","params":{"source":"1 + 2"},"id":"type"}' |
  curl.exe --silent --show-error --include --header 'Content-Type: application/json' --data-binary '@-' http://127.0.0.1:8000/rpc
```

Expect HTTP `200` and `{"type":"sint"}` in `result`.

### Interpret factorial

```powershell
echo '{"jsonrpc":"2.0","method":"lambda.interpret","params":{"source":"let fact : sint -> sint = fix fact(n: sint): sint => if n <= 1 then 1 else n * fact(n - 1) in fact(6) end"},"id":"factorial"}' |
  curl.exe --silent --show-error --include --header 'Content-Type: application/json' --data-binary '@-' http://127.0.0.1:8000/rpc
```

Expect HTTP `200` and `{"type":"sint","value":"720"}` in `result`.

### Compile to JavaScript

```powershell
echo '{"jsonrpc":"2.0","method":"lambda.compile","params":{"source":"6 * 7","target":"javascript"},"id":"compile"}' |
  curl.exe --silent --show-error --include --header 'Content-Type: application/json' --data-binary '@-' http://127.0.0.1:8000/rpc
```

Expect HTTP `200`, `result.target` set to `"javascript"`, and generated
source in `result.code`. Set `target` to `"python"` for Python source.

### See an unbound-variable error

```powershell
echo '{"jsonrpc":"2.0","method":"lambda.typecheck","params":{"source":"missing"},"id":"unbound"}' |
  curl.exe --silent --show-error --include --header 'Content-Type: application/json' --data-binary '@-' http://127.0.0.1:8000/rpc
```

Expect HTTP `200` and an RPC `error` with code `-32011` and message
`unbound variable 'missing'`.
