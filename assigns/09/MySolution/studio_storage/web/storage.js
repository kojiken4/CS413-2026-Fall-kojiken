const BASE_URL = "/api/v1";

export class StorageError extends Error {
  constructor(code, message) {
    super(message);
    this.code = code;
  }
}

function invalidResponse() {
  return new StorageError("invalid_response", "The storage service returned an invalid response.");
}

async function request(path, { method = "GET", fields, etag } = {}) {
  const headers = { Accept: "application/json" };
  if (fields !== undefined) headers["Content-Type"] = "application/json";
  if (etag !== undefined) headers["If-Match"] = etag;

  let response;
  try {
    response = await fetch(BASE_URL + path, {
      method,
      headers,
      body: fields === undefined ? undefined : JSON.stringify(fields),
      cache: "no-store",
    });
  } catch {
    throw new StorageError("network_error", "Could not reach the storage service. Try again when it is running.");
  }

  let data;
  try {
    data = await response.json();
  } catch {
    if (response.ok) throw invalidResponse();
  }
  if (!response.ok) {
    const { code, message } = data?.error ?? {};
    if (typeof code === "string" && typeof message === "string") {
      throw new StorageError(code, message);
    }
    throw new StorageError("http_error", `The storage request failed (HTTP ${response.status}).`);
  }
  return { data, etag: response.headers.get("ETag") };
}

async function listRecords(path, isRecord) {
  const records = [];
  const seenCursors = new Set();
  let cursor = null;
  do {
    const query = cursor === null ? "" : "?" + new URLSearchParams({ cursor });
    const { data } = await request(path + query);
    if (!Array.isArray(data?.items) || !data.items.every(isRecord) ||
        (data.next_cursor !== null && (typeof data.next_cursor !== "string" || !data.next_cursor))) {
      throw invalidResponse();
    }
    records.push(...data.items);
    cursor = data.next_cursor;
    if (seenCursors.has(cursor)) throw invalidResponse();
    if (cursor !== null) seenCursors.add(cursor);
  } while (cursor !== null);
  return records;
}

function isProgram(program) {
  return program && typeof program.id === "string" &&
    typeof program.name === "string" && typeof program.source === "string" &&
    typeof program.description === "string" && Number.isInteger(program.revision);
}

function isCase(testCase) {
  if (!testCase || typeof testCase.id !== "string" || typeof testCase.name !== "string" ||
      typeof testCase.source !== "string" || typeof testCase.description !== "string") return false;
  const expected = testCase.expected;
  return (expected?.kind === "value" && typeof expected.value === "string") ||
    (expected?.kind === "error" && ["syntax", "type"].includes(expected.category));
}

function isCollection(collection) {
  return collection && typeof collection.id === "string" && typeof collection.name === "string" &&
    typeof collection.description === "string" && Number.isInteger(collection.revision) &&
    Array.isArray(collection.cases) && collection.cases.every(isCase);
}

async function readRecord(path, key, isRecord, options) {
  const { data, etag } = await request(path, options);
  const record = data?.[key];
  if (!isRecord(record) || etag !== `"${record.revision}"`) throw invalidResponse();
  return { [key]: record, etag };
}

export function listPrograms() {
  return listRecords("/programs", isProgram);
}

export function getProgram(id) {
  return readRecord(`/programs/${encodeURIComponent(id)}`, "program", isProgram);
}

export function createProgram(fields) {
  return readRecord("/programs", "program", isProgram, { method: "POST", fields });
}

export function updateProgram(id, fields, etag) {
  return readRecord(`/programs/${encodeURIComponent(id)}`, "program", isProgram, { method: "PUT", fields, etag });
}

function collectionPath(id) {
  return `/collections/${encodeURIComponent(id)}`;
}

export function listCollections() {
  return listRecords("/collections", isCollection);
}

export function getCollection(id) {
  return readRecord(collectionPath(id), "collection", isCollection);
}

export function createCollection(fields) {
  return readRecord("/collections", "collection", isCollection, { method: "POST", fields });
}

export function appendCase(collectionId, fields, etag) {
  const path = `${collectionPath(collectionId)}/cases`;
  return readRecord(path, "collection", isCollection, { method: "POST", fields, etag });
}

export function updateCase(collectionId, caseId, fields, etag) {
  const path = `${collectionPath(collectionId)}/cases/${encodeURIComponent(caseId)}`;
  return readRecord(path, "collection", isCollection, { method: "PUT", fields, etag });
}

export function deleteCase(collectionId, caseId, etag) {
  const path = `${collectionPath(collectionId)}/cases/${encodeURIComponent(caseId)}`;
  return readRecord(path, "collection", isCollection, { method: "DELETE", etag });
}
