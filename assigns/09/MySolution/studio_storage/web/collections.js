import { appendCase, createCollection, deleteCase, getCollection, listCollections, StorageError, updateCase } from "./storage.js";

const collectionForm = document.querySelector("#collection-form");
const collectionName = collectionForm.elements.name;
const createButton = document.querySelector("#create-collection");
const refreshButton = document.querySelector("#refresh-collections");
const collectionList = document.querySelector("#collection-list");
const listStatus = document.querySelector("#collection-list-status");
const libraryError = document.querySelector("#collection-library-error");
const heading = document.querySelector("#collection-heading");
const status = document.querySelector("#collection-status");
const placeholder = document.querySelector("#collection-placeholder");
const content = document.querySelector("#collection-content");
const conflictNotice = document.querySelector("#collection-conflict");
const caseError = document.querySelector("#case-error");
const addButton = document.querySelector("#add-case");
const reloadButton = document.querySelector("#reload-collection");
const caseList = document.querySelector("#case-list");
const caseListStatus = document.querySelector("#case-list-status");
const caseForm = document.querySelector("#case-form");
const caseFields = document.querySelector("#case-fields");
const caseHeading = document.querySelector("#case-form-heading");
const expectedValueField = document.querySelector("#expected-value-field");
const saveButton = document.querySelector("#save-case");
const deleteButton = document.querySelector("#delete-case");
const { name, source, outcome, expectedValue, description } = caseForm.elements;

let collections = [];
let saved = null;
let editingCase = null;
let baseline = readDraft();
let busy = false;
let conflict = false;

function readDraft() {
  return {
    name: name.value,
    source: source.value,
    outcome: outcome.value,
    expectedValue: outcome.value === "value" ? expectedValue.value : "",
    description: description.value,
  };
}

function hasUnsavedEdits() {
  if (caseForm.hidden) return false;
  const draft = readDraft();
  return Object.keys(draft).some((key) => draft[key] !== baseline[key]);
}

function savedCaseFields(draft) {
  // Text controls normalize line endings. Reuse the stored text for untouched fields.
  const fields = {};
  for (const key of ["name", "source", "description"]) {
    fields[key] = editingCase && draft[key] === baseline[key] ? editingCase[key] : draft[key];
  }
  if (draft.outcome === "value") {
    const unchanged = editingCase?.expected.kind === "value" && draft.expectedValue === baseline.expectedValue;
    fields.expected = { kind: "value", value: unchanged ? editingCase.expected.value : draft.expectedValue };
  } else {
    fields.expected = { kind: "error", category: draft.outcome };
  }
  return fields;
}

function renderExpectedValue() {
  const valueOutcome = outcome.value === "value";
  expectedValueField.hidden = !valueOutcome;
  expectedValue.disabled = !valueOutcome;
}

function renderStatus() {
  const dirty = hasUnsavedEdits();
  const savedStatus = saved ? `Saved · revision ${saved.collection.revision}` : "";
  status.textContent = dirty ? "Unsaved case changes" : savedStatus;
  status.classList.toggle("dirty", dirty);
  saveButton.disabled = conflict || (editingCase !== null && !dirty);
  deleteButton.disabled = conflict;
  addButton.disabled = busy || conflict;
  conflictNotice.hidden = !conflict;
}

function renderList(list, records, selectedId) {
  const items = records.map((record) => {
    const item = document.createElement("li");
    const button = document.createElement("button");
    button.type = "button";
    button.dataset.recordId = record.id;
    button.textContent = record.name;
    button.disabled = busy;
    if (record.id === selectedId) button.setAttribute("aria-current", "true");
    item.append(button);
    return item;
  });
  list.replaceChildren(...items);
}

function renderCollectionList() {
  renderList(collectionList, collections, saved?.collection.id);
  listStatus.textContent = collections.length ? "" : "No collections saved yet.";
}

function populateCase(testCase, visible) {
  editingCase = testCase;
  name.value = testCase?.name ?? "";
  source.value = testCase?.source ?? "";
  description.value = testCase?.description ?? "";
  const expected = testCase?.expected;
  outcome.value = expected?.kind === "error" ? expected.category : "value";
  expectedValue.value = expected?.kind === "value" ? expected.value : "";
  baseline = readDraft();
  caseHeading.textContent = testCase ? "Edit test case" : "New test case";
  caseForm.hidden = !visible;
  deleteButton.hidden = !testCase;
  renderExpectedValue();
  const cases = saved.collection.cases;
  renderList(caseList, cases, testCase?.id);
  caseListStatus.hidden = cases.length > 0;
  renderStatus();
}

