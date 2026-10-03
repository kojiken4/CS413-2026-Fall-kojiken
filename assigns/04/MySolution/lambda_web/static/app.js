"use strict";

const editor = document.getElementById("source-editor");
const menu = document.getElementById("source-menu");
const loadButton = document.getElementById("load-source");
const fileInput = document.getElementById("source-file");
const applyButton = document.getElementById("apply-changes");
const discardButton = document.getElementById("discard-changes");
const actionButtons = [...document.querySelectorAll("[data-operation]")];
const labels = { lint: "Lint", interpret: "Interpret", typecheck: "Type-check", compile: "Compile", execute: "Execute" };
let state = null;
let pending = false;
let pendingLabel = "";
let draftVersion = 0;
let savedVersion = 0;
let draftTask = null;
let pollTimer = null;
let renderedResults = "";

function showError(error) {
  document.getElementById("notice").textContent = error.message;
}

async function request(path, body, method = "POST") {
  const options = { method };
  if (body instanceof FormData) {
    options.body = body;
  } else if (body !== undefined) {
    options.headers = { "Content-Type": "application/json" };
    options.body = JSON.stringify(body);
  }
  let response, data;
  try {
    response = await fetch(path, options);
    data = await response.json();
  } catch {
    throw new Error("Unable to contact the application. Your editor text is preserved; check the server and try again.");
  }
  if (!response.ok) {
    const error = new Error(data.detail || "The request could not be completed.");
    error.state = data.state;
    throw error;
  }
  return data;
}

function acceptState(next, replaceDraft = false) {
  state = next;
  if (replaceDraft) {
    editor.value = state.draft;
    savedVersion = draftVersion;
  }
  render();
}

function render() {
  const locked = pending || !state || state.busy;
  const dirty = state ? editor.value !== (state.applied_source || "") : false;
  const unsynced = draftVersion !== savedVersion;
  editor.readOnly = Boolean(locked);
  menu.disabled = loadButton.disabled = fileInput.disabled = Boolean(locked || dirty || unsynced);
  applyButton.disabled = Boolean(locked || (!dirty && state.applied_source !== null));
  discardButton.disabled = Boolean(locked || (!dirty && !unsynced));
  for (const button of actionButtons) {
    button.disabled = Boolean(locked || dirty || unsynced || !state.enabled_actions[button.dataset.operation]);
  }
  if (!state) return;
  document.getElementById("source-info").textContent =
    (state.source_name || "No applied source") + " · Revision " + state.revision;
  document.getElementById("edit-status").textContent = dirty
    ? "Unapplied changes in " + state.draft_name + ". Apply or discard before running tools or loading another source."
    : state.applied_source === null ? "Enter source and apply it to enable tools." : "No unapplied changes.";
  document.getElementById("status").textContent = pending ? pendingLabel
    : state.busy ? "Busy: " + labels[state.active_operation] + ". Waiting for completion."
    : unsynced ? "Updating draft…"
    : dirty ? "Unapplied changes." : "Ready.";
  document.getElementById("results-section").setAttribute("aria-busy", String(pending || state.busy));
  // Rebuild only changed results, preserving selection during draft updates.
  const resultKey = JSON.stringify([state.revision, state.results]);
  if (resultKey !== renderedResults) {
    renderedResults = resultKey;
    const container = document.getElementById("results");
    container.replaceChildren();
    if (!state.results.length) {
      const empty = document.createElement("p");
      empty.textContent = "No results for this revision.";
      container.append(empty);
    }
    for (const result of state.results) {
      const article = document.createElement("article");
      article.className = "result";
      const heading = document.createElement("h3");
      heading.textContent = labels[result.operation] + " · Revision " + result.source_revision + " · " + result.outcome;
      const output = document.createElement("pre");
      output.textContent = result.output;
      article.append(heading, output);
      container.append(article);
    }
  }
}

function syncDraft() {
  if (draftTask) return draftTask;
  draftTask = (async () => {
    while (savedVersion !== draftVersion) {
      const version = draftVersion;
      const text = editor.value;
      try {
        const next = await request("/api/source/draft", { source: text });
        savedVersion = version;
        // Keep newer typing even if this response describes an older draft.
        acceptState(next);
      } catch (error) {
        if (error.state) acceptState(error.state);
        error.preserveDraft = true;
        throw error;
      }
    }
  })().finally(() => { draftTask = null; render(); });
  return draftTask;
}

async function refreshState(replaceDraft = false) {
  acceptState(await request("/api/state", undefined, "GET"), replaceDraft);
}

function pollBusy() {
  clearTimeout(pollTimer);
  if (!state || !state.busy || pending) return;
  pollTimer = setTimeout(async () => {
    try { await refreshState(); } catch (error) { showError(error); }
    pollBusy();
  }, 300);
}

async function run(path, body, message, focusEditor = false) {
  if (pending || !state || state.busy) return;
  pending = true;
  pendingLabel = message;
  document.getElementById("notice").textContent = "";
  render();
  try {
    await syncDraft();
    const data = await request(path, body);
    acceptState(data.state || data, true);
    if (focusEditor) editor.focus();
  } catch (error) {
    if (error.state) acceptState(error.state, !error.preserveDraft);
    else {
      // A lost action response does not imply that the server stopped working.
      try { await refreshState(); } catch { /* Keep the last known state and local text. */ }
    }
    showError(error);
  } finally {
    pending = false;
    render();
    pollBusy();
  }
}

editor.addEventListener("input", () => {
  draftVersion += 1;
  document.getElementById("notice").textContent = "";
  render();
  syncDraft().catch(showError);
});
applyButton.addEventListener("click", () => run("/api/source/apply", undefined, "Applying changes…"));
discardButton.addEventListener("click", () => run("/api/source/discard", undefined, "Discarding changes…", true));
loadButton.addEventListener("click", () => {
  if (menu.value === "file") fileInput.click();
  else if (menu.value === "manual") run("/api/source/manual", undefined, "Opening manual input…", true);
  else run("/api/source/canned", { name: menu.value }, "Loading example…", true);
});
fileInput.addEventListener("change", () => {
  const file = fileInput.files[0];
  if (!file) return;
  const body = new FormData();
  body.append("file", file);
  run("/api/source/upload", body, "Loading file…", true);
  fileInput.value = "";
});
for (const button of actionButtons) {
  button.addEventListener("click", () =>
    run("/api/actions/" + button.dataset.operation, undefined, "Busy: " + labels[button.dataset.operation] + "…"));
}

refreshState(true).then(pollBusy).catch(showError);
