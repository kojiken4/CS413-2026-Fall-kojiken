# LAMBDA-studio storage API v1

The storage service exposes a local, single-user HTTP API at
`http://127.0.0.1:8001/api/v1`. It stores LAMBDA source and test expectations
as data. LAMBDA3 handles execution separately. All records and pagination
snapshots live in the storage process's memory. They survive browser reloads
and disappear when the storage process stops.

Send create and update bodies as UTF-8 JSON with `Content-Type: application/json`.
All responses with bodies use `Content-Type: application/json`. A `204` response
has an empty body. The companion [OpenAPI description](openapi.json) defines
the request and response schemas, headers, and per-operation status codes.

## Routes

All paths below are relative to `/api/v1`. A dash indicates no request body.
The `If-Match` column identifies the record whose ETag the client must send.

| Method and path | Request body or query | `If-Match` | Success |
| --- | --- | --- | --- |
| `GET /health` | — | — | `200 {"status":"ok","version":"1.0"}` |
| `POST /programs` | Program write | — | `201` program envelope and ETag |
| `GET /programs` | `limit`, `cursor` | — | `200` program page |
| `GET /programs/{id}` | — | — | `200` program envelope and ETag |
| `PUT /programs/{id}` | Program write | Program | `200` program envelope and updated ETag |
| `DELETE /programs/{id}` | — | Program | `204` |
| `POST /collections` | Collection write | — | `201` collection envelope and ETag |
| `GET /collections` | `limit`, `cursor` | — | `200` collection page |
| `GET /collections/{id}` | — | — | `200` collection envelope and ETag |
| `PUT /collections/{id}` | Collection write | Collection | `200` collection envelope and updated ETag |
| `DELETE /collections/{id}` | — | Collection | `204` |
| `POST /collections/{id}/cases` | Case write | Collection | `201` collection envelope and updated ETag |
| `PUT /collections/{id}/cases/{case_id}` | Case write | Collection | `200` collection envelope and updated ETag |
| `DELETE /collections/{id}/cases/{case_id}` | — | Collection | `200` collection envelope and updated ETag |

## Records and writes

| Record | Fields in response | Required write fields |
| --- | --- | --- |
| Program | `id`, `name`, `source`, `description`, `created_at`, `updated_at`, `revision` | `name`, `source` |
| Collection | `id`, `name`, `description`, `created_at`, `updated_at`, `revision`, `cases` | `name` |
| Case | `id`, `name`, `source`, `expected`, `description` | `name`, `source`, `expected` |

- Each write is a JSON object. Every write accepts an optional string
  `description` and stores an empty string when it is omitted. Unknown keys,
  including server-managed fields, cause a `400`.
- IDs are opaque strings assigned by the service. Use returned IDs in URLs.
  A case ID identifies a case within its collection. Timestamps are ISO 8601
  UTC strings ending in `Z`. Revisions are positive integers.
- Names must be strings with at least one non-whitespace character. The
  service stores the trimmed name and compares it case-sensitively. Uniqueness
  applies separately to programs, collections, and the cases of each
  collection. Source must be a nonblank string and is stored exactly as sent.
- The record envelopes are `{"program": <program>}` and
  `{"collection": <collection>}`. A page is
  `{"items": [<record>, ...], "next_cursor": <string or null>}`, with full
  records in `items`. Collection records always include their ordered cases.
- A new collection has an empty `cases` array. Collection PUT replaces only
  metadata. Case POST appends a case, PUT replaces it in place and preserves
  its ID, and DELETE removes it while preserving the remaining order.
  Deleting a collection removes its cases from live storage.
- Each case stores its own source snapshot. Changes to a program, including
  deletion, leave saved cases unaffected.

The `expected` field accepts exactly one of these JSON shapes.

| Expectation | JSON | Pass condition in the studio |
| --- | --- | --- |
| Formatted value | `{"kind":"value","value":"42"}` | LAMBDA3 succeeds and its formatted value exactly equals the stored string. |
| Syntax error | `{"kind":"error","category":"syntax"}` | LAMBDA3 reports a syntax error. |
| Type error | `{"kind":"error","category":"type"}` | LAMBDA3 reports a type-checking error. |

Unknown keys inside `expected` cause a `400`. A timeout, transport failure, or
unexpected server error fails the case. The studio performs the comparison.

## Revisions and atomicity

Programs and collections start at revision `1`, with `created_at` and
`updated_at` set to the same UTC timestamp. Each successful PUT and each case
mutation updates the affected record's `updated_at` and advances its revision
by exactly one. Case writes advance the collection revision. Top-level
deletes check the current revision and remove the record.

The ETag is a single strong tag containing the quoted decimal revision, for
example `ETag: "3"`. Send the exact tag as `If-Match: "3"`. Weak tags,
wildcards, lists of tags, and other malformed values receive `400` for
existing targets. A missing program, collection, or target case receives
`404` before the precondition is evaluated. An existing target with a
missing header receives `428`, and a well-formed stale tag receives `409`.
Top-level `204` deletions have no ETag.

Revision checks and mutations are atomic. When two writers use the same
current revision, at most one succeeds. Failed writes leave the record,
its revision, and its case order unchanged.

## Limits and pagination

