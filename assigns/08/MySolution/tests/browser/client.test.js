import { mountPlayback } from "../../web/playback.js";
import { createQueensRpc } from "../../web/rpc.js";

const results = document.getElementById("results");
const pause = (milliseconds = 0) => new Promise((resolve) => setTimeout(resolve, milliseconds));

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

async function until(check, message) {
  const deadline = performance.now() + 1500;
  while (!check()) {
    assert(performance.now() < deadline, message);
    await pause(10);
  }
}

function fixture(markup) {
  const page = new DOMParser().parseFromString(markup, "text/html");
  const requests = [];
  const rpc = createQueensRpc((url, config) => new Promise((resolve, reject) => {
    assert(url === "/rpc" && config.method === "POST", "RPC transport must POST to /rpc");
    assert(config.headers["Content-Type"] === "application/json", "RPC must send JSON");
    const { jsonrpc, id, method, params } = JSON.parse(config.body);
    assert(jsonrpc === "2.0", "RPC must use JSON-RPC 2.0");
    const respond = (fields) => resolve({ ok: true, json: async () => ({ jsonrpc, id, ...fields }) });
    requests.push({
      method,
      params,
      resolve: (result) => respond({ result }),
      fail: (code, message) => respond({ error: { code, message } }),
      disconnect: () => reject(new TypeError("network offline")),
    });
  }));
  mountPlayback(page, rpc);
  const element = (id) => page.getElementById(id);

  function take(method, params) {
    const request = requests.shift();
    assert(request?.method === method, `Expected ${method}, got ${request?.method}`);
    assert(JSON.stringify(request.params) === JSON.stringify(params), `Unexpected params for ${method}`);
    return request;
  }

  return {
    requests,
    element,
    click: (id) => element(id).click(),
    kind: () => element("status").dataset.event,
    count: () => Number(element("count").textContent),
    squares: (selector) => element("board").querySelectorAll(selector).length,
    take,
    async open(streamId = "search") {
      element("start").click();
      take("queens.open", { size: 8 }).resolve({ stream_id: streamId, size: 8 });
      await until(() => element("status").dataset.event === "ready", "Search did not open");
    },
    async sendEvents(events, { streamId = "search", limit = 1 } = {}) {
      await until(() => requests.length > 0, "No event request was sent");
      take("queens.next", { stream_id: streamId, limit }).resolve({
        events, done: events.at(-1).event === "done",
      });
      await pause();
    },
  };
}

const firstTry = { event: "try", row: 0, column: 0, board: [] };
const firstPlace = { event: "place", row: 0, column: 0, board: [0] };
const solution = { event: "solution", board: [0, 4, 7, 5, 2, 6, 1, 3] };

