"""Run both programs fresh and compare their complete output (Windows + WSL)."""

import difflib
import subprocess
import sys
import time
from pathlib import Path

from test03_queens import parse_ats_output


def main():
    solution = Path(__file__).resolve().parents[1]
    build = solution / ".ats-build"
    build.mkdir(exist_ok=True)
    ats_output = build / "queens-ats-fresh.txt"
    lambda_output = build / "queens-lambda-fresh.txt"

    print("Compiling and running queens.dats in Ubuntu WSL...", flush=True)
    subprocess.run(
        ["wsl", "-d", "Ubuntu", "--", "patscc", "-o", "queens", "../queens.dats"],
        cwd=build, check=True,
    )
    with ats_output.open("wb") as output:
        subprocess.run(["wsl", "-d", "Ubuntu", "--", "./queens"],
                       cwd=build, stdout=output, check=True)

    print("Running queens_lambda0.py (allow several minutes)...", flush=True)
    started = time.perf_counter()
    with lambda_output.open("wb") as output:
        subprocess.run([sys.executable, "-B", str(solution / "queens_lambda0.py")],
                       cwd=solution, stdout=output, check=True)
    elapsed = time.perf_counter() - started

    # Universal-newline decoding accounts for Windows CRLF versus Linux LF only.
    original = ats_output.read_text(encoding="utf-8")
    translated = lambda_output.read_text(encoding="utf-8")
    if original != translated:
        difference = difflib.unified_diff(
            original.splitlines(keepends=True), translated.splitlines(keepends=True),
            fromfile="ATS2", tofile="LAMBDA0",
        )
        sys.stderr.writelines(difference)
        raise ValueError("Fresh program outputs differ")
    reference = (solution / "reference" / "queens-ats-output.txt").read_text(encoding="utf-8")
    if original != reference:
        raise ValueError("Fresh ATS2 output differs from the saved reference")

    boards = parse_ats_output(translated)
    if len(boards) != 92 or len(set(boards)) != 92:
        raise ValueError("Expected 92 distinct solution boards")
    for number, board in enumerate(boards, start=1):
        if (set(board) != set(range(8))
                or len({row - col for row, col in enumerate(board)}) != 8
                or len({row + col for row, col in enumerate(board)}) != 8):
            raise ValueError(f"Invalid solution #{number}")
    print("PASS: both programs exited successfully; complete output matches (newline-normalized).")
    print("PASS: 92 distinct valid boards in ATS2 order; saved reference matches the fresh run.")
    print(f"LAMBDA0 execution: {elapsed:.3f} seconds. Outputs: {build}")


if __name__ == "__main__":
    main()
