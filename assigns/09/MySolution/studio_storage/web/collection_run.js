import { getCollection, StorageError } from "./storage.js";

const panel = document.querySelector("#collection-run");
const heading = document.querySelector("#run-heading");
const status = document.querySelector("#run-status");
const results = document.querySelector("#run-results");

const ERROR_CATEGORIES = new Map([[-32010, "syntax"], [-32011, "type"]]);
const TIMEOUT_MESSAGE = "LAMBDA3 timed out.";
const INVALID_REPLY = "LAMBDA3 returned an invalid reply.";

function failure(message) {
  return { kind: "failure", message };
}

async function interpret(testCase) {
  const signal = AbortSignal.timeout(6_000);
  try {
    const response = await fetch("/studio/interpret", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        jsonrpc: "2.0",
        method: "lambda.interpret",
        id: testCase.id,
        params: { source: testCase.source },
      }),
      signal,
    });
    if (response.status === 504) return failure(TIMEOUT_MESSAGE);
    if (!response.ok) return failure(`LAMBDA3 request failed (HTTP ${response.status}).`);
    const reply = await response.json();
    if (reply?.jsonrpc !== "2.0" || reply.id !== testCase.id ||
        Object.hasOwn(reply, "result") === Object.hasOwn(reply, "error")) {
      return failure(INVALID_REPLY);
    }
    if (typeof reply.result?.value === "string") {
      return { kind: "value", value: reply.result.value };
    }
    const code = reply.error?.code;
    if (ERROR_CATEGORIES.has(code)) return { kind: "error", category: ERROR_CATEGORIES.get(code) };
    if (code === -32012) return failure(TIMEOUT_MESSAGE);
    return failure(Number.isInteger(code) ? "LAMBDA3 reported an unexpected error." : INVALID_REPLY);
  } catch (error) {
    if (signal.aborted) return failure(TIMEOUT_MESSAGE);
    return failure(error instanceof SyntaxError ? INVALID_REPLY : "Could not reach LAMBDA3.");
  }
}

function matches(expected, actual) {
  if (actual.kind !== expected.kind) return false;
  return expected.kind === "value" ? actual.value === expected.value : actual.category === expected.category;
}

function describe(outcome) {
  if (outcome.kind === "value") return `Value ${JSON.stringify(outcome.value)}`;
  if (outcome.kind === "error") return outcome.category === "syntax" ? "Syntax error" : "Type error";
  return outcome.message;
}

function addResult(testCase, actual, passed) {
  const item = document.createElement("li");
  item.dataset.caseId = testCase.id;
  const details = document.createElement("details");
  const label = document.createElement("summary");
  label.classList.add(passed ? "run-pass" : "run-fail");
  label.textContent = `${passed ? "Pass" : "Fail"} · ${testCase.name}`;
  const expectedText = document.createElement("p");
  expectedText.textContent = `Expected ${describe(testCase.expected)}`;
  const actualText = document.createElement("p");
  actualText.textContent = `Observed ${describe(actual)}`;
  const source = document.createElement("pre");
  source.setAttribute("aria-label", "Source snapshot");
  source.textContent = testCase.source;
  details.append(label, expectedText, actualText, source);
  item.append(details);
  results.append(item);
}

export async function runCollection(collectionId) {
  heading.textContent = "Collection run";
  status.textContent = "Loading saved cases…";
  results.replaceChildren();
  panel.hidden = false;

  let collection;
  try {
    // This full GET provides the snapshot used for every result in this run.
    ({ collection } = await getCollection(collectionId));
  } catch (error) {
    status.textContent = error instanceof StorageError ? error.message : "Could not load the collection.";
    return;
  }

  heading.textContent = `${collection.name} · revision ${collection.revision}`;
  const { cases } = collection;
  if (cases.length === 0) {
    status.textContent = "No saved cases to run.";
    return;
  }

  let passed = 0;
  for (const [index, testCase] of cases.entries()) {
    status.textContent = `Running case ${index + 1} of ${cases.length}…`;
    const actual = await interpret(testCase);
    const matched = matches(testCase.expected, actual);
    if (matched) passed += 1;
    addResult(testCase, actual, matched);
  }
  status.textContent = `${passed} passed, ${cases.length - passed} failed.`;
}
