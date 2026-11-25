"""Project confirmed 2A sensor events to a read-only local position snapshot."""

import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3

from spool import read_stream, utc_timestamp


STATIONS = frozenset("IN VIS1 VIS2 RJ1 T1 T2 T3 T4 IDC RT RJ2 SORT LA LB LC BOX OUT".split())
POSITION_KINDS = frozenset({"ID_READ", "CELL_ENTERED", "CELL_EXITED"})


def project_positions(events, *, run_id, source_id, source_session_id, as_of, heartbeat_timeout_seconds):
    """Read one authoritative stream. Input rows use the normalized spool envelope."""
    cutoff = datetime.fromisoformat(utc_timestamp(as_of, "as_of"))
    if heartbeat_timeout_seconds <= 0:
        raise ValueError("heartbeat timeout must be positive")
    timeout = timedelta(seconds=heartbeat_timeout_seconds)
    stream = (run_id, source_id, source_session_id)
    selected = []
    for event in events:
        if (event["run_id"], event["source_id"], event["source_session_id"]) != stream:
            continue
        occurred = datetime.fromisoformat(event["occurred_at"])
        received = datetime.fromisoformat(event["received_at"])
        if occurred <= cutoff and received <= cutoff:
            selected.append((event, received))
    selected.sort(key=lambda pair: pair[0]["source_sequence"])

    origins = {event["data_origin"] for event, _ in selected}
    if len(origins) > 1:
        raise ValueError("The selected source session mixes data origins")
    cells = {}
    last_heartbeat = None
    previous_sequence = None
    missing_sequences = 0
    rejected_observations = 0

    for event, received in selected:
        sequence = event["source_sequence"]
        if previous_sequence is not None:
            missing_sequences += max(sequence - previous_sequence - 1, 0)
        previous_sequence = sequence

        kind = event["kind"]
        if kind == "HEARTBEAT":
            last_heartbeat = max(last_heartbeat, received) if last_heartbeat else received
            continue
        if kind not in POSITION_KINDS:
            continue
        if kind == "ID_READ" and event["payload"].get("result") != "PASS":
            continue
        cell_id = event.get("cell_id")
        station_code = event["station_code"]
        if not cell_id or not station_code.startswith("2A-") or station_code[3:] not in STATIONS:
            rejected_observations += 1
            continue
        if kind == "ID_READ" and station_code != "2A-VIS1":
            continue
        previous = cells.get(cell_id)
        if kind == "ID_READ" and previous:
            continue
        if kind == "CELL_EXITED" and previous and (
            previous["last_station_code"] != station_code or previous["movement"] != "at_station"
        ):
            rejected_observations += 1
            continue
        cells[cell_id] = {
            "cell_id": cell_id,
            "movement": "in_transit" if kind == "CELL_EXITED" else "at_station",
            "last_station_code": station_code,
            "observed_at": event["occurred_at"],
            "received_at": event["received_at"],
            "event_key": event["event_key"],
            "sequence": sequence,
        }

    if last_heartbeat is None:
        source_status = "unobserved"
    elif cutoff - last_heartbeat > timeout:
        source_status = "heartbeat_late"
    else:
        source_status = "recent_heartbeat"

    return {
        "snapshot_version": 1,
        "run_id": run_id,
        "source_id": source_id,
        "source_session_id": source_session_id,
        "data_origin": next(iter(origins), None),
        "as_of": cutoff.isoformat(),
        "source_status": source_status,
        "last_heartbeat_received_at": last_heartbeat.isoformat() if last_heartbeat else None,
        "missing_sequences": missing_sequences,
        "rejected_observations": rejected_observations,
        "cells": [cells[key] for key in sorted(cells)],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--as-of", default=None, help="ISO 8601 with time zone; defaults to current UTC")
    parser.add_argument("--heartbeat-timeout", type=int, required=True, help="Test freshness threshold in seconds")
    args = parser.parse_args()

    try:
        events = read_stream(args.db, args.run_id, args.source_id, args.session_id)
        snapshot = project_positions(
            events, run_id=args.run_id, source_id=args.source_id, source_session_id=args.session_id,
            as_of=args.as_of or datetime.now(timezone.utc).isoformat(),
            heartbeat_timeout_seconds=args.heartbeat_timeout,
        )
    except (OSError, ValueError, sqlite3.Error) as error:
        parser.exit(1, f"Position snapshot error: {error}\n")
    print(json.dumps(snapshot, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
