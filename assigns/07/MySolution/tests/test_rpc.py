"""HTTP tests for the JSON-RPC transport and dispatcher."""

import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from MySolution.lambda_rpc import dispatcher, http, service


LAMBDA3_DIR = Path(__file__).resolve().parents[2] / "LAMBDA3"


def health_call(**overrides):
    return {"jsonrpc": "2.0", "method": "service.health", "params": {}, "id": 1} | overrides


def health_notification(**overrides):
    request = health_call(**overrides)
    del request["id"]
    return request


class RpcHttpTests(unittest.TestCase):
    def setUp(self):
        self.client = http.create_app().test_client()

    def assert_rpc_error(self, response, request_id, code):
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/json")
        body = response.get_json()
        self.assertEqual(set(body), {"jsonrpc", "id", "error"})
        self.assertEqual(body["jsonrpc"], "2.0")
        self.assertEqual(body["id"], request_id)
        self.assertEqual(body["error"]["code"], code)
        self.assertIsInstance(body["error"]["message"], str)
        return body["error"]

    def assert_rpc_result(self, response, request_id, result):
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/json")
        self.assertEqual(response.get_json(), {
            "jsonrpc": "2.0", "id": request_id, "result": result,
        })

    def call(self, method, params):
        return self.client.post("/rpc", json={
            "jsonrpc": "2.0", "method": method, "params": params, "id": "source",
        })

    def test_health_preserves_call_ids(self):
        for request_id in ("health", 0, 1.25, None):
            with self.subTest(request_id=request_id):
                response = self.client.post("/rpc", json=health_call(id=request_id))
                self.assert_rpc_result(response, request_id, {"status": "ok", "version": "1.0"})

    def test_typecheck_returns_formatted_types(self):
        for source, inferred_type in (("1 + 2", "sint"), ("(1, true)", "(sint, bool)")):
            with self.subTest(source=source):
                response = self.call("lambda.typecheck", {"source": source})
                self.assert_rpc_result(response, "source", {"type": inferred_type})

    def test_typecheck_rejects_unbound_variable(self):
        response = self.call("lambda.typecheck", {"source": "missing"})
        error = self.assert_rpc_error(response, "source", -32011)
        self.assertEqual(error["message"], "unbound variable 'missing'")

    def test_language_syntax_and_type_errors(self):
        for method, extra in (
            ("lambda.typecheck", {}),
            ("lambda.compile", {"target": "python"}),
            ("lambda.compile", {"target": "javascript"}),
            ("lambda.interpret", {}),
        ):
            with self.subTest(method=method, target=extra.get("target")):
                response = self.call(method, {"source": "if then"} | extra)
                error = self.assert_rpc_error(response, "source", -32010)
                self.assertEqual(error, {
                    "code": -32010,
                    "message": "Expected an expression",
                    "data": {"line": 1, "column": 4},
                })
                response = self.call(method, {"source": "1 + true"} | extra)
                error = self.assert_rpc_error(response, "source", -32011)
                self.assertEqual(error, {"code": -32011, "message": "+: expected bool, got sint"})

    def test_compile_returns_both_compilers_output_unchanged(self):
        source = "1 + 2"
        expression, _ = service.lambda3.d0exp_parse_and_typecheck(source)
        for target, compiler in (
            ("python", service.lambda3.d0exp_compile),
            ("javascript", service.lambda3.d0exp_compile_js),
        ):
            with self.subTest(target=target):
                response = self.call("lambda.compile", {"source": source, "target": target})
                code = compiler(expression)
                self.assertTrue(code.strip())
                self.assert_rpc_result(response, "source", {"target": target, "code": code})

    def test_source_parameter_validation_for_language_methods(self):
        for method, extra in (
            ("lambda.typecheck", {}),
            ("lambda.compile", {"target": "python"}),
            ("lambda.interpret", {}),
        ):
            for params in ({}, {"source": 42}, {"source": ""}, {"source": " \t\n"}, {"source": "\ud800"}):
                with self.subTest(method=method, params=params):
                    response = self.call(method, params | extra)
                    self.assert_rpc_error(response, "source", -32602)

    def test_source_limit_counts_utf8_bytes(self):
        # "42 #" is four bytes and each following comment character is two.
        limit_source = "42 #" + "\u00e9" * 8_190
        response = self.call("lambda.typecheck", {"source": limit_source})
        self.assert_rpc_result(response, "source", {"type": "sint"})
        for method, extra in (
            ("lambda.typecheck", {}),
            ("lambda.compile", {"target": "python"}),
            ("lambda.interpret", {}),
        ):
            with self.subTest(method=method):
                response = self.call(method, {"source": limit_source + "x"} | extra)
                self.assert_rpc_error(response, "source", -32602)

    def test_compile_validates_target(self):
        for extra in ({}, {"target": []}, {"target": "Python"}, {"target": "ruby"}):
            with self.subTest(extra=extra):
                response = self.call("lambda.compile", {"source": "42"} | extra)
                self.assert_rpc_error(response, "source", -32602)

    def test_interpret_returns_formatted_values_and_types(self):
        for source, inferred_type, value in (
            ("6 * 7", "sint", "42"),
            ("(1, true)", "(sint, bool)", "(1, true)"),
            ("list_cons(1, list_cons(2, list_nil()))", "List[sint]", "[1, 2]"),
            ("lam (x: sint) => x", "sint -> sint", "<lam>"),
            ("print(42)", "unit", "()"),
        ):
            with self.subTest(source=source):
                response = self.call("lambda.interpret", {"source": source})
                self.assert_rpc_result(response, "source", {"type": inferred_type, "value": value})

    def test_interpret_factorial(self):
        source = (LAMBDA3_DIR / "mytest" / "factorial.lam").read_text(encoding="utf-8")
        response = self.call("lambda.interpret", {"source": source})
        self.assert_rpc_result(response, "source", {
            "type": "(sint, sint, sint, sint)", "value": "(1, 1, 120, 720)",
        })

    def test_interpret_uses_provided_list_library(self):
        declarations = (LAMBDA3_DIR / "mylib" / "list.lam").read_text(encoding="utf-8")
        source = f"let\n{declarations}\nin list_range(1, 4) end"
        response = self.call("lambda.interpret", {"source": source})
        self.assert_rpc_result(response, "source", {"type": "List[sint]", "value": "[1, 2, 3]"})

    def test_interpret_timeout_stops_worker_and_allows_next_request(self):
        processes = []
        start_process = subprocess.Popen

        def record_process(*args, **kwargs):
            process = start_process(*args, **kwargs)
            processes.append(process)
            return process

        slow_worker = (sys.executable, "-B", "-c", "import time; time.sleep(30)")
        with patch.object(service, "WORKER_COMMAND", slow_worker):
            with patch.object(subprocess, "Popen", side_effect=record_process):
                response = self.call("lambda.interpret", {"source": "42"})

        error = self.assert_rpc_error(response, "source", -32012)
        self.assertEqual(error, {"code": -32012, "message": "Interpretation timed out"})
        self.assertEqual(len(processes), 1)
        self.assertIsNotNone(processes[0].returncode)
        self.assertNotEqual(processes[0].returncode, 0)
        response = self.call("lambda.interpret", {"source": "42"})
        self.assert_rpc_result(response, "source", {"type": "sint", "value": "42"})

    def test_interpret_worker_failure_is_logged_and_redacted(self):
        with self.assertLogs(dispatcher.__name__, level="ERROR") as logs:
            response = self.call("lambda.interpret", {"source": "1 / 0"})
        error = self.assert_rpc_error(response, "source", -32603)
        self.assertEqual(error, {"code": -32603, "message": "Internal error"})
        self.assertIn("ZeroDivisionError", logs.output[0])

    def test_interpret_rejects_invalid_worker_reply(self):
        bad_worker = (sys.executable, "-B", "-c", "print('{}')")
        with patch.object(service, "WORKER_COMMAND", bad_worker):
            with self.assertLogs(dispatcher.__name__, level="ERROR") as logs:
                response = self.call("lambda.interpret", {"source": "42"})
        error = self.assert_rpc_error(response, "source", -32603)
        self.assertEqual(error, {"code": -32603, "message": "Internal error"})
        self.assertIn("Invalid interpretation worker reply", logs.output[0])

    def test_unsupported_media_type_is_a_transport_error(self):
        for content_type in (None, "text/plain", "application/problem+json"):
            with self.subTest(content_type=content_type):
                response = self.client.post("/rpc", data="{}", content_type=content_type)
                self.assertEqual(response.status_code, 415)
                self.assertEqual(response.data, b"")

    def test_malformed_json(self):
        for body in (b'{"jsonrpc":', b"", b"\xff", b'{"id":NaN}'):
            with self.subTest(body=body):
                response = self.client.post("/rpc", data=body, content_type="application/json")
                self.assert_rpc_error(response, None, -32700)

    def test_invalid_envelope_gets_null_id(self):
        cases = [
            "not a request",
            {"jsonrpc": "2.0"},
            health_call(jsonrpc="1.0"),
            health_call(method=4),
            health_call(id=True),
            health_call(id=[]),
        ]
        for request in cases:
            with self.subTest(request=request):
                response = self.client.post("/rpc", json=request)
                self.assert_rpc_error(response, None, -32600)

    def test_unknown_method_is_case_sensitive(self):
        response = self.client.post("/rpc", json=health_call(method="Service.Health"))
        self.assert_rpc_error(response, 1, -32601)

    def test_invalid_health_params(self):
        missing_params = health_call()
        del missing_params["params"]
        for request in (
            missing_params, health_call(params=[]), health_call(params=None),
            health_call(params={"extra": "value"}),
        ):
            with self.subTest(request=request):
                response = self.client.post("/rpc", json=request)
                self.assert_rpc_error(response, 1, -32602)

    def test_mixed_batch_preserves_ids_and_omits_notifications(self):
        response = self.client.post("/rpc", json=[
            health_call(id="ok"),
            health_notification(),
            "invalid member",
            health_call(id=2, method="missing"),
        ])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/json")
        replies = response.get_json()
        self.assertEqual(len(replies), 3)
        self.assertEqual({reply["id"]: reply for reply in replies}, {
            "ok": {
                "jsonrpc": "2.0", "id": "ok",
                "result": {"status": "ok", "version": "1.0"},
            },
            None: {
                "jsonrpc": "2.0", "id": None,
                "error": {"code": -32600, "message": "Invalid Request"},
            },
            2: {
                "jsonrpc": "2.0", "id": 2,
                "error": {"code": -32601, "message": "Method not found"},
            },
        })

    def test_empty_batch_returns_one_error_object(self):
        response = self.client.post("/rpc", json=[])
        self.assert_rpc_error(response, None, -32600)

    def test_notifications_are_dispatched_without_replies(self):
        with patch.object(http, "health", wraps=http.health) as health:
            client = http.create_app().test_client()
            for payload in (
                health_notification(),
                [health_notification(), health_notification(method="missing")],
            ):
                with self.subTest(payload=payload):
                    response = client.post("/rpc", json=payload)
                    self.assertEqual(response.status_code, 204)
                    self.assertEqual(response.data, b"")
            self.assertEqual(health.call_count, 2)

    def test_unexpected_failure_is_logged_and_redacted(self):
        failure = RuntimeError("private path: C:/private/backend.py")
        with patch.object(http, "health", side_effect=failure):
            client = http.create_app().test_client()
            with self.assertLogs(dispatcher.__name__, level="ERROR") as logs:
                response = client.post("/rpc", json=health_call(id="failure"))
        error = self.assert_rpc_error(response, "failure", -32603)
        self.assertEqual(error, {"code": -32603, "message": "Internal error"})
        self.assertIn(str(failure), logs.output[0])
