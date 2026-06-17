#!/usr/bin/env python3
"""Extract race summary (lap times per kart) from socketio JSONL log."""

import json
import sys
from pathlib import Path


def format_time(ms: int) -> str:
    """Format milliseconds as MM:SS,mmm."""
    minutes = ms // 60000
    seconds = (ms % 60000) // 1000
    millis = ms % 1000
    return f"{minutes:02d}:{seconds:02d},{millis:03d}"


def extract_lap_times(log_path: Path) -> dict[str, list[int]]:
    """Parse JSONL and extract lap times for each kart."""
    prev_state: dict[str, int] = {}  # kart -> total_laps
    lap_times: dict[str, list[int]] = {}  # kart -> [lap_time_raw, ...]

    with open(log_path) as f:
        for line in f:
            data = json.loads(line)
            runs = data.get("data", data).get("runs", [])
            for run in runs:
                kart = run["kart"]
                total_laps = run["total_laps"]
                last_time_raw = run["last_time_raw"]

                if kart not in lap_times:
                    lap_times[kart] = []
                    prev_state[kart] = total_laps

                if total_laps > prev_state[kart] and last_time_raw not in (None, "None", 0):
                    lap_times[kart].append(int(last_time_raw))
                    prev_state[kart] = total_laps

    return lap_times


def print_summary(lap_times: dict[str, list[int]]) -> None:
    """Print race summary table sorted by final position (most laps, then lowest total time)."""
    # Sort karts: most laps first, then lowest total time
    karts_sorted = sorted(
        lap_times.items(),
        key=lambda x: (-len(x[1]), sum(x[1])),
    )

    max_laps = max(len(laps) for _, laps in karts_sorted)
    kart_names = [k for k, _ in karts_sorted]
    col_w = 12

    # Header
    print(f"{'Pos':<5}", end="")
    for i in range(len(kart_names)):
        print(f"#{i+1:<{col_w-1}}", end="")
    print()

    print(f"{'Kart':<5}", end="")
    for k in kart_names:
        print(f"{k:<{col_w}}", end="")
    print()

    print(f"{'Laps':<5}", end="")
    for _, laps in karts_sorted:
        print(f"{len(laps):<{col_w}}", end="")
    print()

    # Average
    print(f"{'Avg':<5}", end="")
    for _, laps in karts_sorted:
        avg = sum(laps) // len(laps) if laps else 0
        print(f"{format_time(avg):<{col_w}}", end="")
    print()

    # Best
    print(f"{'Best':<5}", end="")
    for _, laps in karts_sorted:
        best = min(laps) if laps else 0
        print(f"{format_time(best):<{col_w}}", end="")
    print()

    print("-" * (5 + col_w * len(kart_names)))

    # Per-lap times
    for lap_idx in range(max_laps):
        print(f"{lap_idx+1:<5}", end="")
        for _, laps in karts_sorted:
            if lap_idx < len(laps):
                print(f"{format_time(laps[lap_idx]):<{col_w}}", end="")
            else:
                print(f"{'':<{col_w}}", end="")
        print()


if __name__ == "__main__":
    log_file = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("socketio.log")
    if not log_file.exists():
        print(f"File not found: {log_file}", file=sys.stderr)
        sys.exit(1)

    lap_times = extract_lap_times(log_file)
    print_summary(lap_times)
