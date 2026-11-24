"""Exercise program storage and transport through the public HTTP API."""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Barrier
from unittest import TestCase
from unittest.mock import patch

from studio_storage import http

PROGRAMS = "/api/v1/programs"


class ProgramApiTests(TestCase):
    def setUp(self):
        self.app = http.create_app()
        self.client = self.app.test_client()

    def assert_error(self, response, status, code, *, current_revision=None):
        self.assertEqual(response.status_code, status)
        self.assertEqual(response.mimetype, "application/json")
        body = response.get_json()
        self.assertEqual(set(body), {"error"})
        error = body["error"]
        expected_fields = {"code", "message"}
        if current_revision is not None:
            expected_fields.add("current_revision")
            self.assertEqual(error["current_revision"], current_revision)
        self.assertEqual(set(error), expected_fields)
        self.assertEqual(error["code"], code)
        self.assertIsInstance(error["message"], str)
        self.assertTrue(error["message"])

    def create_program(self, name, source="1 + 2", **fields):
        response = self.client.post(PROGRAMS, json={"name": name, "source": source, **fields})
        self.assertEqual(response.status_code, 201, response.get_data(as_text=True))
        self.assertEqual(response.mimetype, "application/json")
        self.assertEqual(response.headers["ETag"], '"1"')
        return response.get_json()["program"]

    def test_health_missing_route_and_unsupported_method(self):
        health = self.client.get("/api/v1/health")
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.mimetype, "application/json")
        self.assertEqual(health.get_json(), {"status": "ok", "version": "1.0"})
        self.assert_error(self.client.get("/api/v1/missing"), 404, "record_not_found")
        unsupported = self.client.patch(PROGRAMS)
        self.assert_error(unsupported, 405, "method_not_allowed")
        self.assertTrue({"GET", "POST"} <= set(unsupported.headers["Allow"].split(", ")))
        self.assert_error(self.client.get(f"{PROGRAMS}/%00"), 400, "invalid_request")

    def test_program_crud_preserves_source_and_sets_version_fields(self):
        original = self.create_program("  Sample  ", "\n6 * 7  ")
        self.assertEqual(set(original), {
            "id", "name", "source", "description", "created_at", "updated_at", "revision",
        })
        self.assertIsInstance(original["id"], str)
        self.assertTrue(original["id"])
        self.assertEqual(original["name"], "Sample")
        self.assertEqual(original["source"], "\n6 * 7  ")
        self.assertEqual(original["description"], "")
        self.assertEqual(original["revision"], 1)
        self.assertEqual(original["created_at"], original["updated_at"])
        self.assertTrue(original["created_at"].endswith("Z"))
        self.assertEqual(datetime.fromisoformat(original["created_at"]).tzinfo, UTC)

        path = f"{PROGRAMS}/{original['id']}"
        found = self.client.get(path)
        self.assertEqual(found.status_code, 200)
        self.assertEqual(found.headers["ETag"], '"1"')
        self.assertEqual(found.get_json(), {"program": original})
        self.assertEqual(self.client.get(PROGRAMS).get_json(), {"items": [original], "next_cursor": None})

        changed = self.client.put(path, headers={"If-Match": '"1"'}, json={
            "name": "  Sample  ", "source": "40 + 2", "description": "Changed",
        })
        self.assertEqual(changed.status_code, 200)
        self.assertEqual(changed.headers["ETag"], '"2"')
        updated = changed.get_json()["program"]
        self.assertTrue(updated["updated_at"].endswith("Z"))
        self.assertGreaterEqual(datetime.fromisoformat(updated["updated_at"]), datetime.fromisoformat(original["updated_at"]))
        self.assertEqual(updated, original | {
            "source": "40 + 2", "description": "Changed", "revision": 2, "updated_at": updated["updated_at"],
        })
        removed = self.client.delete(path, headers={"If-Match": '"2"'})
        self.assertEqual(removed.status_code, 204)
        self.assertEqual(removed.data, b"")
        self.assertNotIn("ETag", removed.headers)
        self.assert_error(self.client.get(path), 404, "record_not_found")
        self.assertEqual(self.client.get(PROGRAMS).get_json(), {"items": [], "next_cursor": None})

    def test_content_type_malformed_json_and_body_limit(self):
        for content_type in (None, "text/plain", "application/problem+json"):
            with self.subTest(content_type=content_type):
                response = self.client.post(PROGRAMS, data=b"{}", content_type=content_type)
                self.assert_error(response, 415, "unsupported_media_type")
        for body in (b"", b"{", b"\xff", b'{"name": "Example", "source": NaN}'):
            with self.subTest(body=body):
                response = self.client.post(PROGRAMS, data=body, content_type="application/json")
                self.assert_error(response, 400, "invalid_request")
        valid_body = b'{"name":"Exact size","source":"1"}'
        exact = valid_body.ljust(262_144, b" ")
        oversized = self.client.post(PROGRAMS, data=exact + b" ", content_type="application/json")
        self.assert_error(oversized, 413, "request_too_large")
        accepted = self.client.post(PROGRAMS, data=exact, content_type="application/json; charset=utf-8")
        self.assertEqual(accepted.status_code, 201)

    def test_validation_rejects_invalid_fields_and_accepts_exact_field_limits(self):
        for payload in (
            [], {}, {"source": "1"}, {"name": "P"}, {"name": 10, "source": "1"},
            {"name": " \t ", "source": "1"}, {"name": "P", "source": 1},
            {"name": "P", "source": ""}, {"name": "P", "source": " \n"},
            {"name": "P", "source": "1", "description": None},
            {"name": "P", "source": "1", "description": "x" * 2_049},
            {"name": "P", "source": "\u00e9" * 8_193}, {"name": "P", "source": "\ud800"},
            {"name": "P", "source": "1", "revision": 1},
        ):
            with self.subTest(fields=list(payload)):
                self.assert_error(self.client.post(PROGRAMS, json=payload), 400, "invalid_request")
        self.assertEqual(self.client.get(PROGRAMS).get_json(), {"items": [], "next_cursor": None})
        program = self.create_program("P", "\u00e9" * 8_192, description="\u00e9" * 2_048)
        self.assertEqual(len(program["source"].encode("utf-8")), 16_384)
        self.assertEqual(len(program["description"]), 2_048)

    def test_trimmed_name_conflicts_are_case_sensitive_and_leave_state_unchanged(self):
        original = self.create_program(" P ")
        other = self.create_program("p")
        duplicate = self.client.post(PROGRAMS, json={"name": "P", "source": "1"})
        self.assert_error(duplicate, 409, "duplicate_name")
        path = f"{PROGRAMS}/{other['id']}"
        rejected = self.client.put(path, headers={"If-Match": '"1"'}, json={"name": "  P  ", "source": "updated"})
        self.assert_error(rejected, 409, "duplicate_name")
        bad_fields = self.client.put(path, headers={"If-Match": '"1"'}, json={"name": "p", "source": ""})
        self.assert_error(bad_fields, 400, "invalid_request")
        self.assertEqual(self.client.get(PROGRAMS).get_json()["items"], [original, other])

    def test_missing_malformed_and_stale_preconditions_leave_state_unchanged(self):
        data = {"name": "Example", "source": "2"}
        missing = f"{PROGRAMS}/unknown-id"
        self.assert_error(self.client.get(missing), 404, "record_not_found")
        for method in ("PUT", "DELETE"):
            for headers in ({}, {"If-Match": '"99"'}, {"If-Match": "*"}):
                self.assert_error(self.client.open(missing, method=method, headers=headers), 404, "record_not_found")

        original = self.create_program("Example")
        path = f"{PROGRAMS}/{original['id']}"
        self.assert_error(self.client.put(path), 428, "precondition_required")
        self.assert_error(self.client.delete(path), 428, "precondition_required")
        for tag in ('W/"1"', "*", '"1", "2"', "1", '"01"'):
            with self.subTest(tag=tag):
                rejected = self.client.put(path, headers={"If-Match": tag}, json=data)
                self.assert_error(rejected, 400, "invalid_request")

        updated = self.client.put(path, headers={"If-Match": '"1"'}, json=data).get_json()
        for method in ("PUT", "DELETE"):
            stale = self.client.open(path, method=method, headers={"If-Match": '"1"'}, json=data)
            self.assert_error(stale, 409, "revision_conflict", current_revision=2)
        self.assertEqual(self.client.get(path).get_json(), updated)

    def test_page_validation_and_cursor_replay(self):
        for name in ("Z", "B", "A"):
            self.create_program(name)
        for query in (
            "limit=0", "limit=51", "limit=abc", "limit=1.0", "limit=",
            "limit=1&limit=2", "cursor=", "cursor=unknown", "cursor=x&cursor=y", "unknown=1",
        ):
            with self.subTest(query=query):
                self.assert_error(self.client.get(f"{PROGRAMS}?{query}"), 400, "invalid_request")

        first = self.client.get(PROGRAMS, query_string={"limit": 2}).get_json()
        self.assertEqual([item["name"] for item in first["items"]], ["Z", "B"])
        token = first["next_cursor"]
        self.assertIsInstance(token, str)
        repeated = self.client.get(PROGRAMS, query_string={"limit": 2}).get_json()
        self.assertEqual(repeated, first)
        for query in ({"cursor": token}, {"cursor": token, "limit": 2}):
            last = self.client.get(PROGRAMS, query_string=query).get_json()
            self.assertEqual([item["name"] for item in last["items"]], ["A"])
            self.assertIsNone(last["next_cursor"])
        mismatch = self.client.get(PROGRAMS, query_string={"cursor": token, "limit": 1})
        self.assert_error(mismatch, 400, "invalid_request")

    def test_snapshot_pages_keep_updated_and_deleted_representations(self):
        first, old, removed = [self.create_program(name) for name in ("First", "Old", "Removed")]
        page = self.client.get(PROGRAMS, query_string={"limit": 1}).get_json()
        self.assertEqual(page["items"], [first])
        changed = self.client.put(f"{PROGRAMS}/{old['id']}", headers={"If-Match": '"1"'}, json={
            "name": "Changed", "source": "7", "description": "New description",
        }).get_json()["program"]
        self.assertEqual(self.client.delete(f"{PROGRAMS}/{removed['id']}", headers={"If-Match": '"1"'}).status_code, 204)
        added = self.create_program("Added")

        middle = self.client.get(PROGRAMS, query_string={"cursor": page["next_cursor"]}).get_json()
        self.assertEqual(middle["items"], [old])
        last = self.client.get(PROGRAMS, query_string={"cursor": middle["next_cursor"]}).get_json()
        self.assertEqual(last, {"items": [removed], "next_cursor": None})
        self.assertEqual(self.client.get(PROGRAMS).get_json(), {"items": [first, changed, added], "next_cursor": None})

        fresh_service = http.create_app().test_client()
        expired = fresh_service.get(PROGRAMS, query_string={"cursor": page["next_cursor"]})
        self.assert_error(expired, 400, "invalid_request")
        self.assertEqual(fresh_service.get(PROGRAMS).get_json(), {"items": [], "next_cursor": None})

    def test_default_page_size_and_capacity_recovery(self):
        records = [self.create_program(f"P {index}") for index in range(500)]
        full = self.client.post(PROGRAMS, json={"name": "One more", "source": "1"})
        self.assert_error(full, 409, "capacity_limit")
        page = self.client.get(PROGRAMS).get_json()
        self.assertEqual(page["items"], records[:50])
        second = self.client.get(PROGRAMS, query_string={"cursor": page["next_cursor"]}).get_json()
        self.assertEqual(second["items"], records[50:100])
        deleted = self.client.delete(f"{PROGRAMS}/{records[0]['id']}", headers={"If-Match": '"1"'})
        self.assertEqual(deleted.status_code, 204)
        self.create_program("One more")

    def test_concurrent_updates_recheck_revision_at_write_time(self):
        original = self.create_program("Concurrent")
        path = f"{PROGRAMS}/{original['id']}"
        both_passed_initial_check = Barrier(2)
        parse_program = http.program_write

        def wait_after_precondition(payload):
            both_passed_initial_check.wait(timeout=5)
            return parse_program(payload)

        def update(source):
            return self.app.test_client().put(path, headers={"If-Match": '"1"'}, json={
                "name": "Concurrent", "source": source,
            })

        with patch.object(http, "program_write", side_effect=wait_after_precondition):
            with ThreadPoolExecutor(max_workers=2) as workers:
                responses = list(workers.map(update, ["20", "21"]))
        winner, loser = sorted(responses, key=lambda response: response.status_code)
        self.assertEqual(winner.status_code, 200)
        self.assertEqual(winner.headers["ETag"], '"2"')
        self.assert_error(loser, 409, "revision_conflict", current_revision=2)
        saved = self.client.get(path).get_json()
        self.assertEqual(saved, winner.get_json())
        self.assertIn(saved["program"]["source"], {"20", "21"})

    def test_internal_error_is_json_and_does_not_expose_details(self):
        with patch.object(http, "program_write", side_effect=RuntimeError("private detail")):
            with self.assertLogs(self.app.logger, level="ERROR"):
                response = self.client.post(PROGRAMS, json={"name": "Example", "source": "1"})
        self.assert_error(response, 500, "internal_error")
        self.assertNotIn(b"private detail", response.data)