const tests = {
  async "Start, step, render snapshots, and reset"(page) {
    assert(page.squares(".square") === 64, "Board must have 64 squares");
    assert(page.element("step").disabled, "Step must wait for a stream");
    await page.open();
    assert(page.requests.length === 0, "Start must leave the first event unread");

    const attempt = { event: "try", row: 1, column: 1, board: [0] };
    for (const event of [firstTry, firstPlace, attempt, { ...attempt, event: "reject" }]) {
      page.click("step");
      await page.sendEvents([event]);
      assert(page.kind() === event.event, `Expected status for ${event.event}`);
      assert(page.squares(`.is-${event.event}`) === 1, `Missing ${event.event} highlight`);
      assert(page.squares(".has-queen") === event.board.length, "Wrong board snapshot");
      assert(page.requests.length === 0, "Step must request exactly one event");
    }
    assert(page.element("status-detail").textContent.includes("shares a diagonal"), "Missing rejection reason");

    page.click("step");
    await page.sendEvents([{ ...firstTry, event: "backtrack" }]);
    assert(page.squares(".is-backtrack") === 1 && page.squares(".has-queen") === 0, "Backtrack must clear a queen");
    page.click("reset");
    page.take("queens.close", { stream_id: "search" }).resolve({ closed: true });
    assert(page.kind() === "idle" && page.count() === 0, "Reset must clear status and count");
    assert(page.squares(".is-backtrack") === 0, "Reset must clear highlights");
  },

  async "Play requests one event at a time and pause keeps an in-flight event"(page) {
    await page.open();
    page.element("speed").value = "60";
    page.click("play");
    assert(page.element("play").textContent === "Pause", "Play must become Pause");
    const pending = page.take("queens.next", { stream_id: "search", limit: 1 });
    await pause(90);
    assert(page.requests.length === 0, "Play must wait until the current request returns");
    page.click("play");
    pending.resolve({ events: [firstTry], done: false });
    await pause();
    assert(page.kind() === "ready", "Pause must hold the in-flight event");

    page.click("step");
    assert(page.kind() === "try" && page.requests.length === 0, "Step must consume the buffered event");
    page.click("play");
    await page.sendEvents([firstPlace]);
    await page.sendEvents([{ event: "try", row: 1, column: 0, board: [0] }]);
    page.click("play");
    await pause(90);
    assert(page.requests.length === 0, "Pause must cancel the next timed read");
  },

  async "Next solution stops inside a batch, preserves later events, and allows restart"(page) {
    await page.open();
    page.click("seek");
    await page.sendEvents([
      firstTry,
      solution,
      { event: "backtrack", row: 7, column: 3, board: solution.board.slice(0, -1) },
      { event: "solution", board: solution.board.map((column) => 7 - column) },
      { event: "done" },
    ], { limit: 32 });
    assert(page.kind() === "solution" && page.count() === 1, "A solution must update the status and count");
    assert(page.squares(".is-solution") === 8, "Highlight all solution queens");
    assert(page.requests.length === 0 && !page.element("seek").disabled, "Seek must stop at a solution");

    page.click("step");
    assert(page.kind() === "backtrack" && page.requests.length === 0, "Step must use the next buffered event");
    page.click("seek");
    assert(page.kind() === "solution" && page.count() === 2, "Seek must stop at a buffered solution");
    page.click("seek");
    assert(page.kind() === "done" && page.count() === 2, "Done must preserve the count");
    assert(page.requests.length === 0, "Playback must finish the buffered batch before requesting again");
    assert(page.element("step").disabled && !page.element("start").disabled, "Completion must allow a restart");
    page.click("start");
    page.take("queens.close", { stream_id: "search" }).resolve({ closed: true });
    page.take("queens.open", { size: 8 }).resolve({ stream_id: "restart", size: 8 });
    await until(() => page.kind() === "ready", "Restart did not open a fresh stream");
    assert(page.count() === 0 && page.squares(".has-queen") === 0, "Restart must clear the previous solution");
  },

  async "Reset closes a late open and ignores an earlier next response"(page) {
    page.click("start");
    const oldOpen = page.take("queens.open", { size: 8 });
    page.click("reset");
    await page.open();
    oldOpen.resolve({ stream_id: "old", size: 8 });
    await until(() => page.requests.length > 0, "A late open must be closed");
    page.take("queens.close", { stream_id: "old" }).resolve({ closed: true });

    page.click("step");
    const oldNext = page.take("queens.next", { stream_id: "search", limit: 1 });
    page.click("reset");
    page.take("queens.close", { stream_id: "search" }).resolve({ closed: true });
    await page.open("new");
    oldNext.resolve({ events: [solution], done: false });
    await pause();
    assert(page.kind() === "ready" && page.count() === 0, "Stale events must leave the new board alone");
    page.click("step");
    await page.sendEvents([firstTry], { streamId: "new" });
    assert(page.kind() === "try", "Continue with the replacement stream");
  },

  async "RPC and network failures are visible and reset restores controls"(page) {
    await page.open();
    page.click("play");
    page.take("queens.next", { stream_id: "search", limit: 1 }).fail(-32004, "Stream not found");
    const error = page.element("error");
    await until(() => !error.hidden, "RPC failure was not shown");
    assert(error.textContent === "Stream not found", "Wrong RPC failure text");
    assert(page.element("play").disabled && !page.element("reset").disabled, "Failure must stop playback");
    page.click("reset");
    page.take("queens.close", { stream_id: "search" }).resolve({ closed: true });
    assert(error.hidden && !page.element("start").disabled, "Reset must restore Start and dismiss the error");

    page.click("start");
    page.take("queens.open", { size: 8 }).disconnect();
    await until(() => !error.hidden, "Network failure was not shown");
    assert(error.textContent.includes("Could not reach"), "Wrong network failure text");
  },
};

try {
  const response = await fetch("../../web/index.html");
  if (!response.ok) throw new Error("Could not load the application markup.");
  const markup = await response.text();
  const lines = [];
  let failures = 0;
  for (const [name, test] of Object.entries(tests)) {
    try {
      await test(fixture(markup));
      lines.push(`PASS ${name}`);
    } catch (error) {
      failures += 1;
      lines.push(`FAIL ${name}\n${error.stack}`);
    }
  }
  results.textContent = lines.join("\n");
  results.dataset.state = failures ? "failed" : "passed";
} catch (error) {
  results.dataset.state = "failed";
  results.textContent = error.stack;
}
