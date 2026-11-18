export function createQueensRpc(send = (...args) => fetch(...args)) {
  let nextId = 0;

  async function call(method, params) {
    const id = ++nextId;
    let response;
    try {
      response = await send("/rpc", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ jsonrpc: "2.0", id, method, params }),
      });
    } catch {
      throw new Error("Could not reach the puzzle service.");
    }
    if (!response.ok) {
      throw new Error(`The puzzle service returned HTTP ${response.status}.`);
    }

    let reply;
    try {
      reply = await response.json();
    } catch {
      throw new Error("The puzzle service returned invalid JSON.");
    }
    if (reply?.jsonrpc !== "2.0" || reply.id !== id) {
      throw new Error("The puzzle service returned an unexpected reply.");
    }
    if (reply.error) {
      throw new Error(reply.error.message);
    }
    if (!reply.result || typeof reply.result !== "object") {
      throw new Error("The puzzle service returned no result.");
    }
    return reply.result;
  }

  return {
    async open() {
      const result = await call("queens.open", { size: 8 });
      if (typeof result.stream_id !== "string" || !result.stream_id || result.size !== 8) {
        throw new Error("The puzzle service returned an invalid stream.");
      }
      return result.stream_id;
    },
    async next(streamId, limit) {
      const { events, done } = await call("queens.next", { stream_id: streamId, limit });
      if (Array.isArray(events) && events.length > 0 && events.length <= limit) {
        return events;
      }
      if (Array.isArray(events) && events.length === 0 && done === true) {
        return [{ event: "done" }];
      }
      throw new Error("The puzzle service returned an unexpected event batch.");
    },
    async close(streamId) {
      await call("queens.close", { stream_id: streamId });
    },
  };
}