function showCollection(record, caseId) {
  saved = record;
  const { collection } = record;
  const index = collections.findIndex((item) => item.id === collection.id);
  if (index === -1) collections.push(collection);
  else collections[index] = collection;
  heading.textContent = collection.name;
  placeholder.hidden = true;
  content.hidden = false;
  conflict = false;
  renderCollectionList();
  const testCase = collection.cases.find((candidate) => candidate.id === caseId) ?? null;
  populateCase(testCase, testCase !== null);
}

function showError(notice, message = "") {
  notice.textContent = message;
  notice.hidden = !message;
}

function setBusy(value) {
  busy = value;
  for (const control of [collectionName, createButton, refreshButton, reloadButton, caseFields]) {
    control.disabled = value;
  }
  for (const button of document.querySelectorAll("#collection-list button, #case-list button")) {
    button.disabled = value;
  }
  renderStatus();
}

async function perform(action, { notice = caseError, mutation = false } = {}) {
  if (busy) return;
  setBusy(true);
  showError(libraryError);
  showError(caseError);
  try {
    await action();
  } catch (error) {
    if (mutation && error instanceof StorageError && error.code === "revision_conflict") {
      conflict = true;
    } else {
      showError(notice, error instanceof StorageError ? error.message : "The collection operation failed.");
    }
  } finally {
    setBusy(false);
  }
}

function confirmDiscard() {
  return !hasUnsavedEdits() || window.confirm("Discard the unsaved case changes?");
}

function refreshCollections() {
  return perform(async () => {
    listStatus.textContent = "Loading test collections…";
    try {
      collections = await listCollections();
    } catch (error) {
      listStatus.textContent = "Could not refresh test collections.";
      throw error;
    }
    renderCollectionList();
  }, { notice: libraryError });
}

refreshButton.addEventListener("click", refreshCollections);
collectionForm.addEventListener("submit", (event) => {
  event.preventDefault();
  if (busy) return;
  if (!collectionName.value.trim()) {
    showError(libraryError, "Enter a collection name.");
    collectionName.focus();
    return;
  }
  if (!confirmDiscard()) return;
  void perform(async () => {
    const record = await createCollection({ name: collectionName.value });
    collectionName.value = "";
    showCollection(record);
  }, { notice: libraryError });
});
collectionList.addEventListener("click", (event) => {
  const id = event.target.closest("button")?.dataset.recordId;
  if (!id || id === saved?.collection.id || !confirmDiscard()) return;
  void perform(async () => showCollection(await getCollection(id)), { notice: libraryError });
});
reloadButton.addEventListener("click", () => {
  if (!confirmDiscard()) return;
  void perform(async () => showCollection(await getCollection(saved.collection.id), editingCase?.id));
});

addButton.addEventListener("click", () => {
  if (!confirmDiscard()) return;
  showError(caseError);
  populateCase(null, true);
  name.focus();
});
caseList.addEventListener("click", (event) => {
  const id = event.target.closest("button")?.dataset.recordId;
  if (!id || id === editingCase?.id || !confirmDiscard()) return;
  showError(caseError);
  populateCase(saved.collection.cases.find((testCase) => testCase.id === id), true);
  name.focus();
});
caseForm.addEventListener("input", () => {
  renderExpectedValue();
  renderStatus();
});
caseForm.addEventListener("submit", (event) => {
  event.preventDefault();
  if (busy || saveButton.disabled) return;
  const draft = readDraft();
  const invalidField = [name, source].find((input) => !draft[input.name].trim());
  if (invalidField) {
    showError(caseError, invalidField === name ? "Enter a case name." : "Enter case source.");
    invalidField.focus();
    return;
  }
  const fields = savedCaseFields(draft);
  void perform(async () => {
    const id = saved.collection.id;
    if (editingCase) {
      const caseId = editingCase.id;
      showCollection(await updateCase(id, caseId, fields, saved.etag), caseId);
    } else {
      const record = await appendCase(id, fields, saved.etag);
      showCollection(record, record.collection.cases.at(-1).id);
    }
  }, { mutation: true });
});
deleteButton.addEventListener("click", () => {
  if (!window.confirm("Delete this saved case? Any edits to it will be discarded.")) return;
  void perform(async () => {
    showCollection(await deleteCase(saved.collection.id, editingCase.id, saved.etag));
  }, { mutation: true });
});

void refreshCollections();
