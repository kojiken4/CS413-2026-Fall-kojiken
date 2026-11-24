"""Exercise collection and ordered case editing in an actual browser."""

from playwright.sync_api import expect

from browser_support import StudioBrowserTestCase


class CollectionEditorTests(StudioBrowserTestCase):
    def open_studio(self):
        page = self.page_in_new_context()
        page.goto(self.url)
        page.get_by_role("link", name="Test collections", exact=True).click()
        return page

    def create_collection(self, page, name):
        page.get_by_label("Collection name", exact=True).fill(name)
        page.get_by_role("button", name="Create collection", exact=True).click()
        self.expect_revision(page, 1)
        expect(page.locator("#collection-heading")).to_have_text(name.strip())

    def expect_revision(self, page, revision):
        expect(page.locator("#collection-status")).to_have_text(f"Saved · revision {revision}")

    def add_case(self, page, name, source, *, outcome, value=None):
        page.get_by_role("button", name="Add case", exact=True).click()
        page.get_by_label("Case name", exact=True).fill(name)
        page.get_by_label("Case source", exact=True).fill(source)
        page.get_by_label("Expected outcome", exact=True).select_option(outcome)
        expected_value = page.get_by_label("Expected value", exact=True)
        if outcome == "value":
            expected_value.fill(value)
        else:
            expect(expected_value).to_be_hidden()
        expect(page.locator("#collection-status")).to_have_text("Unsaved case changes")
        page.get_by_role("button", name="Save case", exact=True).click()

    def case_list(self, page):
        return page.get_by_role("list", name="Saved cases").get_by_role("button")

    def test_create_edit_delete_and_reopen_ordered_cases(self):
        page = self.open_studio()
        self.create_collection(page, " Arithmetic ")
        self.add_case(page, "Value", "6 * 7", outcome="value", value="42")
        self.expect_revision(page, 2)
        self.add_case(page, "Parse", "if then", outcome="syntax")
        self.expect_revision(page, 3)
        self.add_case(page, "Typing", "1 + true", outcome="type")
        self.expect_revision(page, 4)
        expect(self.case_list(page)).to_have_text(["Value", "Parse", "Typing"])

        page.get_by_role("button", name="Parse", exact=True).click()
        expect(page.get_by_label("Expected outcome")).to_have_value("syntax")
        page.get_by_label("Case name").fill("Parse error")
        page.get_by_label("Case description (optional)").fill("Saved note")
        page.get_by_role("button", name="Save case", exact=True).click()
        self.expect_revision(page, 5)
        expect(self.case_list(page)).to_have_text(["Value", "Parse error", "Typing"])

        page.get_by_role("button", name="Value", exact=True).click()
        expect(page.get_by_label("Expected value", exact=True)).to_have_value("42")
        page.once("dialog", lambda dialog: dialog.accept())
        page.get_by_role("button", name="Delete case", exact=True).click()
        self.expect_revision(page, 6)
        expect(self.case_list(page)).to_have_text(["Parse error", "Typing"])

        reopened = self.open_studio()
        reopened.get_by_role("button", name="Arithmetic", exact=True).click()
        self.expect_revision(reopened, 6)
        expect(self.case_list(reopened)).to_have_text(["Parse error", "Typing"])
        reopened.get_by_role("button", name="Parse error", exact=True).click()
        expect(reopened.get_by_label("Case source")).to_have_value("if then")
        expect(reopened.get_by_label("Case description (optional)")).to_have_value("Saved note")
        expect(reopened.get_by_label("Expected outcome")).to_have_value("syntax")

    def test_stale_case_save_preserves_draft_and_reloads_the_newer_case(self):
        stale = self.open_studio()
        self.create_collection(stale, "Arithmetic")
        self.add_case(stale, "Value", "6 * 7", outcome="value", value="42")
        self.expect_revision(stale, 2)

        other = self.open_studio()
        other.get_by_role("button", name="Arithmetic", exact=True).click()
        other.get_by_role("button", name="Value", exact=True).click()
        other.get_by_label("Case source").fill("40 + 2")
        other.get_by_role("button", name="Save case", exact=True).click()
        self.expect_revision(other, 3)

        stale.get_by_label("Case source").fill("21 * 2")
        stale.get_by_role("button", name="Save case", exact=True).click()
        expect(stale.get_by_role("alert")).to_contain_text("A newer collection revision is saved.")
        expect(stale.get_by_label("Case source")).to_have_value("21 * 2")
        expect(stale.locator("#collection-status")).to_have_text("Unsaved case changes")
        expect(stale.get_by_role("button", name="Save case")).to_be_disabled()
        stale.once("dialog", lambda dialog: dialog.accept())
        stale.get_by_role("button", name="Reload collection", exact=True).click()
        self.expect_revision(stale, 3)
        expect(stale.get_by_label("Case source")).to_have_value("40 + 2")
        expect(stale.get_by_role("alert")).to_have_count(0)

    def test_rejected_case_save_preserves_input_without_changing_order(self):
        page = self.open_studio()
        self.create_collection(page, "Arithmetic")
        self.add_case(page, "Value", "6 * 7", outcome="value", value="42")
        self.expect_revision(page, 2)
        self.add_case(page, "Value", "42", outcome="value", value="42")
        expect(page.get_by_role("alert")).to_contain_text("A case with that name already exists.")
        expect(page.get_by_label("Case source")).to_have_value("42")
        expect(self.case_list(page)).to_have_text(["Value"])
        expect(page.locator("#collection-status")).to_have_text("Unsaved case changes")
        page.get_by_label("Case name").fill("Second value")
        page.get_by_role("button", name="Save case", exact=True).click()
        self.expect_revision(page, 3)
        expect(self.case_list(page)).to_have_text(["Value", "Second value"])
