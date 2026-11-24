import unittest
from datetime import datetime

from model import CONTROL_ACTIONS, KST, SCENARIOS, STATIONS, Quality, State, sample


class SnapshotTest(unittest.TestCase):
    now = datetime(2026, 11, 24, 9, 0, tzinfo=KST)

    def test_missing_and_confirmed_zero_are_different(self):
        missing = sample("missing", self.now)
        idle = sample("idle", self.now)
        self.assertIsNone(missing.run_id)
        self.assertEqual(missing.display_count(0), "—")
        self.assertEqual(missing.display_state(), "미수집")
        self.assertEqual(idle.display_count(0), "0")
        self.assertEqual(idle.display_state(), "정상 대기")

    def test_stale_and_disconnected_snapshots_keep_last_observation_only(self):
        for key, quality, age in (("stale", Quality.STALE, 12), ("offline", Quality.OFFLINE, 36)):
            with self.subTest(scenario=key):
                view = sample(key, self.now)
                self.assertIs(view.quality, quality)
                self.assertEqual(view.display_state("T1"), "확인 불가")
                self.assertEqual(view.last_state("T1"), "운전 중")
                self.assertEqual(view.display_count(0), "—")
                self.assertEqual((self.now - view.observed_at).total_seconds(), age)

    def test_fault_and_paused_production_are_attributed_to_stations(self):
        view = sample("fault", self.now)
        self.assertEqual(set(view.stations), set(STATIONS))
        self.assertIs(view.quality, Quality.GOOD)
        self.assertEqual(view.fault_station, "T3")
        self.assertIs(view.state_at("T3"), State.FAULT)
        self.assertIs(view.state_at("T4"), State.STOPPED)
        self.assertEqual(view.display_count(4), "1")

    def test_controls_remain_disabled_in_every_scenario(self):
        for key in SCENARIOS:
            for action in CONTROL_ACTIONS:
                with self.subTest(scenario=key, action=action):
                    self.assertFalse(sample(key, self.now).control_enabled(action))


if __name__ == "__main__":
    unittest.main()
