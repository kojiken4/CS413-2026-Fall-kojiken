# LAMBDA3 JSON-RPC contract

## HTTP transport

Send JSON-RPC 2.0 requests to `POST /rpc` with `Content-Type: application/json`.
The local development URL is `http://127.0.0.1:8000/rpc`.

| HTTP status | Meaning | Body |
| --- | --- | --- |
| `200 OK` | The server produced an RPC reply. Check the reply to determine the RPC outcome. | A JSON object or array with media type `application/json` |
| `204 No Content` | The request contained only valid notifications. | Empty |
| `415 Unsupported Media Type` | The request used an unsupported media type or omitted it. | Empty |

## Requests and replies

A request envelope is an object with `jsonrpc` set to `"2.0"` and a
case-sensitive string `method`. A call includes an `id` that is a string,
number, or `null`. Each method requires a `params` object, which the service
checks after validating the envelope. The reply includes `jsonrpc: "2.0"`,
the same `id`, and exactly one of `result` or `error`. An `id` of `null` is
still an explicit ID. Boolean values are invalid IDs.

Omit `id` to send a notification. The server dispatches a notification with a
valid envelope and sends no RPC reply, even if dispatch fails. An invalid
envelope receives an Invalid Request reply with `id: null`, including when it
omits `id` or supplies a numeric ID with an invalid protocol version.

A batch is a nonempty JSON array of requests. The server returns a reply array
with one entry for each call and each invalid member, omitting notifications.
Match replies by ID. A batch of only valid notifications returns HTTP `204`.
An empty array returns one Invalid Request object with `id: null`.

[rpc.schema.json](rpc.schema.json) describes the envelope shapes. Its
`requestPayload` and `responsePayload` definitions can be used separately to
validate the two directions. The service applies method-specific validation
after checking the envelope. It also handles malformed payloads and invalid
batch members according to the rules above.

## Methods

| Method | Named parameters | Result | Behavior |
| --- | --- | --- | --- |
| `service.health` | `{}` | `{"status":"ok","version":"1.0"}` | Report service status and API version. |
| `lambda.typecheck` | `{"source":"..."}` | `{"type":"sint"}` | Parse and type-check a LAMBDA3 expression. Return the type from `format_type`. |
| `lambda.interpret` | `{"source":"..."}` | `{"type":"sint","value":"42"}` | Parse, type-check, and evaluate the expression. Return the type from `format_type` and the value from `d0val_format`. Function values are strings such as `<lam>` and `<fix>`. |
| `lambda.compile` | `{"source":"...","target":"python"}` or `{"source":"...","target":"javascript"}` | `{"target":"python","code":"..."}` | Parse and type-check the expression, then return the selected compiler's source string unchanged. The service does not execute generated code. |

`source` must contain LAMBDA3 expression text and at least one non-whitespace
character. The maximum size is **16,384 bytes (16 KiB)** measured after JSON
decoding and UTF-8 encoding, before parsing. Missing `params`, non-object
`params`, missing fields, wrong field types, blank or oversized source, and
unsupported targets are Invalid Params errors for calls.

Each interpretation has a **2-second deadline** that covers the worker startup,
parsing, type-checking, evaluation, and formatting. The server terminates the
worker if the deadline expires. A timeout reports deadline expiry and cannot
determine whether the program would eventually finish.

## RPC errors

Every error has an integer `code` and a string `message`. When present, `data`
is a JSON object. Client replies contain safe diagnostics. Unexpected failures
are logged on the server, and RPC replies exclude tracebacks and filesystem
paths.

| Code | Message or category | When returned | `data` |
| --- | --- | --- | --- |
| `-32700` | Parse error | The HTTP body cannot be decoded as JSON. | Omitted |
| `-32600` | Invalid Request | The request envelope or batch member is invalid, or the batch is empty. | Omitted |
| `-32601` | Method not found | The method name is unknown. | Omitted |
| `-32602` | Invalid params | Parameters for a known method fail validation. | Omitted |
| `-32603` | Internal error | An unexpected server or backend failure occurs. | Omitted |
| `-32010` | LAMBDA3 syntax diagnostic | LAMBDA3 raises `LambdaSyntaxError` for the source. | One-based integer `line` and `column` when available |
| `-32011` | LAMBDA3 type diagnostic | LAMBDA3 raises `TypeCheckError` for the source. | Omitted |
| `-32012` | Interpretation timed out | The interpretation deadline expires. | Omitted |

