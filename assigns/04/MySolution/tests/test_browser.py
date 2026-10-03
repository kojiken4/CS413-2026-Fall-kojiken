"""Opt-in real-browser smoke tests against an isolated loopback server."""

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("LAMBDA_BROWSER_TESTS") != "1",
    reason="Set LAMBDA_BROWSER_TESTS=1 to run the documented browser smoke tests.",
)
ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def page():
    from playwright.sync_api import sync_playwright, expect

    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    url = f"http://127.0.0.1:{port}"
    server = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "lambda_web.app:create_app", "--factory",
         "--host", "127.0.0.1", "--port", str(port), "--workers", "1"],
        cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
    )
    try:
        deadline = time.monotonic() + 10
        while True:
            try:
                httpx.get(url, timeout=1).raise_for_status()
                break
            except httpx.ConnectError:
                if time.monotonic() > deadline or server.poll() is not None:
                    raise
                time.sleep(0.05)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                channel=os.environ.get("LAMBDA_BROWSER_CHANNEL") or None,
            )
            try:
                context = browser.new_context()
                page = context.new_page()
                page.set_default_timeout(10000)
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(url)
                expect(page.get_by_label("Constructor expression")).to_be_editable()
                yield page
                assert errors == [], errors
            finally:
                browser.close()
    finally:
        server.terminate()
        server.communicate(timeout=10)


def edit_apply(page, source):
    from playwright.sync_api import expect

    page.get_by_label("Constructor expression").fill(source)
    page.get_by_role("button", name="Apply changes", exact=True).click()
    expect(page.get_by_role("button", name="Interpret", exact=True)).to_be_enabled()


def action(page, name):
    from playwright.sync_api import expect

    page.get_by_role("button", name=name, exact=True).click()
    expect(page.locator("#status")).to_have_text("Ready.")
    return page.locator(".result").last


def load(page, name):
    from playwright.sync_api import expect

    page.get_by_label("Load source", exact=True).select_option(name)
    page.get_by_role("button", name="Load source", exact=True).click()
    expect(page.locator("#status")).to_have_text("Ready.")


def test_keyboard_manual_editing_and_controls(page):
    from playwright.sync_api import expect

    assert page.locator("[data-operation]").all_text_contents() == [
        "Lint", "Interpret", "Type-check", "Compile", "Execute",
    ]
    for button in page.locator("[data-operation]").all():
        expect(button).to_be_disabled()
    page.get_by_label("Load source", exact=True).select_option("manual")
    page.get_by_role("button", name="Load source", exact=True).focus()
    page.keyboard.press("Enter")
    expect(page.get_by_label("Constructor expression")).to_be_focused()
    edit_apply(page, 'D0Eop2("+", D0Eint(20), D0Eint(22))')
    expect(page.locator("#source-info")).to_contain_text("Manual input · Revision 1")
    expect(action(page, "Interpret")).to_contain_text("D0Vint(arg1=42)")
    editor = page.get_by_label("Constructor expression")
    editor.fill("D0Eint(3)")
    expect(page.get_by_label("Load source", exact=True)).to_be_disabled()
    expect(page.get_by_role("button", name="Lint", exact=True)).to_be_disabled()
    page.get_by_role("button", name="Discard changes", exact=True).click()
    expect(editor).to_have_value('D0Eop2("+", D0Eint(20), D0Eint(22))')
    expect(page.locator(".result")).to_have_count(1)
    edit_apply(page, "D0Eint(3)")
    expect(page.locator("#source-info")).to_contain_text("Revision 2")
    expect(page.locator(".result")).to_have_count(0)


def test_canned_examples_lint_runtime_and_placeholders(page):
    from playwright.sync_api import expect

    for name, value in [("factorial", 120), ("fibonacci", 8)]:
        load(page, name)
        expect(action(page, "Lint")).to_contain_text("success")
        expect(action(page, "Interpret")).to_contain_text(f"D0Vint(arg1={value})")
    for name, output in [
        ("Type-check", "Type checking is not yet implemented"),
        ("Compile", "Compilation is not yet implemented"),
    ]:
        result = action(page, name)
        expect(result).to_contain_text("not_implemented")
        expect(result).to_contain_text(output)
    expect(page.get_by_role("button", name="Execute", exact=True)).to_be_disabled()
    expect(page.locator("#execute-help")).to_contain_text("generated code")
    edit_apply(page, 'D0Evar("x")')
    expect(action(page, "Lint")).to_contain_text("language_error")
    expect(page.locator(".result").last).to_contain_text("'x'")
    edit_apply(page, "D0Eint(42)")
    expect(action(page, "Lint")).to_contain_text("success")
    edit_apply(page, 'D0Eop2("/", D0Eint(1), D0Eint(0))')
    expect(action(page, "Lint")).to_contain_text("success")
    expect(action(page, "Interpret")).to_contain_text("runtime_error")
    edit_apply(page, "not a constructor")
    expect(action(page, "Interpret")).to_contain_text("invalid_input")


