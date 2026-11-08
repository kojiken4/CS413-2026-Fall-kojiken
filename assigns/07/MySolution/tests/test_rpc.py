"""HTTP tests for the JSON-RPC transport and dispatcher."""

import unittest
from unittest.mock import patch

from MySolution.lambda_rpc import dispatcher, http


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

    def test_health_preserves_call_ids(self):
        for request_id in ("health", 0, 1.25, None):
            with self.subTest(request_id=request_id):
                response = self.client.post("/rpc", json=health_call(id=request_id))
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.mimetype, "application/json")
                self.assertEqual(response.get_json(), {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {"status": "ok", "version": "1.0"},
                })

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
