"""Read one source expression and write one JSON interpretation reply."""

import json
import os
import sys
from contextlib import redirect_stdout

from .dispatcher import RpcError
from .service import lambda3, parse_and_typecheck


def main() -> None:
    source = sys.stdin.buffer.read().decode("utf-8")
    # Keep LAMBDA3 print output separate from the worker reply on stdout.
    with open(os.devnull, "w", encoding="utf-8") as discard, redirect_stdout(discard):
        try:
            expression, inferred_type = parse_and_typecheck(source)
            value = lambda3.d0exp_evaluate(expression)
            reply = {"result": {
                "type": lambda3.format_type(inferred_type),
                "value": lambda3.d0val_format(value),
            }}
        except RpcError as error:
            reply = {"error": {"code": error.code, "message": str(error), "data": error.data}}
    sys.stdout.write(json.dumps(reply))


if __name__ == "__main__":
    main()