## Examples

Each request below is the body of `POST /rpc` with `Content-Type: application/json`.

### Health

```json
{"jsonrpc":"2.0","method":"service.health","params":{},"id":"health"}
```

HTTP `200` reply

```json
{"jsonrpc":"2.0","result":{"status":"ok","version":"1.0"},"id":"health"}
```

### Type-check an expression

```json
{"jsonrpc":"2.0","method":"lambda.typecheck","params":{"source":"1 + 2"},"id":1}
```

HTTP `200` reply

```json
{"jsonrpc":"2.0","result":{"type":"sint"},"id":1}
```

### Interpret an expression

```json
{"jsonrpc":"2.0","method":"lambda.interpret","params":{"source":"6 * 7"},"id":2}
```

HTTP `200` reply

```json
{"jsonrpc":"2.0","result":{"type":"sint","value":"42"},"id":2}
```

### Compile an expression

```json
{"jsonrpc":"2.0","method":"lambda.compile","params":{"source":"42","target":"python"},"id":3}
```

HTTP `200` reply

<details>
<summary>Full reply with generated Python source</summary>

```json
{
  "jsonrpc": "2.0",
  "result": {
    "target": "python",
    "code": "# The emitted program uses Python values for integers, booleans, lists and\n# tuples. Options need a tagged pair so optn_cons(None) remains distinct from\n# optn_nil (None); the private sentinel is created once per generated program.\ndef _lambda_list_cons(head, tail):\n    if not isinstance(tail, list):\n        raise TypeError(\"list_cons: list tail expected\")\n    return [head] + tail\n\ndef _lambda_list_nilq(value):\n    if not isinstance(value, list):\n        raise TypeError(\"list_nilq: list expected\")\n    return len(value) == 0\n\ndef _lambda_list_head(value):\n    if not isinstance(value, list):\n        raise TypeError(\"list_head: list expected\")\n    if not value:\n        raise ValueError(\"list_head: nonempty list expected\")\n    return value[0]\n\ndef _lambda_list_tail(value):\n    if not isinstance(value, list):\n        raise TypeError(\"list_tail: list expected\")\n    if not value:\n        raise ValueError(\"list_tail: nonempty list expected\")\n    return value[1:]\n\ndef _lambda_a1sz_index(array, index):\n    if not isinstance(array, list) or not isinstance(index, int) or isinstance(index, bool):\n        raise TypeError(\"A1sz indexing expects an array and sint index\")\n    if not 0 <= index < len(array): raise IndexError(\"A1sz index out of range\")\n    return index\ndef _lambda_a1sz_getat(array, index): return array[_lambda_a1sz_index(array, index)]\ndef _lambda_a1sz_setat(array, index, value):\n    array[_lambda_a1sz_index(array, index)] = value\n    return ()\ndef _lambda_a1sz_make_ncpy(size, value):\n    if not isinstance(size, int) or isinstance(size, bool): raise TypeError(\"A1sz size must be sint\")\n    if size < 0: raise ValueError(\"A1sz size must be nonnegative\")\n    return [value for _ in range(size)]\ndef _lambda_a1sz_make_nfun(size, fn):\n    if not isinstance(size, int) or isinstance(size, bool): raise TypeError(\"A1sz size must be sint\")\n    if size < 0: raise ValueError(\"A1sz size must be nonnegative\")\n    return [fn(i) for i in range(size)]\n\ndef _lambda_optn_cons(value):\n    return (_lambda_some_tag, value)\n\ndef _lambda_optn_nilq(value):\n    return value is None\n\ndef _lambda_optn_get(value):\n    if value is None or not (isinstance(value, tuple) and len(value) == 2 and value[0] is _lambda_some_tag):\n        raise ValueError(\"optn_get: nonempty option expected\")\n    return value[1]\n\nclass _LambdaLazy:\n    def __init__(self, thunk):\n        self.thunk, self.evaluated, self.value = thunk, False, None\n\ndef _lambda_lazy_make(thunk):\n    if not callable(thunk): raise TypeError(\"lazy_make: thunk function expected\")\n    return _LambdaLazy(thunk)\ndef _lambda_lazy_eval(value):\n    if not isinstance(value, _LambdaLazy): raise TypeError(\"lazy_eval: Lazy value expected\")\n    if not value.evaluated:\n        value.value = value.thunk(())\n        value.evaluated = True\n    return value.value\ndef _lambda_stcn_nil(): return {\"cons\": False}\ndef _lambda_stcn_cons(head, tail):\n    if not isinstance(tail, _LambdaLazy): raise TypeError(\"stcn_cons: lazy stream tail expected\")\n    return {\"cons\": True, \"head\": head, \"tail\": tail}\ndef _lambda_stcn_check(value, name):\n    if not isinstance(value, dict) or \"cons\" not in value: raise TypeError(name + \": Stcn value expected\")\ndef _lambda_stcn_nilq(value):\n    _lambda_stcn_check(value, \"stcn_nilq\")\n    return not value[\"cons\"]\ndef _lambda_stcn_consq(value):\n    _lambda_stcn_check(value, \"stcn_consq\")\n    return value[\"cons\"]\ndef _lambda_stcn_head(value):\n    _lambda_stcn_check(value, \"stcn_head\")\n    if not value[\"cons\"]: raise ValueError(\"stcn_head: nonempty stream constructor expected\")\n    return value[\"head\"]\ndef _lambda_stcn_tail(value):\n    _lambda_stcn_check(value, \"stcn_tail\")\n    if not value[\"cons\"]: raise ValueError(\"stcn_tail: nonempty stream constructor expected\")\n    return value[\"tail\"]\n\ndef _lambda_format(value):\n    if isinstance(value, _LambdaLazy): return \"<lazy>\"\n    if isinstance(value, dict) and \"cons\" in value:\n        if not value[\"cons\"]: return \"stcn_nil()\"\n        return \"stcn_cons(\" + _lambda_format(value[\"head\"]) + \", <lazy>)\"\n    if value is None:\n        return \"optn_nil()\"\n    if isinstance(value, tuple) and len(value) == 2 and value[0] is _lambda_some_tag:\n        return \"optn_cons(\" + _lambda_format(value[1]) + \")\"\n    if isinstance(value, bool):\n        return \"true\" if value else \"false\"\n    if isinstance(value, list):\n        return \"[\" + \", \".join(_lambda_format(item) for item in value) + \"]\"\n    if isinstance(value, tuple):\n        body = \", \".join(_lambda_format(item) for item in value)\n        return \"(\" + body + (\",\" if len(value) == 1 else \"\") + \")\"\n    if callable(value):\n        return \"<lam>\"\n    return str(value)\n\ndef _lambda_print(value):\n    print(_lambda_format(value))\n    return ()\n\n_lambda_some_tag = object()\n\ndef _lambda_main():\n    _v1 = 42\n    return _v1\n\n_lambda_result = _lambda_main()\n"
  },
  "id": 3
}
```

