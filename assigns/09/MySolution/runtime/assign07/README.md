# Packaged Assign07 runtime

This directory contains an unchanged copy of `assigns/07/MySolution/lambda_rpc/`
and the language implementation and libraries from `assigns/07/LAMBDA3/` at
repository commit `08640bc4bdbeee33056607484acb0a3c561f59`. The original layout
lets the RPC service locate LAMBDA3 and start its interpretation worker.
The repository license is included.

Run the RPC service in a separate terminal from the Assign09 `MySolution/`
directory using the same Python environment as the studio.

```sh
python -B -m flask --app runtime.assign07.MySolution.lambda_rpc.http:create_app run --host 127.0.0.1 --port 8000
```

The studio forwards interpretation requests to `http://127.0.0.1:8000/rpc`.
