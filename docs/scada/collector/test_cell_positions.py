from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from cell_positions import project_positions
from spool import EventSpool, read_jsonl, read_stream


FIXTURE = Path(__file__).with_name("fixtures") / "cell_positions.jsonl"
STREAM = {"run_id": "QA-POSITION", "source_id": "qa-bridge", "source_session_id": "boot-1"}


def snapshot(events, at="2026-11-25T09:00:06+09:00", **stream):
    return project_positions(events, as_of=at, heartbeat_timeout_seconds=10, **(STREAM | stream))


class PositionTest(unittest.TestCase):
    def test_arrival_order_and_retries_do_not_mix_two_cells(self):
        fixture = list(read_jsonl(FIXTURE))
        with TemporaryDirectory() as root:
            path = Path(root) / "position.sqlite3"
            spool = EventSpool(path)
            self.assertEqual(spool.enqueue_batch(reversed(fixture)), (6, 0))
            self.assertEqual(spool.enqueue_batch(fixture), (0, 6))
            spool.mark_delivered("pos-5", "2026-11-25T09:00:06+09:00")
            result = snapshot(read_stream(path, **STREAM))
        self.assertEqual(result["missing_sequences"], 0)
        self.assertEqual([(c["cell_id"], c["last_station_code"]) for c in result["cells"]],
                         [("QA-001", "2A-T2"), ("QA-002", "2A-T4")])

    def test_leaving_does_not_predict_the_next_station(self):
        result = snapshot(read_jsonl(FIXTURE), at="2026-11-25T09:00:03+09:00")
        first, second = result["cells"]
        self.assertEqual((first["movement"], first["last_station_code"]), ("in_transit", "2A-VIS1"))
        self.assertEqual((second["movement"], second["last_station_code"]), ("at_station", "2A-VIS1"))

    def test_late_input_and_wrong_station_exit_do_not_override_current_location(self):
        events = list(read_jsonl(FIXTURE))
        events[5]["received_at"] = "2026-11-25T09:00:08+09:00"
        earlier = snapshot(events)
        self.assertEqual(earlier["cells"][1]["last_station_code"], "2A-VIS1")
        events.append(dict(events[3], event_key="pos-8", source_sequence=8))
        result = snapshot(events, at="2026-11-25T09:00:09+09:00")
        self.assertEqual(result["missing_sequences"], 1)
        self.assertEqual(result["rejected_observations"], 1)
        self.assertEqual(result["cells"][0]["last_station_code"], "2A-T2")
        self.assertEqual(result["cells"][1]["last_station_code"], "2A-T4")

    def test_stale_heartbeat_keeps_last_observation_and_new_session_starts_empty(self):
        events = list(read_jsonl(FIXTURE))
        self.assertEqual(snapshot(events)["source_status"], "recent_heartbeat")
        old = snapshot(events, at="2026-11-25T09:00:11+09:00")
        self.assertEqual(old["source_status"], "heartbeat_late")
        self.assertEqual(old["cells"][0]["last_station_code"], "2A-T2")
        for changes in ({"run_id": "other"}, {"source_session_id": "boot-2"}):
            result = snapshot(events, **changes)
            self.assertEqual(result["source_status"], "unobserved")
            self.assertEqual(result["cells"], [])


if __name__ == "__main__":
    unittest.main()
