import { createQueensRpc } from "./rpc.js";
import { createView } from "./view.js";

const SEEK_LIMIT = 32;

function newRun(mode) {
  return { mode, id: null, timer: null, inFlight: false, pending: [], solutions: 0 };
}

export function mountPlayback(document, rpc = createQueensRpc()) {
  const view = createView(document);
  const { start, step, play, seek, reset, speed } = view.controls;
  let run = newRun("idle");

  function setMode(mode) {
    run.mode = mode;
    view.setMode(mode);
  }

  function cancelTimer(active) {
    clearTimeout(active.timer);
    active.timer = null;
  }

  async function closeStream(id, reportTo = null) {
    if (id === null) return;
    try {
      await rpc.close(id);
    } catch (error) {
      if (run === reportTo) view.showError(error.message);
    }
  }

  async function startSearch() {
    const previous = run;
    const active = newRun("opening");
    run = active;
    view.clear();
    setMode("opening");
    view.setStatus("opening", "Opening search", "Preparing a new 8×8 board.");
    void closeStream(previous.id);

    try {
      const id = await rpc.open();
      if (run !== active) {
        void closeStream(id);
        return;
      }
      active.id = id;
      setMode("ready");
      view.setStatus("ready", "Search ready", "Step through the search or press Play.");
    } catch (error) {
      if (run === active) stopWithError(error);
    }
  }

  function resetSearch() {
    const previous = run;
    cancelTimer(previous);
    run = newRun("idle");
    view.clear();
    setMode("idle");
    view.setStatus("idle", "Ready to start", "Start opens a new search.");
    void closeStream(previous.id, run);
  }

  function stopWithError(error) {
    setMode("error");
    view.setStatus("error", "Search stopped", "Reset to open a new search.");
    view.showError(error.message);
  }

  async function advance(active) {
    if (active !== run || active.inFlight || active.mode === "ready") return;
    active.inFlight = true;
    try {
      if (active.pending.length === 0) {
        const limit = active.mode === "seeking" ? SEEK_LIMIT : 1;
        const events = await rpc.next(active.id, limit);
        if (active !== run) return;
        active.pending = events;
      }
      if (active.mode === "ready") return;

      do {
        const event = active.pending.shift();
        if (event.event === "solution") active.solutions += 1;
        view.showEvent(event, active.solutions);
        if (event.event === "done") {
          setMode("complete");
        } else if (active.mode === "stepping" || (active.mode === "seeking" && event.event === "solution")) {
          setMode("ready");
        }
      } while (active.mode === "seeking" && active.pending.length > 0);
    } catch (error) {
      if (active === run) stopWithError(error);
    } finally {
      active.inFlight = false;
    }

    if (active.mode === "playing") {
      active.timer = setTimeout(() => {
        active.timer = null;
        void advance(active);
      }, Number(speed.value));
    } else if (active.mode === "seeking") {
      void advance(active);
    }
  }

  function begin(mode) {
    setMode(mode);
    void advance(run);
  }

  start.addEventListener("click", startSearch);
  reset.addEventListener("click", resetSearch);
  step.addEventListener("click", () => begin("stepping"));
  seek.addEventListener("click", () => begin("seeking"));
  play.addEventListener("click", () => {
    if (run.mode === "playing" || run.mode === "seeking") {
      cancelTimer(run);
      setMode("ready");
    } else {
      begin("playing");
    }
  });
  view.clear();
  view.setMode(run.mode);
}