</details>

### Report a LAMBDA3 syntax error

```json
{"jsonrpc":"2.0","method":"lambda.typecheck","params":{"source":"if then"},"id":"syntax"}
```

HTTP `200` reply

```json
{"jsonrpc":"2.0","error":{"code":-32010,"message":"Expected an expression","data":{"line":1,"column":4}},"id":"syntax"}
```

### Report a LAMBDA3 type error

```json
{"jsonrpc":"2.0","method":"lambda.typecheck","params":{"source":"1 + true"},"id":"type"}
```

HTTP `200` reply

```json
{"jsonrpc":"2.0","error":{"code":-32011,"message":"+: expected bool, got sint"},"id":"type"}
```

### Batch with calls and a notification

```json
[
  {"jsonrpc":"2.0","method":"service.health","params":{},"id":"health"},
  {"jsonrpc":"2.0","method":"service.health","params":{}},
  {"jsonrpc":"2.0","method":"lambda.interpret","params":{"source":"6 * 7"},"id":null}
]
```

HTTP `200` reply

```json
[
  {"jsonrpc":"2.0","result":{"status":"ok","version":"1.0"},"id":"health"},
  {"jsonrpc":"2.0","result":{"type":"sint","value":"42"},"id":null}
]
```

### Batch of only notifications

```json
[
  {"jsonrpc":"2.0","method":"service.health","params":{}},
  {"jsonrpc":"2.0","method":"lambda.typecheck","params":{"source":"1 + 2"}}
]
```

The reply is HTTP `204` with an empty body.
