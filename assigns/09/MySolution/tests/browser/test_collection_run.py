"""Exercise collection runs against the packaged Assign07 service."""

from multiprocessing import get_context

from playwright.sync_api import expect

from browser_support import StudioBrowserTestCase
from studio_storage.studio import create_app


def serve_lambda3(ready):
    from werkzeug.serving import make_server

    from runtime.assign07.MySolution.lambda_rpc.http import create_app as create_lambda3_app

    with make_server("127.0.0.1", 0, create_lambda3_app(), threaded=True) as server:
        with ready:
            ready.send(server.server_port)
        server.serve_forever()


def stop_lambda3(process):
    process.terminate()
    process.join(5)
    if process.is_alive():
        process.kill()
        process.join(5)
    process.close()


class CollectionRunTests(StudioBrowserTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        context = get_context("spawn")
        receive, send = context.Pipe(duplex=False)
        with receive, send:
            process = context.Process(target=serve_lambda3, args=(send,))
            process.start()
            cls.addClassCleanup(stop_lambda3, process)
            send.close()
            if not receive.poll(10):
                raise RuntimeError("The packaged LAMBDA3 service did not start.")
            cls.lambda3_port = receive.recv()

    def make_app(self):
        return create_app(lambda3_port=self.lambda3_port)

    def open_collection(self, page):
        page.get_by_role("link", name="Test collections", exact=True).click()
        page.get_by_label("Collection name").fill("Arithmetic")
        page.get_by_role("button", name="Create collection").click()
        expect(page.locator("#collection-status")).to_have_text("Saved · revision 1")

    def save_case(self, page, revision, name, source, *, outcome, value=None):
        page.get_by_role("button", name="Add case", exact=True).click()
        page.get_by_label("Case name").fill(name)
        page.get_by_label("Case source").fill(source)
        page.get_by_label("Expected outcome").select_option(outcome)
        if outcome == "value":
            page.get_by_label("Expected value", exact=True).fill(value)
        page.get_by_role("button", name="Save case", exact=True).click()
        expect(page.locator("#collection-status")).to_have_text(f"Saved · revision {revision}")

    def test_program_reload_and_real_collection_run_continues_after_failures(self):
        editor = self.page_in_new_context()
        editor.goto(self.url)
        editor.get_by_label("Name", exact=True).fill("Product")
        editor.get_by_label("LAMBDA source").fill("6 * 7")
        editor.get_by_role("button", name="Save program").click()
        expect(editor.locator("#save-status")).to_have_text("Saved · revision 1")

        page = self.page_in_new_context()
        page.goto(self.url)
        page.get_by_role("button", name="Product", exact=True).click()
        expect(page.get_by_label("LAMBDA source")).to_have_value("6 * 7")

        self.open_collection(page)
        self.save_case(page, 2, "Trailing space", "6 * 7", outcome="value", value="42 ")
        self.save_case(page, 3, "Unexpected failure", "1 / 0", outcome="syntax")
        self.save_case(page, 4, "Exact value", "6 * 7", outcome="value", value="42")
        self.save_case(page, 5, "Syntax category", "if then", outcome="syntax")
        self.save_case(page, 6, "Type category", "1 + true", outcome="type")
        page.get_by_role("button", name="Run collection", exact=True).click()

        expect(page.locator("#run-heading")).to_have_text("Arithmetic · revision 6")
        expect(page.locator("#run-status")).to_have_text("3 passed, 2 failed.")
        summaries = page.get_by_role("list", name="Case results").locator("summary")
        expect(summaries).to_have_text([
            "Fail · Trailing space",
            "Fail · Unexpected failure",
            "Pass · Exact value",
            "Pass · Syntax category",
            "Pass · Type category",
        ])

    def test_edit_during_run_keeps_original_case_source_and_id_on_result(self):
        page = self.page_in_new_context()
        page.goto(self.url)
        self.open_collection(page)
        self.save_case(page, 2, "Original", "6 * 7", outcome="value", value="42")
        response = page.request.get(f"{self.url}/api/v1/collections")
        original_case = response.json()["items"][0]["cases"][0]

        # Hold the real response in the browser until a newer revision has been saved.
        page.evaluate("""() => {
          const realFetch = window.fetch.bind(window);
          window.fetch = async (...args) => {
            const response = await realFetch(...args);
            if (args[0] === "/studio/interpret") {
              await new Promise((resolve) => { window.releaseCaseReply = resolve; });
            }
            return response;
          };
        }""")
        page.get_by_role("button", name="Run collection", exact=True).click()
        page.wait_for_function("typeof window.releaseCaseReply === 'function'")
        page.get_by_label("Case name").fill("Edited")
        page.get_by_label("Case source").fill("0")
        page.get_by_role("button", name="Save case").click()
        expect(page.locator("#collection-status")).to_have_text("Saved · revision 3")

        page.evaluate("window.releaseCaseReply()")
        expect(page.locator("#run-heading")).to_have_text("Arithmetic · revision 2")
        expect(page.locator("#run-status")).to_have_text("1 passed, 0 failed.")
        row = page.get_by_role("list", name="Case results").get_by_role("listitem")
        expect(row).to_have_attribute("data-case-id", original_case["id"])
        row.locator("summary").click()
        expect(row.locator("summary")).to_have_text("Pass · Original")
        expect(row.locator("pre")).to_have_text(original_case["source"])
        expect(page.get_by_label("Case source")).to_have_value("0")

    def test_transport_failure_is_not_an_expected_error_and_run_continues(self):
        page = self.page_in_new_context()
        page.goto(self.url)
        self.open_collection(page)
        self.save_case(page, 2, "Offline", "if then", outcome="syntax")
        self.save_case(page, 3, "After failure", "6 * 7", outcome="value", value="42")
        page.route("**/studio/interpret", lambda route: route.abort(), times=1)
        page.get_by_role("button", name="Run collection", exact=True).click()
        expect(page.locator("#run-status")).to_have_text("1 passed, 1 failed.")
        expect(page.locator("#run-results summary")).to_have_text(["Fail · Offline", "Pass · After failure"])
