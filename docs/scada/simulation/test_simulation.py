import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from process import CENTERS, Simulation, connect
from server import METRICS, PREFIX, read_history, render


class SimulationTest(unittest.TestCase):
    def setUp(self):
        folder = TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name) / "simulation.sqlite3"
        self.simulation = Simulation(self.path, seed=42)
        self.first = 1_800_000_000
        self.last = self.first + 59
        for stamp in range(self.first, self.last + 1):
            self.simulation.tick(stamp)
        with connect(self.path) as db:
            self.events = db.execute("SELECT * FROM events ORDER BY event_id").fetchall()

    def test_grafana_graphite_ref_id_alias_preserves_values_and_query_identity(self):
        metric = f"{PREFIX}production.cells"
        plain = render(self.path, self.simulation.run_id, [metric], self.first, self.last)
        queries = [rf'aliasSub({metric}, "(^.*$)", "\1 {ref}")' for ref in ("A", "B")]
        wrapped = render(self.path, self.simulation.run_id, queries, self.first, self.last)
        self.assertEqual(wrapped, [
            {"target": f"{metric} {ref}", "datapoints": plain[0]["datapoints"]} for ref in ("A", "B")
        ])
        with self.assertRaisesRegex(ValueError, "exact cellect.sim metric"):
            render(self.path, self.simulation.run_id, [f"sumSeries({metric})"], self.first, self.last)

    def test_cell_progression_and_kit_composition(self):
        cells = {}
        kits = {}
        for event in self.events:
            if event["cell_id"]:
                cells.setdefault(event["cell_id"], []).append(event)
            if event["kit_id"]:
                kits.setdefault(event["kit_id"], []).append(event)

        self.assertEqual(len(cells), 60)
        rejected_at = set()
        for history in cells.values():
            stages = [event["kind"] for event in history]
            self.assertEqual(stages, ["ID_ASSIGNED", "VISION", "ELECTRICAL", "SORTED", "PACKED"][:len(stages)])
            stamps = [event["stamp"] for event in history]
            self.assertEqual(stamps, sorted(set(stamps)))
            for event in history[:-1]:
                if event["kind"] in ("VISION", "ELECTRICAL"):
                    self.assertEqual(event["result"], "PASS")
            if history[-1]["result"] == "FAIL":
                rejected_at.add(history[-1]["kind"])
            if "SORTED" in stages:
                measurement, sort_event = history[2:4]
                nearest = min(CENTERS, key=lambda group: self.simulation.distance(
                    group, measurement["ocv_v"], measurement["ir_mohm"]
                ))
                self.assertEqual(sort_event["group_code"], nearest)
        self.assertEqual(rejected_at, {"VISION", "ELECTRICAL"})

        self.assertGreater(len(kits), 0)
        packed_cells = set()
        for events in kits.values():
            packed = events[:-1]
            self.assertEqual([row["kind"] for row in events], ["PACKED"] * 4 + ["KIT_CREATED"])
            self.assertEqual([row["slot"] for row in packed], [1, 2, 3, 4])
            self.assertEqual({row["group_code"] for row in packed}, {events[-1]["group_code"]})
            for row in packed:
                cell = row["cell_id"]
                self.assertNotIn(cell, packed_cells)
                packed_cells.add(cell)
                self.assertEqual(cells[cell][-2]["group_code"], row["group_code"])

    def test_grafana_metrics_match_ledger_at_each_tick_in_requested_window(self):
        start = self.first + 10
        targets = [PREFIX + name for name in METRICS]
        frames = render(self.path, self.simulation.run_id, targets, start, self.last)
        points = {frame["target"].removeprefix(PREFIX): {
            stamp: value for value, stamp in frame["datapoints"]
        } for frame in frames}
        self.assertTrue(all(set(values) == set(range(start, self.last + 1)) for values in points.values()))
        for stamp in range(start, self.last + 1):
            history = [event for event in self.events if event["stamp"] <= stamp]
            self.assertEqual(points["production.cells"][stamp], sum(row["kind"] == "ID_ASSIGNED" for row in history))
            self.assertEqual(points["kits.total"][stamp], sum(row["kind"] == "KIT_CREATED" for row in history))
            for kind in ("VISION", "ELECTRICAL"):
                for result in ("PASS", "FAIL"):
                    self.assertEqual(points[f"{kind.lower()}.{result.lower()}"][stamp], sum(
                        row["kind"] == kind and row["result"] == result for row in history
                    ))
            for group in CENTERS:
                sorted_cells = {row["cell_id"] for row in history
                                if row["kind"] == "SORTED" and row["group_code"] == group}
                packed_cells = {row["cell_id"] for row in history
                                if row["kind"] == "PACKED" and row["group_code"] == group}
                self.assertEqual(points[f"buffer.{group}"][stamp], len(sorted_cells - packed_cells))
            test = next((row for row in history if row["kind"] == "ELECTRICAL" and row["stamp"] == stamp), None)
            for field in ("ocv_v", "ir_mohm"):
                self.assertEqual(points[f"electrical.{field}"][stamp], test[field] if test else None)

    def test_restart_preserves_history_and_excludes_previous_run_from_graphs(self):
        previous_cell = self.events[0]["cell_id"]
        new_run = Simulation(self.path, seed=42)
        new_run.tick(self.last + 1)
        history = read_history(self.path, new_run.run_id, previous_cell, "")
        self.assertEqual(history[0]["run_id"], self.simulation.run_id)
        frames = render(self.path, new_run.run_id, [PREFIX + "production.cells"], self.first, self.last + 1)
        self.assertEqual(frames[0]["datapoints"], [[1, self.last + 1]])

    def test_inspection_timestamp_opens_matching_cell_history(self):
        measurement = next(event for event in self.events if event["kind"] == "ELECTRICAL")
        rows = read_history(self.path, self.simulation.run_id, "", "", test_stamp=measurement["stamp"])
        self.assertEqual({row["cell_id"] for row in rows}, {measurement["cell_id"]})
        self.assertIn(dict(measurement), rows)


if __name__ == "__main__":
    unittest.main()
