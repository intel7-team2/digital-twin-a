import unittest
from dataclasses import replace
from datetime import datetime, timedelta

from model import (
    CONTROL_ACTIONS, KST, SAMPLE_MAX_AGE, SCENARIOS, STATIONS,
    BridgeObservation, OperationPractice, Quality, State, project_observation, sample, sample_observation,
)


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

    def test_age_and_link_determine_quality_independently_of_equipment_fault(self):
        fault = sample_observation("fault", self.now)
        at_limit = self.now + SAMPLE_MAX_AGE
        self.assertIs(project_observation("test", fault, at_limit).quality, Quality.GOOD)
        stale = project_observation("test", fault, at_limit + timedelta(milliseconds=1))
        self.assertIs(stale.quality, Quality.STALE)
        self.assertEqual(stale.last_state("T3"), "설비 이상")
        self.assertIsNone(stale.fault_station)
        self.assertIsNone(stale.handoff)
        offline = project_observation("test", replace(fault, plc_connected=False), self.now)
        self.assertIs(offline.quality, Quality.OFFLINE)
        self.assertEqual(offline.display_state("T3"), "확인 불가")

    def test_missing_observation_partial_values_and_new_round(self):
        no_sample = project_observation("test", BridgeObservation(plc_connected=True), self.now)
        self.assertIs(no_sample.quality, Quality.MISSING)
        idle = sample_observation("idle", self.now)
        partial = project_observation("test", replace(idle, counts=(0, None, 0, 0, 0), stations={}), self.now)
        self.assertEqual(partial.display_count(0), "0")
        self.assertEqual(partial.display_count(1), "—")
        self.assertEqual(partial.display_state("T1"), "미수집")
        no_run = project_observation("test", replace(idle, run_id=None), self.now)
        self.assertEqual(no_run.display_count(0), "—")
        self.assertIsNone(no_run.handoff)
        self.assertNotEqual(sample("running", self.now).run_id, partial.run_id)

    def test_controls_remain_disabled_in_every_scenario(self):
        for key in SCENARIOS:
            for action in CONTROL_ACTIONS:
                with self.subTest(scenario=key, action=action):
                    self.assertFalse(sample(key, self.now).control_enabled(action))

    def test_practice_start_repeat_stop_and_reset_while_running(self):
        practice = OperationPractice("practice")
        self.assertIs(practice.snapshot(self.now).line_state, State.IDLE)
        self.assertTrue(practice.command("START").applied)
        self.assertIs(practice.snapshot(self.now).line_state, State.BUSY)
        self.assertEqual(practice.command("START").reason, "이미 운전 중")
        self.assertFalse(practice.command("RESET").applied)
        self.assertIs(practice.snapshot(self.now).line_state, State.BUSY)
        self.assertTrue(practice.command("STOP").applied)
        self.assertIs(practice.snapshot(self.now).line_state, State.STOPPED)
        self.assertEqual(practice.snapshot(self.now).display_count(0), "0")

    def test_practice_reset_clears_training_fault_but_keeps_lot_hold(self):
        practice = OperationPractice("practice_hold")
        self.assertIs(practice.snapshot(self.now).state_at("T3"), State.FAULT)
        self.assertFalse(practice.command("START").applied)
        self.assertEqual(practice.result.reason, "LOT 보류")
        self.assertTrue(practice.command("RESET").applied)
        self.assertTrue(practice.lot_hold)
        self.assertIs(practice.snapshot(self.now).state_at("T3"), State.STOPPED)
        self.assertFalse(practice.command("START").applied)
        self.assertTrue(practice.command("STOP").applied)


if __name__ == "__main__":
    unittest.main()