def test_upload_rejection_preserves_applied_source_and_correctable_edits(page):
    from playwright.sync_api import expect

    page.get_by_label("Load source", exact=True).select_option("file")
    with page.expect_file_chooser() as chooser:
        page.get_by_role("button", name="Load source", exact=True).click()
    chooser.value.set_files({"name": "local.txt", "mimeType": "text/plain", "buffer": b"D0Eint(7)"})
    expect(page.locator("#source-info")).to_have_text("local.txt · Revision 1")
    expect(action(page, "Interpret")).to_contain_text("D0Vint(arg1=7)")
    for raw, message in [(b"\xff", "valid UTF-8"), (b"x" * 65537, "exceeds")]:
        page.locator("#source-file").set_input_files(
            {"name": "rejected.txt", "mimeType": "text/plain", "buffer": raw}
        )
        expect(page.locator("#notice")).to_contain_text(message)
        expect(page.locator("#source-info")).to_have_text("local.txt · Revision 1")
        expect(page.get_by_label("Constructor expression")).to_have_value("D0Eint(7)")
        expect(page.locator(".result")).to_have_count(1)
    editor = page.get_by_label("Constructor expression")
    for source, message in [(" ", "must not be empty"), ("x" * 65537, "exceeds")]:
        editor.fill(source)
        page.get_by_role("button", name="Apply changes", exact=True).click()
        expect(page.locator("#notice")).to_contain_text(message)
        expect(editor).to_have_value(source)
        expect(page.locator("#source-info")).to_have_text("local.txt · Revision 1")
        expect(page.locator(".result")).to_have_count(1)
    page.get_by_role("button", name="Discard changes", exact=True).click()
    expect(editor).to_have_value("D0Eint(7)")
    page.locator("#source-file").set_input_files(
        {"name": "empty.txt", "mimeType": "text/plain", "buffer": b""}
    )
    expect(page.locator("#notice")).to_contain_text("must not be empty")
    expect(editor).to_have_value("")
    expect(page.locator("#source-info")).to_have_text("local.txt · Revision 1")
    edit_apply(page, "D0Eint(8)")
    expect(page.locator("#source-info")).to_have_text("empty.txt · Revision 2")


def test_source_and_multiline_output_are_literal(page):
    from playwright.sync_api import expect

    source = 'D0Evar("<img src=x onerror=window.injected=true>")'
    edit_apply(page, source)
    expect(page.get_by_label("Constructor expression")).to_have_value(source)
    expect(action(page, "Lint")).to_contain_text("<img src=x onerror=window.injected=true>")
    assert page.locator("#results img").count() == 0
    # Only inject the output transport for this rendering check; real tools are
    # exercised by the other browser tests and the preceding Lint request.
    payload = page.request.get(page.url + "api/state").json()
    result = {
        "operation": "interpret", "source_revision": payload["revision"],
        "outcome": "runtime_error", "output": "<script>window.injected=true</script>\nsecond line",
        "free_variables": None, "artifact": None,
    }
    payload["results"].append(result)
    page.route("**/api/actions/interpret", lambda route: route.fulfill(
        json={"state": payload, "result": result},
    ))
    output = action(page, "Interpret").locator("pre")
    assert output.text_content() == result["output"]
    assert page.locator("#results script").count() == 0
    assert page.evaluate("window.injected === undefined")
    page.set_viewport_size({"width": 390, "height": 844})
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")


def test_latest_typing_wins_over_delayed_draft_response(page):
    from playwright.sync_api import expect

    page.evaluate("""() => {
        const originalFetch = window.fetch;
        let first = true;
        window.fetch = async (...args) => {
            const response = await originalFetch(...args);
            if (args[0] === "/api/source/draft" && first) {
                first = false;
                await new Promise(resolve => { window.releaseDraft = resolve; });
            }
            return response;
        };
    }""")
    editor = page.get_by_label("Constructor expression")
    editor.fill("D0Eint(1)")
    expect(page.locator("#status")).to_have_text("Updating draft…")
    page.wait_for_function("typeof window.releaseDraft === 'function'")
    editor.fill("D0Eint(42)")
    page.evaluate("window.releaseDraft()")
    page.get_by_role("button", name="Apply changes", exact=True).click()
    expect(editor).to_have_value("D0Eint(42)")
    expect(page.get_by_role("button", name="Interpret", exact=True)).to_be_enabled()
    expect(action(page, "Interpret")).to_contain_text("D0Vint(arg1=42)")


def test_network_failure_keeps_draft_and_allows_retry(page):
    from playwright.sync_api import expect

    edit_apply(page, "D0Eint(1)")
    page.route("**/api/source/draft", lambda route: route.abort())
    editor = page.get_by_label("Constructor expression")
    editor.fill("D0Eint(42)")
    expect(page.locator("#notice")).to_contain_text("Unable to contact")
    expect(editor).to_have_value("D0Eint(42)")
    expect(page.get_by_role("button", name="Interpret", exact=True)).to_be_disabled()
    page.unroute("**/api/source/draft")
    page.get_by_role("button", name="Apply changes", exact=True).click()
    expect(action(page, "Interpret")).to_contain_text("D0Vint(arg1=42)")


def test_timeout_busy_controls_and_recovery(page):
    from playwright.sync_api import expect

    source = (ROOT / "samples/fibonacci.txt").read_text(encoding="utf-8")
    source = "D0Eint(40)".join(source.rsplit("D0Eint(6)", 1))
    edit_apply(page, source)
    page.get_by_role("button", name="Interpret", exact=True).click()
    expect(page.locator("#status")).to_contain_text("Busy: Interpret")
    expect(page.get_by_label("Constructor expression")).not_to_be_editable()
    for selector in ["#source-menu", "#load-source", "#apply-changes", "#discard-changes"]:
        expect(page.locator(selector)).to_be_disabled()
    for button in page.locator("[data-operation]").all():
        expect(button).to_be_disabled()
    # The browser can still read state while the server evaluates.
    assert page.request.get(page.url + "api/state").json()["busy"]
    expect(page.locator(".result")).to_contain_text("backend_failure", timeout=10000)
    expect(page.locator(".result")).to_contain_text("timed out")
    expect(page.get_by_label("Constructor expression")).to_be_editable()
    expect(page.get_by_label("Constructor expression")).to_have_value(source)
    edit_apply(page, "D0Eint(42)")
    expect(action(page, "Interpret")).to_contain_text("D0Vint(arg1=42)")
