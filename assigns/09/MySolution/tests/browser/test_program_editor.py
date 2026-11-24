"""Run with python -m unittest discover -s tests/browser -v after installing Chromium."""

import os
from threading import Thread
from unittest import TestCase

from playwright.sync_api import expect, sync_playwright
from werkzeug.serving import make_server

from studio_storage.studio import create_app


class ProgramEditorTests(TestCase):
    @classmethod
    def setUpClass(cls):
        playwright = sync_playwright().start()
        cls.addClassCleanup(playwright.stop)
        cls.browser = playwright.chromium.launch(channel=os.environ.get("ASSIGN09_BROWSER_CHANNEL"))
        cls.addClassCleanup(cls.browser.close)

    def setUp(self):
        server = make_server("127.0.0.1", 0, create_app(), threaded=True)
        worker = Thread(target=server.serve_forever, name="studio-test-server", daemon=True)
        worker.start()
        self.addCleanup(server.server_close)
        self.addCleanup(worker.join, 5)
        self.addCleanup(server.shutdown)
        self.url = f"http://127.0.0.1:{server.server_port}"
        self.errors = []
        self.addCleanup(self.assertEqual, self.errors, [])

    def page_in_new_context(self):
        context = self.browser.new_context()
        self.addCleanup(context.close)
        page = context.new_page()
        page.on("pageerror", lambda error: self.errors.append(str(error)))
        return page

    def fill_program(self, page, name, source):
        page.get_by_label("Name", exact=True).fill(name)
        page.get_by_label("LAMBDA source").fill(source)

    def save_program(self, page):
        page.get_by_role("button", name="Save program", exact=True).click()

    def expect_status(self, page, text):
        expect(page.locator("#save-status")).to_have_text(text)

    def test_save_reopen_and_reload_after_a_conflict(self):
        editor = self.page_in_new_context()
        editor.goto(self.url)
        expect(editor.get_by_text("Saved data is cleared when the storage service stops.")).to_be_visible()
        expect(editor.get_by_text("No programs saved yet.")).to_be_visible()
        self.fill_program(editor, "Arithmetic", "6 * 7")
        self.expect_status(editor, "Unsaved changes")
        self.save_program(editor)
        self.expect_status(editor, "Saved · revision 1")

        reopened = self.page_in_new_context()
        reopened.goto(self.url)
        reopened.get_by_role("button", name="Arithmetic", exact=True).click()
        expect(reopened.get_by_label("LAMBDA source")).to_have_value("6 * 7")
        self.expect_status(reopened, "Saved · revision 1")

        other_tab = reopened.context.new_page()
        other_tab.on("pageerror", lambda error: self.errors.append(str(error)))
        other_tab.goto(self.url)
        other_tab.get_by_role("button", name="Arithmetic", exact=True).click()
        other_tab.get_by_label("LAMBDA source").fill("40 + 2")
        self.save_program(other_tab)
        self.expect_status(other_tab, "Saved · revision 2")

        reopened.get_by_label("LAMBDA source").fill("21 * 2")
        self.save_program(reopened)
        expect(reopened.get_by_role("alert").filter(has_text="A newer version is saved")).to_be_visible()
        expect(reopened.get_by_label("LAMBDA source")).to_have_value("21 * 2")
        self.expect_status(reopened, "Unsaved changes")
        expect(reopened.get_by_role("button", name="Save program")).to_be_disabled()
        reopened.get_by_role("button", name="Reload server copy").click()
        self.expect_status(reopened, "Saved · revision 2")
        expect(reopened.get_by_label("LAMBDA source")).to_have_value("40 + 2")
        expect(reopened.get_by_role("button", name="Reload server copy")).to_be_hidden()

    def test_validation_and_network_failure_preserve_the_draft(self):
        page = self.page_in_new_context()
        page.goto(self.url)
        self.fill_program(page, "  ", "1")
        self.save_program(page)
        expect(page.get_by_role("alert")).to_have_text("Enter a program name.")
        self.expect_status(page, "Unsaved changes")

        self.fill_program(page, "Example", "1")
        page.route("**/api/v1/programs", lambda route: route.abort())
        self.save_program(page)
        expect(page.get_by_role("alert")).to_contain_text("Could not reach the storage service.")
        self.expect_status(page, "Unsaved changes")
        expect(page.get_by_label("LAMBDA source")).to_have_value("1")

        page.unroute("**/api/v1/programs")
        self.save_program(page)
        self.expect_status(page, "Saved · revision 1")
        page.get_by_role("button", name="New program").click()
        self.fill_program(page, "Example", "2")
        self.save_program(page)
        expect(page.get_by_role("alert")).to_contain_text("A program with that name already exists.")
        self.expect_status(page, "Unsaved changes")
        expect(page.get_by_label("LAMBDA source")).to_have_value("2")

    def test_list_follows_cursors_and_metadata_edits_preserve_stored_source(self):
        page = self.page_in_new_context()
        api = f"{self.url}/api/v1/programs"
        for index in range(50):
            created = page.request.post(api, data={"name": f"Program {index:02}", "source": "1"})
            self.assertEqual(created.status, 201)
        created = page.request.post(api, data={"name": "Last program", "source": "1\r\n"})
        self.assertEqual(created.status, 201)
        program_id = created.json()["program"]["id"]

        page.goto(self.url)
        page.get_by_role("button", name="Last program", exact=True).click()
        self.expect_status(page, "Saved · revision 1")
        expect(page.get_by_label("LAMBDA source")).to_have_value("1\n")
        page.get_by_label("Description (optional)").fill("Reviewed")
        self.save_program(page)
        self.expect_status(page, "Saved · revision 2")
        saved = page.request.get(f"{api}/{program_id}").json()["program"]
        self.assertEqual(saved["source"], "1\r\n")
        self.assertEqual(saved["description"], "Reviewed")
