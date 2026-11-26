"""Run studio browser tests with a fresh loopback storage service per test."""

import os
from threading import Thread
from unittest import TestCase

from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server

from studio_storage.studio import create_app


class StudioBrowserTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        playwright = sync_playwright().start()
        cls.addClassCleanup(playwright.stop)
        cls.browser = playwright.chromium.launch(channel=os.environ.get("ASSIGN09_BROWSER_CHANNEL"))
        cls.addClassCleanup(cls.browser.close)

    def setUp(self):
        server = make_server("127.0.0.1", 0, self.make_app(), threaded=True)
        worker = Thread(target=server.serve_forever, name="studio-test-server", daemon=True)
        worker.start()
        self.addCleanup(server.server_close)
        self.addCleanup(worker.join, 5)
        self.addCleanup(server.shutdown)
        self.url = f"http://127.0.0.1:{server.server_port}"
        self.errors = []
        self.addCleanup(self.assertEqual, self.errors, [])

    def make_app(self):
        return create_app()

    def page_in_new_context(self):
        context = self.browser.new_context()
        self.addCleanup(context.close)
        page = context.new_page()
        page.on("pageerror", lambda error: self.errors.append(str(error)))
        return page
