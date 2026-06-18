#!/usr/bin/env python3
"""Replay a JSONL race log via Socket.IO at accelerated speed.

Usage: python tools/replay_race.py [logfile] [--speed 5] [--port 8080] [--channel kartarenacheb]
"""

import argparse
import asyncio
import json
from datetime import datetime
from pathlib import Path

import socketio
from aiohttp import web


def parse_log_ts(ts: str) -> float:
    """Parse 'YYYY-MM-DD HH:MM:SS,mmm' to epoch seconds."""
    return datetime.strptime(ts, "%Y-%m-%d %H:%M:%S,%f").timestamp()


async def replay(app, log_path: Path, channel: str, speed: float):
    """Read log lines and emit them respecting inter-message timing."""
    sio = app["sio"]
    messages = []
    with open(log_path) as f:
        for line in f:
            msg = json.loads(line)
            messages.append(msg)

    if not messages:
        print("No messages in log.")
        return

    print(f"Replaying {len(messages)} messages from {log_path.name} at {speed}× speed")

    first_log_ts = parse_log_ts(messages[0]["log_ts"])
    prev_ts = first_log_ts
    replay_start = asyncio.get_event_loop().time()

    for i, msg in enumerate(messages):
        ts = parse_log_ts(msg["log_ts"])
        delay = (ts - prev_ts) / speed
        if delay > 0:
            await asyncio.sleep(delay)
        prev_ts = ts

        # Shift timestamps: the offset between original log time and current
        # wall time, so elapsed calculations in the browser are correct.
        import time
        now_wall = time.time()
        msg_offset = now_wall - ts
        shifted = shift_timestamps(msg, msg_offset)
        await sio.emit(channel, shifted)
        elapsed = ts - first_log_ts
        print(f"  [{i+1}/{len(messages)}] {msg['log_ts']}  (race +{elapsed:.0f}s)", end="\r")

    print(f"\nReplay complete. {len(messages)} messages sent.")


def shift_timestamps(msg, offset: float) -> dict:
    """Shift all timestamps in a message by offset seconds."""
    import copy

    shifted = copy.deepcopy(msg)
    runs = shifted.get("data", shifted).get("runs", [])
    for run in runs:
        if run.get("current_lap_start_timestamp") and run["current_lap_start_timestamp"] > 0:
            run["current_lap_start_timestamp"] = int(run["current_lap_start_timestamp"] + offset)
        if run.get("current_lap_start_microtimestamp") and run["current_lap_start_microtimestamp"] > 0:
            run["current_lap_start_microtimestamp"] = int(run["current_lap_start_microtimestamp"] + offset * 1000)
        if run.get("last_passing") and run["last_passing"] > 0:
            run["last_passing"] = int(run["last_passing"] + offset * 1000)

    return shifted


def main():
    parser = argparse.ArgumentParser(description="Replay race log via Socket.IO")
    parser.add_argument("logfile", nargs="?",
                        default="socketio/socketio Cheb RaceA 20250413.log",
                        help="Path to JSONL log file")
    parser.add_argument("--speed", type=float, default=5, help="Replay speed multiplier")
    parser.add_argument("--port", type=int, default=8080, help="Server port")
    parser.add_argument("--channel", default="kartarenacheb", help="Socket.IO channel name")
    args = parser.parse_args()

    log_path = Path(args.logfile)
    if not log_path.exists():
        print(f"File not found: {log_path}")
        return

    sio = socketio.AsyncServer(cors_allowed_origins="*")
    app = web.Application()
    sio.attach(app)
    app["sio"] = sio

    @sio.event
    async def connect(sid, environ):
        print(f"Client connected: {sid}")

    @sio.event
    async def disconnect(sid):
        print(f"Client disconnected: {sid}")

    async def start_replay(app):
        app["replay_task"] = asyncio.create_task(
            replay(app, log_path, args.channel, args.speed)
        )

    app.on_startup.append(start_replay)

    print(f"Starting replay server on port {args.port} (channel: {args.channel})")
    print(f"Start the app with: WS_URL=http://localhost:{args.port} python server.py")
    web.run_app(app, port=args.port, print=None)


if __name__ == "__main__":
    main()
