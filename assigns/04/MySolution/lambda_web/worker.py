"""One trusted worker invocation for real Lint or Interpret."""

import json
import sys

from .backend import LambdaBackend
from .contracts import Operation
from .worker_protocol import encode_result


def main() -> int:
    try:
        request = json.loads(sys.stdin.buffer.read().decode("utf-8"))
        if not isinstance(request, dict) or set(request) != {
            "operation", "source", "source_revision",
        }:
            raise ValueError("Invalid worker request fields.")
        operation = Operation(request["operation"])
        if operation not in (Operation.LINT, Operation.INTERPRET):
            raise ValueError("Worker supports only Lint and Interpret.")
        revision = request["source_revision"]
        if type(revision) is not int or revision < 0 or not isinstance(request["source"], str):
            raise ValueError("Invalid source or revision.")
        backend = LambdaBackend()
        method = backend.lint if operation is Operation.LINT else backend.interpret
        result = method(request["source"], revision)
        sys.stdout.buffer.write(encode_result(result).encode("utf-8"))
        sys.stdout.buffer.flush()
        return 0
    except Exception as error:
        sys.stderr.buffer.write(f"Worker failure ({type(error).__name__}): {error}".encode("utf-8"))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
