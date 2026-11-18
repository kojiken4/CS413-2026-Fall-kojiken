"""Check JSON-RPC behavior and consume a full search over real HTTP."""

import json
import unittest
from http.client import HTTPConnection
from threading import Thread
from unittest.mock import patch

from werkzeug.serving import WSGIRequestHandler, make_server

from MySolution.http import create_app
from MySolution.streams import INACTIVITY_SECONDS, StreamTable


_OMITTED = object()


class RpcContractTests(unittest.TestCase):
    def setUp(self):
        self.now = 0.0
        streams = StreamTable(clock=lambda: self.now)
        self.client = create_app(streams=streams).test_client()

    def call(self, method, params=_OMITTED, request_id="call"):
        payload = {"jsonrpc": "2.0", "method": method}
        if params is not _OMITTED:
            payload["params"] = params
        if request_id is not _OMITTED:
            payload["id"] = request_id
        return self.client.post("/rpc", json=payload)

    def error(self, response, code, message, request_id="call"):
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/json")
        self.assertEqual(response.json, {
            "jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message},
        })

    def open_stream(self, size=4):
        response = self.call("queens.open", {"size": size})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["result"]["size"], size)
        return response.json["result"]["stream_id"]

    def test_health_and_request_ids_including_explicit_null(self):
        for request_id in (0, "", "req-19", None, 3.5):
            with self.subTest(request_id=request_id):
                response = self.call("service.health", request_id=request_id)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.mimetype, "application/json")
                self.assertEqual(response.json, {
                    "jsonrpc": "2.0", "id": request_id,
                    "result": {"status": "ok", "version": "1.0"},
                })

    def test_parse_errors_and_wrong_content_type(self):
        for body in (b"", b"{", b"\xff", b'{"id": NaN}'):
            with self.subTest(body=body):
                response = self.client.post("/rpc", data=body, content_type="application/json")
                self.error(response, -32700, "Parse error", request_id=None)
        wrong_type = self.client.post("/rpc", data="{}", content_type="text/plain")
        self.assertEqual(wrong_type.status_code, 415)

    def test_invalid_envelopes_and_batch_arrays(self):
        for payload in (
            [], [{"jsonrpc": "2.0", "method": "service.health", "id": 1}], "string", 17, {},
            {"method": "service.health", "id": "bad"},
            {"jsonrpc": "1.0", "method": "service.health", "id": "bad"},
            {"jsonrpc": "2.0", "method": 3},
            {"jsonrpc": "2.0", "method": "service.health", "id": False},
            {"jsonrpc": "2.0", "method": "service.health", "id": {}},
        ):
            with self.subTest(payload=payload):
                self.error(self.client.post("/rpc", json=payload), -32600, "Invalid Request", request_id=None)

    def test_unknown_methods_including_assign07_methods(self):
        for method in ("", "queens.unknown", "lambda.interpret"):
            with self.subTest(method=method):
                self.error(self.call(method, {}), -32601, "Method not found")

    def test_invalid_params_do_not_consume_a_stream(self):
        stream_id = self.open_stream()
        for method, params in (
            ("service.health", None), ("service.health", []), ("service.health", {"extra": True}),
            ("queens.open", _OMITTED), ("queens.open", {"size": 8, "source": "1+2"}),
            ("queens.open", {"size": 3}), ("queens.open", {"size": 11}),
            ("queens.open", {"size": False}), ("queens.open", {"size": 8.0}),
            ("queens.next", {"stream_id": stream_id}),
            ("queens.next", {"stream_id": stream_id, "limit": 0}),
            ("queens.next", {"stream_id": stream_id, "limit": 33}),
            ("queens.next", {"stream_id": stream_id, "limit": True}),
            ("queens.next", {"stream_id": stream_id, "limit": 1.0}),
            ("queens.next", {"stream_id": "", "limit": 1}),
            ("queens.close", {"stream_id": 1}),
            ("queens.close", {"stream_id": stream_id, "extra": "x"}),
        ):
            with self.subTest(method=method, params=params):
                self.error(self.call(method, params), -32602, "Invalid params")
        next_result = self.call("queens.next", {"stream_id": stream_id, "limit": 1}).json["result"]
        self.assertEqual(next_result, {
            "events": [{"event": "try", "row": 0, "column": 0, "board": []}], "done": False,
        })

    def test_notifications_dispatch_without_a_body(self):
        stream_id = self.open_stream()
        params = {"stream_id": stream_id, "limit": 1}
        notice = self.call("queens.next", params, request_id=_OMITTED)
        self.assertEqual(notice.status_code, 204)
        self.assertEqual(notice.get_data(), b"")
        result = self.call("queens.next", params, request_id=None).json
        self.assertIsNone(result["id"])
        self.assertEqual(result["result"], {
            "events": [{"event": "place", "row": 0, "column": 0, "board": [0]}], "done": False,
        })
        for method, params in (("queens.next", {}), ("unknown", {})):
            with self.subTest(method=method):
                response = self.call(method, params, request_id=_OMITTED)
                self.assertEqual(response.status_code, 204)
                self.assertEqual(response.get_data(), b"")

    def test_missing_closed_and_expired_ids_share_application_error(self):
        closed = self.open_stream()
        close_result = self.call("queens.close", {"stream_id": closed}).json["result"]
        self.assertEqual(close_result, {"closed": True})
        expired = self.open_stream()
        self.now = INACTIVITY_SECONDS
        for stream_id in ("unknown", closed, expired):
            with self.subTest(stream_id=stream_id):
                next_response = self.call("queens.next", {"stream_id": stream_id, "limit": 1})
                close_response = self.call("queens.close", {"stream_id": stream_id})
                self.error(next_response, -32004, "Stream not found")
                self.error(close_response, -32004, "Stream not found")

    def test_unexpected_solver_error_is_sanitized_and_cursor_is_retryable(self):
        params = {"stream_id": self.open_stream(), "limit": 1}
        with patch("MySolution.streams.force_event", side_effect=ValueError("/private/file")):
            with self.assertLogs("MySolution.dispatcher", level="ERROR"):
                response = self.call("queens.next", params)
        self.error(response, -32603, "Internal error")
        result = self.call("queens.next", params).json["result"]
        self.assertEqual(result["events"], [{"event": "try", "row": 0, "column": 0, "board": []}])


