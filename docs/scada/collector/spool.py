"""Local durable queue for normalized 2A collector events."""

import argparse
import json
import sqlite3
from contextlib import closing, contextmanager
from datetime import datetime, timezone
from pathlib import Path


TEXT_FIELDS = (
    "event_key", "run_id", "source_id", "source_session_id", "kind", "station_code",
    "data_origin", "timestamp_source",
)
OPTIONAL_IDS = ("cell_id", "input_ref", "inspection_id", "kit_id")
STREAM_FIELDS = ("run_id", "source_id", "source_session_id", "source_sequence")
DEFAULT_PATH = Path(__file__).resolve().parents[1] / ".local" / "collector-spool.sqlite3"


class EventConflict(ValueError):
    """A previously stored event key or stream sequence has different content."""


def utc_timestamp(value, name):
    if not isinstance(value, str):
        raise ValueError(f"{name} must be an ISO 8601 timestamp with an offset")
    try:
        iso_value = value[:-1] + "+00:00" if value.endswith("Z") else value
        parsed = datetime.fromisoformat(iso_value)
        if parsed.utcoffset() is None:
            raise ValueError
        return parsed.astimezone(timezone.utc).isoformat()
    except (ValueError, OverflowError) as error:
        raise ValueError(f"{name} must be an ISO 8601 timestamp with an offset") from error


def encode(event):
    return json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def normalize(event):
    if not isinstance(event, dict):
        raise ValueError("Expected a version 1 event object")
    version = event.get("contract_version")
    if type(version) not in (int, str) or version not in (1, "1"):
        raise ValueError("Only local draft contract version 1 is supported")
    normalized = dict(event, contract_version=1)
    for name in TEXT_FIELDS + OPTIONAL_IDS:
        value = normalized.get(name)
        if value is None and name in OPTIONAL_IDS:
            normalized.pop(name, None)
            continue
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} must be a non-empty string")
    sequence = normalized.get("source_sequence")
    if type(sequence) is not int or not 0 <= sequence < 2**63:
        raise ValueError("source_sequence must be a nonnegative 64-bit integer")
    if not isinstance(normalized.get("payload"), dict):
        raise ValueError("payload must be a JSON object")
    for name in ("occurred_at", "received_at"):
        normalized[name] = utc_timestamp(normalized.get(name), name)
    return normalized


class EventSpool:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.execute("PRAGMA journal_mode = WAL")
            db.execute("""
                CREATE TABLE IF NOT EXISTS spool (
                    id INTEGER PRIMARY KEY,
                    event_key TEXT NOT NULL UNIQUE,
                    run_id TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    source_session_id TEXT NOT NULL,
                    source_sequence INTEGER NOT NULL,
                    body TEXT NOT NULL,
                    delivered_at TEXT,
                    UNIQUE (run_id, source_id, source_session_id, source_sequence)
                )
            """)

    @contextmanager
    def connection(self):
        with closing(sqlite3.connect(self.path, timeout=5)) as db:
            db.execute("PRAGMA synchronous = FULL")
            with db:
                yield db

    def enqueue_batch(self, events):
        """Commit all events before returning counts suitable for acknowledging persistence."""
        added = duplicates = 0
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            for raw in events:
                event = normalize(raw)
                key = event["event_key"]
                stream = tuple(event[field] for field in STREAM_FIELDS)
                prior = db.execute("SELECT body FROM spool WHERE event_key = ?", (key,)).fetchone()
                if prior is not None:
                    stored = json.loads(prior[0])
                    stored["received_at"] = event["received_at"]
                    if encode(stored) != encode(event):
                        raise EventConflict(f"Different content for event key {key}")
                    duplicates += 1
                    continue
                try:
                    db.execute("""
                        INSERT INTO spool (event_key, run_id, source_id, source_session_id, source_sequence, body)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (key, *stream, encode(event)))
                except sqlite3.IntegrityError as error:
                    raise EventConflict(f"Stream sequence already recorded under a different event key: {key}") from error
                added += 1
        return added, duplicates

    def pending(self, limit=100):
        """Read yet-unconfirmed events in local arrival order."""
        if type(limit) is not int or not 0 < limit < 2**63:
            raise ValueError("limit must be a positive 64-bit integer")
        with self.connection() as db:
            rows = db.execute(
                "SELECT body FROM spool WHERE delivered_at IS NULL ORDER BY id LIMIT ?", (limit,)
            )
            return [json.loads(body) for body, in rows]

    def mark_delivered(self, event_key, delivered_at):
        """Called by a future single sender after the destination confirms its commit."""
        stamp = utc_timestamp(delivered_at, "delivered_at")
        with self.connection() as db:
            row = db.execute(
                "UPDATE spool SET delivered_at = COALESCE(delivered_at, ?) WHERE event_key = ?",
                (stamp, event_key),
            )
            if not row.rowcount:
                raise KeyError(event_key)


def read_jsonl(path):
    with path.open(encoding="utf-8-sig") as source:
        for number, line in enumerate(source, 1):
            if line.strip():
                try:
                    yield json.loads(line)
                except json.JSONDecodeError as error:
                    raise ValueError(f"Invalid JSON on line {number}") from error


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_PATH)
    commands = parser.add_subparsers(dest="command", required=True)
    enqueue = commands.add_parser("enqueue", help="Commit a local JSONL file as one batch")
    enqueue.add_argument("file", type=Path)
    pending = commands.add_parser("pending", help="Print locally queued JSONL events")
    pending.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()

    try:
        spool = EventSpool(args.db)
        if args.command == "enqueue":
            added, duplicates = spool.enqueue_batch(read_jsonl(args.file))
            print(f"Committed {added} new events; {duplicates} duplicates")
        else:
            for event in spool.pending(args.limit):
                print(encode(event))
    except (OSError, TypeError, ValueError, sqlite3.Error) as error:
        parser.exit(1, f"Spool error: {error}\n")


if __name__ == "__main__":
    main()
