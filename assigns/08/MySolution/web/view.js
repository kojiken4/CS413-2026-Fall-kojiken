const SIZE = 8;

function makeSquare(document, row, column) {
  const square = document.createElement("div");
  square.className = (row + column) % 2 ? "square is-dark" : "square";
  square.setAttribute("aria-hidden", "true");

  const queen = document.createElement("span");
  queen.className = "queen";
  queen.textContent = "♛";
  square.append(queen);

  if (column === 0) {
    const label = document.createElement("span");
    label.className = "coordinate row-label";
    label.textContent = row;
    square.append(label);
  }
  if (row === SIZE - 1) {
    const label = document.createElement("span");
    label.className = "coordinate column-label";
    label.textContent = column;
    square.append(label);
  }
  return square;
}

function describeEvent({ event, row, column, board }) {
  const position = `Row ${row}, column ${column}`;
  switch (event) {
    case "try": return ["Trying a square", `${position} is the next candidate.`];
    case "place": return ["Queen placed", `${position} is safe.`];
    case "reject": {
      const conflict = board.findIndex((placed, earlierRow) =>
        placed === column || Math.abs(placed - column) === row - earlierRow);
      const direction = board[conflict] === column ? "a column" : "a diagonal";
      return ["Candidate rejected", `${position} shares ${direction} with the queen in row ${conflict}.`];
    }
    case "backtrack": return ["Backtracking", `${position} was cleared.`];
    case "solution": return ["Solution found", "All eight queens are safe."];
    case "done": return ["Search complete", "All candidates have been explored."];
    default: throw new Error("The puzzle service returned an unknown event.");
  }
}

export function createView(document) {
  const boardElement = document.getElementById("board");
  const squares = Array.from({ length: SIZE }, (_, row) =>
    Array.from({ length: SIZE }, (_, column) => makeSquare(document, row, column)));
  boardElement.replaceChildren(...squares.flat());

  const controls = Object.fromEntries(["start", "step", "play", "seek", "reset", "speed"].map(
    (name) => [name, document.getElementById(name)]));
  const status = document.getElementById("status");
  const title = document.getElementById("status-title");
  const detail = document.getElementById("status-detail");
  const count = document.getElementById("count");
  const error = document.getElementById("error");
  let board = [];
  let highlights = [];

  function setStatus(kind, heading, description) {
    status.dataset.event = kind;
    title.textContent = heading;
    detail.textContent = description;
  }

  function showError(message) {
    error.textContent = message;
    error.hidden = !message;
  }

  function showBoard(snapshot, kind, row, column) {
    for (const [square, style] of highlights) {
      square.classList.remove(style);
    }
    highlights = [];
    if (snapshot !== board) {
      for (let r = 0; r < SIZE; r += 1) {
        squares[r][board[r]]?.classList.remove("has-queen");
        squares[r][snapshot[r]]?.classList.add("has-queen");
      }
      board = snapshot;
    }
    if (kind === "solution") {
      highlights = board.map((col, r) => [squares[r][col], "is-solution"]);
    } else if (row !== undefined && column !== undefined) {
      highlights = [[squares[row][column], `is-${kind}`]];
    }
    for (const [square, style] of highlights) {
      square.classList.add(style);
    }

    const queens = board.map((col, r) => `row ${r}, column ${col}`);
    const positions = queens.length ? `Queens at ${queens.join("; ")}` : "Empty";
    boardElement.setAttribute("aria-label", `Chessboard. ${positions}.`);
  }

  return {
    controls,
    setStatus,
    showError,
    clear() {
      showBoard([]);
      count.textContent = "0";
      showError("");
    },
    showEvent(event, solutions) {
      const [heading, description] = describeEvent(event);
      showBoard(event.board ?? board, event.event, event.row, event.column);
      count.textContent = solutions;
      setStatus(event.event, heading, description);
    },
    setMode(mode) {
      const ready = mode === "ready";
      const running = mode === "playing" || mode === "seeking";
      controls.start.disabled = mode !== "idle" && mode !== "complete";
      controls.step.disabled = !ready;
      controls.play.disabled = !ready && !running;
      controls.play.textContent = running ? "Pause" : "Play";
      controls.seek.disabled = !ready;
      controls.reset.disabled = mode === "idle";
    },
  };
}