class _QuietRequestHandler(WSGIRequestHandler):
    def log_request(self, code="-", size="-"):
        pass


class LiveHttpTests(unittest.TestCase):
    def setUp(self):
        server = make_server("127.0.0.1", 0, create_app(), request_handler=_QuietRequestHandler)
        self.addCleanup(server.server_close)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join, 5)
        self.addCleanup(server.shutdown)

        self.connection = HTTPConnection("127.0.0.1", server.server_port, timeout=5)
        self.addCleanup(self.connection.close)
        self.request_id = 0

    def result(self, method, params):
        self.request_id += 1
        payload = {"jsonrpc": "2.0", "id": self.request_id, "method": method, "params": params}
        self.connection.request("POST", "/rpc", json.dumps(payload), {"Content-Type": "application/json"})
        response = self.connection.getresponse()
        self.assertEqual(response.status, 200)
        self.assertEqual(response.headers.get_content_type(), "application/json")
        body = json.loads(response.read())
        self.assertEqual(set(body), {"jsonrpc", "id", "result"})
        self.assertEqual(body["jsonrpc"], "2.0")
        self.assertEqual(body["id"], self.request_id)
        return body["result"]

    def test_live_http_consumes_all_92_solutions_and_done(self):
        self.assertEqual(self.result("service.health", {}), {"status": "ok", "version": "1.0"})
        opened = self.result("queens.open", {"size": 8})
        self.assertEqual(opened["size"], 8)
        stream = {"stream_id": opened["stream_id"]}
        single = self.result("queens.next", {**stream, "limit": 1})
        self.assertEqual(single, {
            "events": [{"event": "try", "row": 0, "column": 0, "board": []}], "done": False,
        })

        solutions = []
        for _ in range(2000):
            batch = self.result("queens.next", {**stream, "limit": 32})
            events = batch["events"]
            self.assertTrue(1 <= len(events) <= 32)
            self.assertEqual(events.count({"event": "done"}), int(batch["done"]))
            for event in events:
                if event["event"] == "solution":
                    board = event["board"]
                    self.assertIsInstance(board, list)
                    self.assertEqual(len(board), 8)
                    self.assertEqual(set(board), set(range(8)))
                    self.assertEqual(len({row + col for row, col in enumerate(board)}), 8)
                    self.assertEqual(len({row - col for row, col in enumerate(board)}), 8)
                    solutions.append(tuple(board))
            if batch["done"]:
                self.assertEqual(events[-1], {"event": "done"})
                break
            self.assertEqual(len(events), 32)
        else:
            self.fail("8×8 search did not finish")

        self.assertEqual(len(solutions), 92)
        self.assertEqual(solutions, sorted(set(solutions)))
        self.assertEqual(self.result("queens.next", {**stream, "limit": 32}), {"events": [], "done": True})
        self.assertEqual(self.result("queens.close", stream), {"closed": True})
