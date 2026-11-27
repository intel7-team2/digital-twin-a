import random
import sys
import unittest
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sim  # noqa: E402


class SimTest(unittest.TestCase):
    def test_grade_bounds(self):
        b = (3650, 3750)
        self.assertEqual(sim.grade(3750, b), "A")
        self.assertEqual(sim.grade(3749, b), "B")
        self.assertEqual(sim.grade(3650, b), "B")
        self.assertEqual(sim.grade(3649, b), "C")

    def test_bin_kits_stay_inside_one_band(self):
        sc = replace(sim.BASE, cells=400)
        r = sim.run_once(sc, random.Random(3))
        widest = max(sc.spec[1] - sc.bounds[1], sc.bounds[1] - sc.bounds[0], sc.bounds[0] - sc.spec[0])
        self.assertTrue(all(x <= widest for x in r.bin_ranges))

    def test_cells_are_conserved(self):
        r = sim.run_once(sim.BASE, random.Random(5))
        self.assertEqual(r.bin_kits * sim.KIT_SIZE + r.bin_left, r.passed)
        self.assertLessEqual(r.order_kits * sim.KIT_SIZE, r.passed)

    def test_rejects_never_enter_kits(self):
        sc = replace(sim.BASE, defect_rate=1.0)
        r = sim.run_once(sc, random.Random(7))
        self.assertEqual(r.passed, 0)
        self.assertEqual(r.bin_kits, 0)

    def test_same_seed_same_result(self):
        a = sim.summarize(sim.BASE, runs=20, seed=11)
        b = sim.summarize(sim.BASE, runs=20, seed=11)
        self.assertEqual(a["reduction"], b["reduction"])

    def test_binning_reduces_deviation(self):
        s = sim.summarize(sim.BASE, runs=50)
        self.assertGreater(s["reduction"], 0)


if __name__ == "__main__":
    unittest.main()
