import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from spool import EventConflict, EventSpool


def sample(key, sequence, **overrides):
    event = {
        "contract_version": 1,
        "event_key": key,
        "run_id": "QA-RUN",
        "source_id": "qa-bridge",
        "source_session_id": "boot-1",
        "source_sequence": sequence,
        "kind": "TEST_END",
        "station_code": "2A-T1",
        "data_origin": "test",
        "occurred_at": "2026-11-24T09:01:02+09:00",
        "received_at": "2026-11-24T00:01:03Z",
        "timestamp_source": "test-fixture",
        "cell_id": "QA-CELL-1",
        "payload": {"attempt": 1, "ocv_mv": 3695, "ir_mohm": 24},
    }
    return dict(event, **overrides)


class EventSpoolTest(unittest.TestCase):
    def setUp(self):
        folder = TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name) / "events.sqlite3"
        self.spool = EventSpool(self.path)

    def test_restart_and_retry_keep_first_receipt_and_utc_time(self):
        self.assertEqual(self.spool.enqueue_batch([sample("event-a", 1)]), (1, 0))
        retry = sample("event-a", 1, occurred_at="2026-11-24T00:01:02Z", received_at="2026-11-24T00:02:00Z")
        reopened = EventSpool(self.path)
        self.assertEqual(reopened.enqueue_batch([retry]), (0, 1))
        [event] = reopened.pending()
        self.assertEqual(event["occurred_at"], "2026-11-24T00:01:02+00:00")
        self.assertEqual(event["received_at"], "2026-11-24T00:01:03+00:00")

    def test_different_content_with_same_key_rolls_back_the_whole_batch(self):
        self.spool.enqueue_batch([sample("event-a", 1)])
        changed = sample("event-a", 1, payload={"attempt": 2})
        with self.assertRaises(EventConflict):
            self.spool.enqueue_batch([sample("event-b", 2), changed])
        self.assertEqual([e["event_key"] for e in self.spool.pending()], ["event-a"])

    def test_sequence_collision_is_scoped_to_producer_session(self):
        self.spool.enqueue_batch([sample("event-a", 1)])
        with self.assertRaises(EventConflict):
            self.spool.enqueue_batch([sample("event-b", 1)])
        new_session = sample("event-b", 1, source_session_id="boot-2")
        self.assertEqual(self.spool.enqueue_batch([new_session]), (1, 0))
        self.assertEqual([e["event_key"] for e in self.spool.pending()], ["event-a", "event-b"])

    def test_invalid_event_leaves_no_partial_batch(self):
        for invalid in (
            sample("bad", 2, occurred_at="2026-11-24T09:01:02"),
            sample("bad", True),
            sample("bad", 2, contract_version=1.0),
            sample("bad", 2, payload={"ocv_mv": float("nan")}),
        ):
            with self.subTest(event=invalid):
                with self.assertRaises(ValueError):
                    self.spool.enqueue_batch([sample("event-a", 1), invalid])
                self.assertEqual(self.spool.pending(), [])

    def test_delivered_events_remain_deduplicated_after_restart(self):
        self.spool.enqueue_batch([sample("event-a", 1), sample("event-b", 2)])
        self.spool.mark_delivered("event-a", "2026-11-24T00:02:00Z")
        self.spool.mark_delivered("event-a", "2026-11-24T00:03:00Z")
        reopened = EventSpool(self.path)
        self.assertEqual(reopened.enqueue_batch([sample("event-a", 1)]), (0, 1))
        [pending] = reopened.pending(limit=1)
        self.assertEqual(pending["event_key"], "event-b")
