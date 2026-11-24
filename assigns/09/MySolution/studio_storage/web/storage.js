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

async function listRecords(path) {
  const records = [];
  const seenCursors = new Set();
  let cursor = null;
  do {
    const query = cursor === null ? "" : "?" + new URLSearchParams({ cursor });
    const { data } = await request(path + query);
    if (!Array.isArray(data?.items) ||
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

async function readProgram(path, options) {
  const { data, etag } = await request(path, options);
  if (!isProgram(data?.program) || etag !== `"${data.program.revision}"`) {
    throw invalidResponse();
  }
  return { program: data.program, etag };
}

export async function listPrograms() {
  const programs = await listRecords("/programs");
  if (!programs.every(isProgram)) throw invalidResponse();
  return programs;
}

export function getProgram(id) {
  return readProgram(`/programs/${encodeURIComponent(id)}`);
}

export function createProgram(fields) {
  return readProgram("/programs", { method: "POST", fields });
}

export function updateProgram(id, fields, etag) {
  return readProgram(`/programs/${encodeURIComponent(id)}`, { method: "PUT", fields, etag });
}