| Limit | Value |
| --- | --- |
| Source | 16,384 UTF-8 bytes per program or case |
| Description | 2,048 Unicode characters |
| HTTP request body | 262,144 bytes |
| Page size | 1–50 items, default 50 |
| Cases per collection | 50 |
| Live records | 500 total, counting programs, collections, and their cases |

An oversized source or description or an invalid page size receives `400`.
An oversized request body receives `413`. A create or append that would
exceed record capacity receives `409`.

An initial list request omits `cursor`. It captures the ordered record
representations as of that request, including case contents for collections.
Creation order is stable across updates. Later additions are excluded from
the chain, and later updates and deletes leave the captured values intact.

Pass the returned `next_cursor` to fetch the next page. Omit `limit` to use
the page size selected for the chain, or repeat that size. `next_cursor: null`
marks the end. Use only `limit` and `cursor`, each at most once. Unknown,
empty, or wrong-resource cursors and conflicting page sizes receive `400`.

The service keeps a process-local mapping from each opaque cursor token to
the resource, immutable snapshot, page size, and next offset. It reuses
snapshots for unchanged data and retains issued cursor chains until shutdown.
Snapshot data can therefore outlive its live records within a process. The
live-record limit counts current records. A restart invalidates every token.

## Errors

Every error response uses `{"error":{"code":"...","message":"..."}}`. A
revision conflict also contains `error.current_revision`. Code against
`error.code` and use `error.message` for display.

| HTTP status | Code | Condition |
| --- | --- | --- |
| `400` | `invalid_request` | Malformed JSON, invalid fields, or invalid parameters, including malformed `If-Match` |
| `404` | `record_not_found` | Unknown route or missing program, collection, or case |
| `405` | `method_not_allowed` | Unsupported method on a known route. The response includes `Allow`. |
| `409` | `duplicate_name` | Name already exists in its scope |
| `409` | `revision_conflict` | Stale `If-Match` |
| `409` | `capacity_limit` | A write would exceed record or collection capacity |
| `413` | `request_too_large` | HTTP body exceeds the byte limit |
| `415` | `unsupported_media_type` | Required JSON media type is missing or unsupported |
| `428` | `precondition_required` | Required `If-Match` is missing on an existing target |
| `500` | `internal_error` | Unexpected failure, with internal details kept out of the response |

## HTTP examples

The example ID represents a value returned by the service. Responses show
the application headers used by clients.

### Create a program

```http
POST /api/v1/programs
Content-Type: application/json

{"name":"Arithmetic","source":"6 * 7"}
```

```http
HTTP/1.1 201 Created
Content-Type: application/json
ETag: "1"

{"program":{"id":"9a5a8bfeaf8341b49b6f9341d7955320","name":"Arithmetic","source":"6 * 7","description":"","created_at":"2026-11-23T15:00:00Z","updated_at":"2026-11-23T15:00:00Z","revision":1}}
```

### List programs

```http
GET /api/v1/programs?limit=1
```

```http
HTTP/1.1 200 OK
Content-Type: application/json

{"items":[{"id":"9a5a8bfeaf8341b49b6f9341d7955320","name":"Arithmetic","source":"6 * 7","description":"","created_at":"2026-11-23T15:00:00Z","updated_at":"2026-11-23T15:00:00Z","revision":1}],"next_cursor":null}
```

### Read a program

```http
GET /api/v1/programs/9a5a8bfeaf8341b49b6f9341d7955320
```

```http
HTTP/1.1 200 OK
Content-Type: application/json
ETag: "1"

{"program":{"id":"9a5a8bfeaf8341b49b6f9341d7955320","name":"Arithmetic","source":"6 * 7","description":"","created_at":"2026-11-23T15:00:00Z","updated_at":"2026-11-23T15:00:00Z","revision":1}}
```

### Update a program

```http
PUT /api/v1/programs/9a5a8bfeaf8341b49b6f9341d7955320
Content-Type: application/json
If-Match: "1"

{"name":"Arithmetic","source":"40 + 2"}
```

```http
HTTP/1.1 200 OK
Content-Type: application/json
ETag: "2"

{"program":{"id":"9a5a8bfeaf8341b49b6f9341d7955320","name":"Arithmetic","source":"40 + 2","description":"","created_at":"2026-11-23T15:00:00Z","updated_at":"2026-11-23T15:01:00Z","revision":2}}
```

### Receive a stale-revision conflict

```http
PUT /api/v1/programs/9a5a8bfeaf8341b49b6f9341d7955320
Content-Type: application/json
If-Match: "1"

{"name":"Arithmetic","source":"21 * 2"}
```

```http
HTTP/1.1 409 Conflict
Content-Type: application/json

{"error":{"code":"revision_conflict","message":"If-Match does not match the current revision.","current_revision":2}}
```

### Delete a program

```http
DELETE /api/v1/programs/9a5a8bfeaf8341b49b6f9341d7955320
If-Match: "2"
```

```http
HTTP/1.1 204 No Content
```

### Reject an invalid list parameter

```http
GET /api/v1/collections?limit=0
```

```http
HTTP/1.1 400 Bad Request
Content-Type: application/json

{"error":{"code":"invalid_request","message":"limit must be an integer from 1 to 50."}}
```
