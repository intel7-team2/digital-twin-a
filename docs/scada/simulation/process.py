import random
import sqlite3
import uuid
from collections import deque
from contextlib import contextmanager


# Demo calibration only. Group assignment uses the two measured values.
CENTERS = {"A": (3.64, 22.0), "B": (3.73, 18.0), "C": (3.82, 25.0)}


@contextmanager
def connect(path):
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    try:
        with connection:
            yield connection
    finally:
        connection.close()


class Simulation:
    def __init__(self, path, seed):
        self.path = path
        self.random = random.Random(seed)
        self.run_id = f"SIM-{uuid.uuid4().hex}"
        self.step = 0
        self.last_stamp = 0
        self.vision = None
        self.test = None
        self.sort = None
        self.kit_count = 0
        self.buffers = {group: deque() for group in CENTERS}
        with connect(path) as db:
            db.execute("PRAGMA journal_mode = WAL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS events (
                    event_id INTEGER PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    stamp INTEGER NOT NULL,
                    kind TEXT NOT NULL,
                    cell_id TEXT,
                    result TEXT,
                    ocv_v REAL,
                    ir_mohm REAL,
                    group_code TEXT,
                    kit_id TEXT,
                    slot INTEGER
                );
                CREATE INDEX IF NOT EXISTS events_by_run_time ON events(run_id, stamp, event_id);
                CREATE INDEX IF NOT EXISTS events_by_cell ON events(cell_id, event_id);
                CREATE INDEX IF NOT EXISTS events_by_kit ON events(kit_id, event_id);
            """)

    def tick(self, stamp):
        # The producer exits on write failure. HTTP reads observe committed ticks only.
        stamp = max(stamp, self.last_stamp + 1)
        self.last_stamp = stamp
        self.step += 1
        pending = []

        def record(kind, cell=None, result=None, ocv=None, ir=None, group=None, kit=None, slot=None):
            pending.append((self.run_id, stamp, kind, cell, result, ocv, ir, group, kit, slot))

        # Pack cells already buffered at the start of this tick, FIFO within each group.
        for group, buffer in self.buffers.items():
            if len(buffer) >= 4:
                self.kit_count += 1
                kit = f"{self.run_id}-K{self.kit_count:06d}"
                for slot in range(1, 5):
                    record("PACKED", cell=buffer.popleft(), group=group, kit=kit, slot=slot)
                record("KIT_CREATED", group=group, kit=kit)

        if self.sort:
            cell, ocv, ir = self.sort
            group = min(CENTERS, key=lambda name: self.distance(name, ocv, ir))
            self.buffers[group].append(cell)
            record("SORTED", cell=cell, group=group)

        self.sort = None
        if self.test:
            cell, number = self.test
            ocv, ir = self.measure(number)
            passed = 3.55 <= ocv <= 3.92 and 14 <= ir <= 32
            record("ELECTRICAL", cell=cell, result="PASS" if passed else "FAIL", ocv=ocv, ir=ir)
            if passed:
                self.sort = cell, ocv, ir

        self.test = None
        if self.vision:
            cell, number = self.vision
            passed = number % 11 != 5
            record("VISION", cell=cell, result="PASS" if passed else "FAIL")
            if passed:
                self.test = self.vision

        cell = f"{self.run_id}-C{self.step:06d}"
        record("ID_ASSIGNED", cell=cell)
        self.vision = cell, self.step

        with connect(self.path) as db:
            db.executemany("""
                INSERT INTO events(run_id, stamp, kind, cell_id, result, ocv_v, ir_mohm, group_code, kit_id, slot)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, pending)

    @staticmethod
    def distance(group, ocv, ir):
        center_v, center_ir = CENTERS[group]
        return ((ocv - center_v) / 0.04) ** 2 + ((ir - center_ir) / 4.0) ** 2

    def measure(self, number):
        if number % 17 == 8:
            return 3.45, 38.0
        center_v, center_ir = CENTERS["ABC"[(number - 1) % 3]]
        return (
            round(center_v + self.random.uniform(-0.012, 0.012), 3),
            round(center_ir + self.random.uniform(-1.2, 1.2), 2),
        )
