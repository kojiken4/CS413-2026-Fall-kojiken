import { createProgram, getProgram, listPrograms, StorageError, updateProgram } from "./storage.js";

const form = document.querySelector("#program-form");
const fields = document.querySelector("#program-fields");
const inputs = [form.elements.name, form.elements.description, form.elements.source];
const newButton = document.querySelector("#new-program");
const refreshButton = document.querySelector("#refresh-programs");
const saveButton = document.querySelector("#save-program");
const reloadButton = document.querySelector("#reload-program");
const list = document.querySelector("#program-list");
const listStatus = document.querySelector("#program-list-status");
const saveStatus = document.querySelector("#save-status");
const errorNotice = document.querySelector("#program-error");
const conflictNotice = document.querySelector("#program-conflict");

let programs = [];
let saved = null;
let baseline = readDraft();
let busy = false;
let conflict = false;

function readDraft() {
  return Object.fromEntries(inputs.map((input) => [input.name, input.value]));
}

function hasUnsavedEdits() {
  return inputs.some((input) => input.value !== baseline[input.name]);
}

function renderStatus() {
  const dirty = hasUnsavedEdits();
  const savedStatus = saved ? `Saved · revision ${saved.program.revision}` : "New program";
  saveStatus.textContent = dirty ? "Unsaved changes" : savedStatus;
  saveStatus.classList.toggle("dirty", dirty);
  saveButton.disabled = conflict || (saved !== null && !dirty);
}

function renderList() {
  const items = programs.map((program) => {
    const item = document.createElement("li");
    const button = document.createElement("button");
    button.type = "button";
    button.dataset.programId = program.id;
    button.textContent = program.name;
    button.disabled = busy;
    if (saved?.program.id === program.id) button.setAttribute("aria-current", "true");
    item.append(button);
    return item;
  });
  list.replaceChildren(...items);
  listStatus.textContent = programs.length ? "" : "No programs saved yet.";
}

function setBusy(value) {
  busy = value;
  fields.disabled = value;
  newButton.disabled = value;
  refreshButton.disabled = value;
  reloadButton.disabled = value;
  for (const button of list.querySelectorAll("button")) button.disabled = value;
}

function showError(message = "") {
  errorNotice.textContent = message;
  errorNotice.hidden = !message;
}

function showConflict(value) {
  conflict = value;
  conflictNotice.hidden = !value;
  renderStatus();
}

function populateEditor(record) {
  saved = record;
  for (const input of inputs) input.value = saved?.program[input.name] ?? "";
  baseline = readDraft();
  showConflict(false);
  renderList();
}

function rememberProgram(program) {
  const index = programs.findIndex((item) => item.id === program.id);
  if (index === -1) programs.push(program);
  else programs[index] = program;
}

function confirmDiscard() {
  return !hasUnsavedEdits() || window.confirm("Discard the unsaved program changes?");
}

async function perform(action, { saving = false } = {}) {
  if (busy) return;
  setBusy(true);
  showError();
  try {
    await action();
  } catch (error) {
    if (saving && error instanceof StorageError && error.code === "revision_conflict") {
      showConflict(true);
    } else {
      showError(error instanceof StorageError ? error.message : "The program operation failed.");
    }
  } finally {
    setBusy(false);
    renderStatus();
  }
}

async function refreshPrograms() {
  await perform(async () => {
    listStatus.textContent = "Loading saved programs…";
    try {
      programs = await listPrograms();
    } catch (error) {
      listStatus.textContent = "Could not refresh saved programs.";
      throw error;
    }
    renderList();
  });
}

async function openProgram(id) {
  const record = await getProgram(id);
  rememberProgram(record.program);
  populateEditor(record);
}

newButton.addEventListener("click", () => {
  if (!confirmDiscard()) return;
  showError();
  populateEditor(null);
  form.elements.name.focus();
});
refreshButton.addEventListener("click", refreshPrograms);
list.addEventListener("click", (event) => {
  const id = event.target.closest("button")?.dataset.programId;
  if (id && id !== saved?.program.id && confirmDiscard()) void perform(() => openProgram(id));
});
reloadButton.addEventListener("click", () => void perform(() => openProgram(saved.program.id)));
form.addEventListener("input", renderStatus);
form.addEventListener("submit", (event) => {
  event.preventDefault();
  if (busy || saveButton.disabled) return;
  const draft = readDraft();
  for (const input of [form.elements.name, form.elements.source]) {
    if (!draft[input.name].trim()) {
      showError(input.name === "name" ? "Enter a program name." : "Enter LAMBDA source.");
      input.focus();
      return;
    }
  }
  if (saved) {
    // Preserve stored text that the controls normalized when loading it.
    for (const input of inputs) {
      if (draft[input.name] === baseline[input.name]) draft[input.name] = saved.program[input.name];
    }
  }
  void perform(async () => {
    const record = saved ? await updateProgram(saved.program.id, draft, saved.etag) : await createProgram(draft);
    rememberProgram(record.program);
    populateEditor(record);
  }, { saving: true });
});

void refreshPrograms();
