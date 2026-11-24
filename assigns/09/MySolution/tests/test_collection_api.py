"""Exercise collections and their case snapshots through HTTP."""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Barrier
from unittest import TestCase
from unittest.mock import patch

from studio_storage import http

COLLECTIONS = "/api/v1/collections"
PROGRAMS = "/api/v1/programs"
VALUE = {"kind": "value", "value": "42"}
SYNTAX = {"kind": "error", "category": "syntax"}
TYPE = {"kind": "error", "category": "type"}


def match_revision(revision):
    return {"If-Match": f'"{revision}"'}


def case_fields(name, source="6 * 7", expected=VALUE):
    return {"name": name, "source": source, "expected": expected}


class CollectionApiTests(TestCase):
    def setUp(self):
        self.app = http.create_app()
        self.client = self.app.test_client()

    def assert_error(self, response, status, code, *, current_revision=None):
        self.assertEqual(response.status_code, status, response.get_data(as_text=True))
        self.assertEqual(response.mimetype, "application/json")
        body = response.get_json()
        self.assertEqual(set(body), {"error"})
        error = body["error"]
        self.assertEqual(error["code"], code)
        self.assertTrue(error["message"])
        if current_revision is None:
            self.assertNotIn("current_revision", error)
        else:
            self.assertEqual(error["current_revision"], current_revision)

    def read_collection_response(self, response, *, status, revision):
        self.assertEqual(response.status_code, status, response.get_data(as_text=True))
        self.assertEqual(response.mimetype, "application/json")
        self.assertEqual(response.headers["ETag"], f'"{revision}"')
        body = response.get_json()
        self.assertEqual(set(body), {"collection"})
        self.assertEqual(body["collection"]["revision"], revision)
        return body["collection"]

    def create_collection(self, name, **fields):
        response = self.client.post(COLLECTIONS, json={"name": name, **fields})
        return self.read_collection_response(response, status=201, revision=1)

    def append_case(self, collection, name, source="6 * 7", expected=VALUE):
        path = f"{COLLECTIONS}/{collection['id']}/cases"
        revision = collection["revision"]
        response = self.client.post(path, headers=match_revision(revision), json=case_fields(name, source, expected))
        return self.read_collection_response(response, status=201, revision=revision + 1)

    def test_collection_crud_includes_cases_and_updates_only_metadata(self):
        collection = self.create_collection("  Arithmetic  ", description="Initial description")
        self.assertEqual(set(collection), {
            "id", "name", "description", "created_at", "updated_at", "revision", "cases",
        })
        self.assertIsInstance(collection["id"], str)
        self.assertTrue(collection["id"])
        self.assertEqual(collection["name"], "Arithmetic")
        self.assertEqual(collection["cases"], [])
        self.assertEqual(collection["created_at"], collection["updated_at"])
        self.assertTrue(collection["created_at"].endswith("Z"))
        self.assertEqual(datetime.fromisoformat(collection["created_at"]).tzinfo, UTC)

        path = f"{COLLECTIONS}/{collection['id']}"
        collection = self.append_case(collection, "First")
        collection = self.append_case(collection, "Second", "if then", SYNTAX)
        fetched = self.read_collection_response(self.client.get(path), status=200, revision=3)
        self.assertEqual(fetched, collection)
        listing = self.client.get(COLLECTIONS)
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.mimetype, "application/json")
        self.assertEqual(listing.get_json(), {"items": [collection], "next_cursor": None})

        response = self.client.put(path, headers=match_revision(3), json={"name": "  Updated  "})
        changed = self.read_collection_response(response, status=200, revision=4)
        self.assertGreaterEqual(
            datetime.fromisoformat(changed["updated_at"]), datetime.fromisoformat(collection["updated_at"]),
        )
        self.assertEqual(changed, collection | {
            "name": "Updated", "description": "", "revision": 4, "updated_at": changed["updated_at"],
        })
        removed = self.client.delete(path, headers=match_revision(4))
        self.assertEqual(removed.status_code, 204)
        self.assertEqual(removed.data, b"")
        self.assertNotIn("ETag", removed.headers)
        self.assert_error(self.client.get(path), 404, "record_not_found")
        self.assertEqual(self.client.get(COLLECTIONS).get_json(), {"items": [], "next_cursor": None})

    def test_case_mutations_keep_ids_and_order_and_advance_the_parent_revision(self):
        collection = self.create_collection("Cases")
        collection = self.append_case(collection, "First", "1 + true", TYPE)
        collection = self.append_case(collection, "Second")
        collection = self.append_case(collection, "Third", "if then", SYNTAX)
        first, second, third = collection["cases"]
        self.assertEqual(first["expected"], TYPE)
        self.assertEqual(third["expected"], SYNTAX)
        self.assertEqual(len({case["id"] for case in collection["cases"]}), 3)
        self.assertTrue(all(isinstance(case["id"], str) and case["id"] for case in collection["cases"]))

        path = f"{COLLECTIONS}/{collection['id']}"
        fields = case_fields("  Second  ", "\n40 + 2  ", VALUE) | {"description": "Revised"}
        response = self.client.put(f"{path}/cases/{second['id']}", headers=match_revision(4), json=fields)
        updated = self.read_collection_response(response, status=200, revision=5)
        self.assertEqual(updated["cases"], [first, {
            "id": second["id"], "name": "Second", "source": "\n40 + 2  ",
            "description": "Revised", "expected": VALUE,
        }, third])

        response = self.client.delete(f"{path}/cases/{second['id']}", headers=match_revision(5))
        updated = self.read_collection_response(response, status=200, revision=6)
        self.assertEqual(updated["cases"], [first, third])
        already_deleted = self.client.delete(f"{path}/cases/{second['id']}", headers=match_revision(6))
        self.assert_error(already_deleted, 404, "record_not_found")
        self.assertEqual(self.client.get(path).get_json(), {"collection": updated})

    def test_validation_rejects_invalid_collection_case_and_expectation_fields(self):
        for payload in ([], {}, {"name": 7}, {"name": " \t"}, {"name": "C", "description": None},
                        {"name": "C", "description": "a" * 2049}, {"name": "C", "cases": []}):
            with self.subTest(payload=type(payload).__name__, keys=list(payload)):
                self.assert_error(self.client.post(COLLECTIONS, json=payload), 400, "invalid_request")
        collection = self.create_collection("Cases", description="x" * 2048)
        path = f"{COLLECTIONS}/{collection['id']}"
        invalid_cases = [
            {},
            {"name": "Test", "source": "1"},
            case_fields("  "),
            case_fields("Test", ""),
            case_fields("Test", 42),
            case_fields("Test", "\u00e9" * 8193),
            case_fields("Test") | {"description": "x" * 2049},
            case_fields("Test") | {"id": "client-id"},
        ]
        for expected in (
            None, [], {}, {"kind": "other", "value": "42"}, {"kind": "value", "value": 42},
            {"kind": "value", "value": "42", "category": "type"}, {"kind": "error"},
            {"kind": "error", "category": "transport"}, {"kind": "error", "value": "42"},
        ):
            invalid_cases.append(case_fields("Test", expected=expected))
        for payload in invalid_cases:
            response = self.client.post(f"{path}/cases", json=payload, headers=match_revision(1))
            self.assert_error(response, 400, "invalid_request")
        response = self.client.put(path, json={"name": "Cases", "revision": 2}, headers=match_revision(1))
        self.assert_error(response, 400, "invalid_request")
        self.assertEqual(self.client.get(path).get_json(), {"collection": collection})
        accepted = self.append_case(collection, "Test", "\u00e9" * 8192, {"kind": "value", "value": ""})
        self.assertEqual(accepted["cases"][0]["expected"], {"kind": "value", "value": ""})

    def test_trimmed_names_are_unique_only_inside_their_scope(self):
        program = self.client.post(PROGRAMS, json={"name": "Shared", "source": "42"})
        self.assertEqual(program.status_code, 201)
        first = self.create_collection(" Shared ")
        second = self.create_collection("shared")
        duplicate = self.client.post(COLLECTIONS, json={"name": "Shared"})
        self.assert_error(duplicate, 409, "duplicate_name")
        second_path = f"{COLLECTIONS}/{second['id']}"
        duplicate = self.client.put(second_path, json={"name": " Shared "}, headers=match_revision(1))
        self.assert_error(duplicate, 409, "duplicate_name")

        first = self.append_case(first, " Shared ")
        first = self.append_case(first, "shared")
        second = self.append_case(second, "Shared")
        first_path = f"{COLLECTIONS}/{first['id']}"
        duplicate = self.client.post(
            f"{first_path}/cases", json=case_fields("Shared"), headers=match_revision(3),
        )
        self.assert_error(duplicate, 409, "duplicate_name")
        second_case_id = first["cases"][1]["id"]
        duplicate = self.client.put(
            f"{first_path}/cases/{second_case_id}", json=case_fields(" Shared "), headers=match_revision(3),
        )
        self.assert_error(duplicate, 409, "duplicate_name")
        self.assertEqual(self.client.get(first_path).get_json(), {"collection": first})
        self.assertEqual(self.client.get(second_path).get_json(), {"collection": second})

    def test_conditional_failures_leave_the_collection_unchanged(self):
        collection = self.append_case(self.create_collection("Cases"), "First")
        original = collection
        other = self.append_case(self.create_collection("Other collection"), "Other")
        path = f"{COLLECTIONS}/{collection['id']}"
        case_path = f"{path}/cases/{collection['cases'][0]['id']}"
        foreign_case = f"{path}/cases/{other['cases'][0]['id']}"

        for method, target in (
            ("PUT", path), ("DELETE", path), ("POST", f"{path}/cases"),
            ("PUT", case_path), ("DELETE", case_path),
        ):
            with self.subTest(method=method, target=target):
                self.assert_error(self.client.open(target, method=method), 428, "precondition_required")
                stale = self.client.open(target, method=method, headers=match_revision(1))
                self.assert_error(stale, 409, "revision_conflict", current_revision=2)
                invalid = self.client.open(target, method=method, headers={"If-Match": 'W/"2"'})
                self.assert_error(invalid, 400, "invalid_request")

        for headers in ({}, match_revision(1), {"If-Match": "*"}):
            for method in ("PUT", "DELETE"):
                missing = self.client.open(f"{COLLECTIONS}/missing", method=method, headers=headers)
                self.assert_error(missing, 404, "record_not_found")
                missing = self.client.open(f"{path}/cases/missing", method=method, headers=headers)
                self.assert_error(missing, 404, "record_not_found")
            missing = self.client.post(f"{COLLECTIONS}/missing/cases", headers=headers)
            self.assert_error(missing, 404, "record_not_found")
        self.assert_error(self.client.delete(foreign_case, headers=match_revision(2)), 404, "record_not_found")

        bad_edit = self.client.put(case_path, json=case_fields("Changed", expected={}), headers=match_revision(2))
        self.assert_error(bad_edit, 400, "invalid_request")
        wrong_media = self.client.put(
            case_path, data=b"{}", content_type="text/plain", headers=match_revision(2),
        )
        self.assert_error(wrong_media, 415, "unsupported_media_type")
        oversized = self.client.post(
            f"{path}/cases", data=b" " * 262_145, content_type="application/json", headers=match_revision(2),
        )
        self.assert_error(oversized, 413, "request_too_large")
        self.assertEqual(self.client.get(path).get_json(), {"collection": original})

    def test_collection_cursor_retains_old_case_contents_and_excludes_new_records(self):
        first = self.create_collection("Z")
        old = self.append_case(self.create_collection("B"), "Original")
        deleted = self.append_case(self.create_collection("A"), "Removed")
        initial = self.client.get(COLLECTIONS, query_string={"limit": 1}).get_json()
        self.assertEqual(initial["items"], [first])

        old_id, old_case_id = old["id"], old["cases"][0]["id"]
        response = self.client.put(
            f"{COLLECTIONS}/{old_id}/cases/{old_case_id}",
            json=case_fields("Updated", "1 + true", TYPE), headers=match_revision(2),
        )
        updated = self.read_collection_response(response, status=200, revision=3)
        self.assertEqual(self.client.delete(
            f"{COLLECTIONS}/{deleted['id']}", headers=match_revision(2),
        ).status_code, 204)
        added = self.create_collection("New")

        middle = self.client.get(COLLECTIONS, query_string={"cursor": initial["next_cursor"]}).get_json()
        self.assertEqual(middle["items"], [old])
        last = self.client.get(COLLECTIONS, query_string={"cursor": middle["next_cursor"]}).get_json()
        self.assertEqual(last, {"items": [deleted], "next_cursor": None})
        self.assertEqual(self.client.get(COLLECTIONS).get_json(), {
            "items": [first, updated, added], "next_cursor": None,
        })

        for name in ("P1", "P2"):
            self.assertEqual(self.client.post(PROGRAMS, json={"name": name, "source": "42"}).status_code, 201)
        programs = self.client.get(PROGRAMS, query_string={"limit": 1}).get_json()
        wrong_resource = self.client.get(COLLECTIONS, query_string={"cursor": programs["next_cursor"]})
        self.assert_error(wrong_resource, 400, "invalid_request")
        wrong_resource = self.client.get(PROGRAMS, query_string={"cursor": initial["next_cursor"]})
        self.assert_error(wrong_resource, 400, "invalid_request")

    def test_program_edits_and_deletion_leave_saved_case_source_unchanged(self):
        response = self.client.post(PROGRAMS, json={"name": "Source", "source": "6 * 7"})
        self.assertEqual(response.status_code, 201)
        program = response.get_json()["program"]
        collection = self.append_case(self.create_collection("Snapshots"), "Original", program["source"])
        program_path = f"{PROGRAMS}/{program['id']}"
        collection_path = f"{COLLECTIONS}/{collection['id']}"
        changed = self.client.put(program_path, headers=match_revision(1), json={"name": "Source", "source": "0"})
        self.assertEqual(changed.status_code, 200)
        self.assertEqual(self.client.get(collection_path).get_json(), {"collection": collection})
        self.assertEqual(self.client.delete(program_path, headers=match_revision(2)).status_code, 204)
        self.assertEqual(self.client.get(collection_path).get_json(), {"collection": collection})

    def test_case_limit_and_capacity_recovery(self):
        collection = self.create_collection("Cases")
        for index in range(50):
            collection = self.append_case(collection, f"Case {index}")
        path = f"{COLLECTIONS}/{collection['id']}"
        over_limit = self.client.post(f"{path}/cases", json=case_fields("Extra"), headers=match_revision(51))
        self.assert_error(over_limit, 409, "capacity_limit")
        self.assertEqual(self.client.get(path).get_json(), {"collection": collection})
        first_id = collection["cases"][0]["id"]
        deleted = self.client.delete(f"{path}/cases/{first_id}", headers=match_revision(51))
        current = self.read_collection_response(deleted, status=200, revision=52)
        current = self.append_case(current, "Extra")
        self.assertEqual(len(current["cases"]), 50)
        self.assertEqual(current["cases"][-1]["name"], "Extra")

    def test_global_capacity_counts_cases_and_collection_deletion_frees_them(self):
        collection = self.append_case(self.create_collection("Cases"), "First")
        collection = self.append_case(collection, "Second")
        for index in range(497):
            response = self.client.post(PROGRAMS, json={"name": f"P{index}", "source": "42"})
            self.assertEqual(response.status_code, 201)
        path = f"{COLLECTIONS}/{collection['id']}"
        for response in (
            self.client.post(COLLECTIONS, json={"name": "Extra"}),
            self.client.post(PROGRAMS, json={"name": "Extra", "source": "42"}),
            self.client.post(f"{path}/cases", json=case_fields("Extra"), headers=match_revision(3)),
        ):
            self.assert_error(response, 409, "capacity_limit")
        self.assertEqual(self.client.get(path).get_json(), {"collection": collection})

        self.assertEqual(self.client.delete(path, headers=match_revision(3)).status_code, 204)
        for case in collection["cases"]:
            response = self.client.delete(f"{path}/cases/{case['id']}", headers=match_revision(3))
            self.assert_error(response, 404, "record_not_found")
        replacement = self.create_collection("Cases")
        self.assertNotEqual(replacement["id"], collection["id"])
        self.assertEqual(replacement["cases"], [])
        replacement = self.append_case(replacement, "First")
        self.append_case(replacement, "Second")
        self.assert_error(self.client.post(COLLECTIONS, json={"name": "Extra"}), 409, "capacity_limit")

    def test_concurrent_case_append_and_metadata_edit_share_the_parent_revision(self):
        collection = self.create_collection("Original")
        path = f"{COLLECTIONS}/{collection['id']}"
        parse_json = http._read_json
        both_passed_initial_check = Barrier(2)

        def wait_before_reading():
            both_passed_initial_check.wait(timeout=5)
            return parse_json()

        def update(request):
            method, target, payload = request
            return self.app.test_client().open(target, method=method, json=payload, headers=match_revision(1))

        with patch.object(http, "_read_json", side_effect=wait_before_reading):
            with ThreadPoolExecutor(max_workers=2) as workers:
                responses = list(workers.map(update, [
                    ("PUT", path, {"name": "Renamed"}),
                    ("POST", f"{path}/cases", case_fields("First")),
                ]))
        winner, loser = sorted(responses, key=lambda response: response.status_code)
        self.assertIn(winner.status_code, {200, 201})
        self.assert_error(loser, 409, "revision_conflict", current_revision=2)
        stored = self.read_collection_response(self.client.get(path), status=200, revision=2)
        self.assertEqual({"collection": stored}, winner.get_json())
        if winner.status_code == 200:
            self.assertEqual(stored["name"], "Renamed")
            self.assertEqual(stored["cases"], [])
        else:
            self.assertEqual(stored["name"], "Original")
            self.assertEqual([case["name"] for case in stored["cases"]], ["First"])
