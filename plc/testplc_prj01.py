"""prj01 test controller (no real PLC). Factory I/O Modbus TCP Client -> 127.0.0.1:502.

Wiring follows the scene's own driver block (written by gen_prj01_v4.py), same scheme as the team's softplc.py:
  bit inputs (sensors) -> coils, then Run/Pause/Reset      bit outputs (actuators) <- discrete inputs
  numeric inputs (vision, Pick & Place positions) -> holding registers   numeric outputs (set points) <- input registers
  ScaleFactor 100: a register holds value x 100.

Only for watching the line move. Grades at the rescan are given in turn (NG, A, B, C), not measured.
Pick & Place positions are estimates (see PNP below); flags let you flip an axis without editing the file.
Usage: python testplc_prj01.py [scene] [--mc-start hold|pulse] [--mc-stop-nc] [--pnp-x-reverse] [--pnp-z-reverse]
"""
import argparse, re, socketserver, struct, threading, time, collections
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("scene", nargs="?", default=str(Path(__file__).resolve().parent.parent / "factoryio" / "scenes" / "prj01.factoryio"))
ap.add_argument("--port", type=int, default=502)
ap.add_argument("--mc-start", choices=("hold", "pulse"), default="hold", help="Machining Center Start: keep ON or 1 s pulse")
ap.add_argument("--mc-stop-nc", action="store_true", help="drive Machining Center Stop ON while running (if it is active-low)")
ap.add_argument("--pnp-x-reverse", action="store_true", help="Pick & Place X: 0 V is the +X end instead of the -X end")
ap.add_argument("--pnp-z-reverse", action="store_true", help="Pick & Place Z: 0 V is down instead of up")
ap.add_argument("--batch", type=int, default=4, help="cells per pallet")
args = ap.parse_args()

# ---------------- scene -> Modbus map ----------------
text = open(args.scene, encoding="utf-8-sig").read()
key_name = {k: n for n, k in re.findall(r'<(?:Binary|Int|Analogue)\w+ Name="([^"]+)" Address="\d+" Key="([^"]+)"', text)}
drv = re.search(r"<ModbusTCPClient>(.*?)</ModbusTCPClient>", text, re.S).group(1)
IN, OUT, NIN, NOUT = {}, {}, {}, {}
for kind, n, key in re.findall(r'<(BitInput|BitOutput|NumericInput|NumericOutput)(\d+) PointIOKey="([^"]+)"', drv):
    name = key_name.get(key)
    if name:
        {"BitInput": IN, "BitOutput": OUT, "NumericInput": NIN, "NumericOutput": NOUT}[kind][name] = int(n)
RUN_COIL = len(IN)                       # Run, Pause, Reset follow the sensors
SCALE = 100

N = 256
coils, hregs, outs, iregs = [False] * N, [0] * N, [False] * N, [0] * N
lock = threading.RLock()
last_rx = [0.0]


class Modbus(socketserver.BaseRequestHandler):
    def recv(self, n):
        b = b""
        while len(b) < n:
            p = self.request.recv(n - len(b))
            if not p:
                raise EOFError
            b += p
        return b

    def handle(self):
        try:
            while True:
                tid, proto, length, unit = struct.unpack(">HHHB", self.recv(7))
                pdu = self.recv(length - 1)
                with lock:
                    resp = self.dispatch(pdu)
                    last_rx[0] = time.monotonic()
                self.request.sendall(struct.pack(">HHHB", tid, 0, len(resp) + 1, unit) + resp)
        except (EOFError, OSError, struct.error):
            pass

    def dispatch(self, pdu):
        fc = pdu[0]
        a, c = struct.unpack(">HH", pdu[1:5])
        if fc in (1, 2, 3, 4, 15, 16) and (not c or a + c > N):
            return bytes([fc | 128, 2])
        if fc in (1, 2):
            src = coils if fc == 1 else outs
            pk = bytearray((c + 7) // 8)
            for i in range(c):
                pk[i // 8] |= int(src[a + i]) << (i % 8)
            return bytes([fc, len(pk)]) + pk
        if fc in (3, 4):
            v = hregs if fc == 3 else iregs
            return bytes([fc, c * 2]) + struct.pack(">" + "H" * c, *[x & 0xFFFF for x in v[a:a + c]])
        if fc == 15:
            for i in range(c):
                coils[a + i] = bool(pdu[6 + i // 8] & (1 << (i % 8)))
            return pdu[:5]
        if fc == 16:
            hregs[a:a + c] = struct.unpack(">" + "h" * c, pdu[6:6 + 2 * c])
            return pdu[:5]
        if fc == 5:
            coils[a] = c == 0xFF00
            return pdu[:5]
        if fc == 6:
            hregs[a] = c
            return pdu[:5]
        return bytes([fc | 128, 1])


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


# ---------------- helpers ----------------
def i(name):
    return coils[IN[name]]


def o(name, v):
    outs[OUT[name]] = bool(v)


def num(name):
    return hregs[NIN[name]] / SCALE


def setnum(name, v):
    iregs[NOUT[name]] = int(round(v * SCALE))


class Edge:
    def __init__(self):
        self.old = {}

    def rise(self, name):
        v = i(name)
        r = v and not self.old.get(name, False)
        self.old[name] = v
        return r

    def rise_db(self, name, now, hold=1.0):
        """rising edge, ignoring re-triggers within `hold` s (one cell can blink a sensor twice)"""
        r = self.rise(name)
        if r and now - self.old.get("t" + name, -99) < hold:
            return False
        if r:
            self.old["t" + name] = now
        return r

    def fall(self, name):
        v = i(name)
        r = (not v) and self.old.get("f" + name, False)
        self.old["f" + name] = v
        return r


def log(msg):
    print(time.strftime("%H:%M:%S"), msg, flush=True)


# ---------------- Pick & Place geometry (ESTIMATES) ----------------
# Gantry centre X 345, Z 102 (cells). Strokes from the docs: X 2.125 m = 17 cells, Y 1.25 m = 10 cells, Z 0.5 m.
# Assumed linear 0..10 V over the stroke; which end is 0 V is not documented (flags flip X and Z).
def vx(x):
    v = (x - 336.5) / 17 * 10
    return 10 - v if args.pnp_x_reverse else v


def vy(z):
    return (z - 97) / 10 * 10


Z_UP = 10.0 if args.pnp_z_reverse else 0.0
Z_STEP = -0.05 if args.pnp_z_reverse else 0.05
PICK = (341, 102)                                   # end of Z5_FEED_BELT (copied from the sample)
SLOTS = [(345.5, 99.5), (350.5, 99.5), (345.5, 104.5), (350.5, 104.5)]   # 2 x 2 on the pallet (pallet centre ~348, 102)


class Line:
    def __init__(self):
        self.e = Edge()
        self.reserved = {1: False, 2: False, 3: False}
        # one queue per pusher position: a cell is in the queue of the next pusher it will pass
        self.q = {k: collections.deque() for k in ('Z2_1', 'Z2_3', 'NG', 'A', 'B', 'C')}
        self.gate_open, self.gate_t, self.gate_seen = False, -99, 99e9
        self.occupied = {1: False, 2: False, 3: False}
        self.z1_queue = 0
        self.occ_t = {1: 0.0, 2: 0.0, 3: 0.0}
        self.push_done = collections.defaultdict(lambda: -99.0)
        self.start_t = {1: -99, 2: -99, 3: -99}
        self.push = {}
        self.gi = 0
        self.last_vision = 0
        self.lane_n = {"A": 0, "B": 0, "C": 0}       # cells waiting in each grade lane
        self.release = None                          # [lane, cells left to let through]
        self.batch_open = False                      # a batch is on its way to / being loaded on the pallet
        self.batch_grade = None
        # pallet
        self.pallet = "none"                         # none -> coming -> ready -> leaving
        self.pallet_t = 0
        self.slot = 0
        self.pallets = 0
        # pick & place
        self.pp, self.pp_t = "home", 0
        self.sp = [vx(PICK[0]), vy(PICK[1]), Z_UP]
        self.z_pick = None
        self.t0 = time.monotonic()

    # Pusher cycle (same order as the team's line_v0 ladder):
    #   sensor 0.625 m before the pusher -> wait DELAY -> stop the belt GROUP ->
    #   push until the front limit -> release and wait for the back limit -> run the group again.
    # A group is every belt joined end to end with the pusher's belt, so nothing upstream keeps shoving cells
    # into a stopped belt and no cell is left half on a running belt (11/19: stopping one belt twisted cells).
    ENTRY = ["Z1_BELT", "Z2_BELT", "Z3_ST2_IN_BELT"]
    SORT = ["Z3_ST1_OUT_BELT", "Z3_ST1_EXT_BELT", "Z3_FROM_ST1_BELT_1", "Z3_FROM_ST1_BELT_2",
            "Z3_ST2_OUT_BELT", "Z3_COLLECT_BELT",
            "Z3_ST3_OUT_BELT", "Z3_ST3_EXT_BELT", "Z3_FROM_ST3_BELT_1", "Z3_FROM_ST3_BELT_2",
            "Z4_BELT_1", "Z4_BELT_2"]
    GROUP = {"Z2_PUSH_1": ENTRY, "Z2_PUSH_3": ENTRY,
             "Z4_PUSH_NG": SORT, "Z4_PUSH_A": SORT, "Z4_PUSH_B": SORT, "Z4_PUSH_C": SORT}
    # DELAY: from the 11/19 16:23 run - belt 0.60 m/s (Z1_IN_SENS -> Z2_AT_GATE, 2.375 m in 3.94 s),
    # cell 0.38 m long (sensor ON 0.63 s). The sensor fires on the cell's front edge, so the cell centre reaches
    # the pusher centre after (0.625 + 0.19) / 0.60 = 1.36 s. (0.5 s used before pushed with the cell 0.5 m short.)
    DELAY = 1.35

    def sees(self, sensor, pusher, now):
        """new cell at a pusher sensor. Ignored while that pusher is moving and 0.8 s after:
        the cell being pushed sideways passes in front of the sensor again (seen in the 11/19 16:23 run)."""
        r = self.e.rise_db(sensor, now)
        moving = pusher in self.push and self.push[pusher][0] != "wait"
        return r and not moving and now - self.push_done[pusher] > 0.8

    def pusher(self, name, now):
        # state: [stage, time the stage started, belt-running seconds waited]
        st = self.push.get(name)
        if st is None:
            o(name, False)
            return
        stage, t0, waited = st
        if stage == "wait":
            o(name, False)
            # count only while this pusher's belt group is running: if another pusher has the group stopped,
            # the cell is not moving towards this pusher either (otherwise it would push too early)
            if not self.group_held(self.GROUP[name], now):
                st[2] = waited = waited + self.dt
            if waited >= self.DELAY:
                self.push[name] = ["out", now, 0.0]
            return
        if stage == "out":
            o(name, True)
            if i(name + "_FWD") or now - t0 > 3.0:
                self.push[name] = ["back", now, 0.0]
        elif stage == "back":
            o(name, False)
            if (i(name + "_BWD") and now - t0 > 0.2) or now - t0 > 3.0:
                del self.push[name]
                self.push_done[name] = now
                return
        for b in self.GROUP[name]:                     # hold the whole group while the pusher is out or returning
            o(b, False)

    def group_held(self, group, now):
        return any(self.push[p][0] != "wait" and self.GROUP[p] is group for p in self.push)

    def at_sp(self, axes="xyz", tol=0.15):
        fb = [num("Z5_PNP_X"), num("Z5_PNP_Y"), num("Z5_PNP_Z")]
        idx = {"x": 0, "y": 1, "z": 2}
        return all(abs(fb[idx[a]] - self.sp[idx[a]]) < tol for a in axes)

    def scan(self):
        now = time.monotonic()
        self.dt = min(now - getattr(self, 'last_scan', now), 0.1)
        self.last_scan = now
        for n in ("Z1_BELT", "Z2_BELT", "Z2_TO_ST1_BELT_1", "Z2_TO_ST1_BELT_2", "Z2_TO_ST3_BELT_1", "Z2_TO_ST3_BELT_2",
                  "Z3_COLLECT_BELT", "Z3_FROM_ST1_BELT_1", "Z3_FROM_ST1_BELT_2", "Z3_FROM_ST3_BELT_1", "Z3_FROM_ST3_BELT_2",
                  "Z4_BELT_1", "Z4_BELT_2", "Z4_NG_BELT", "Z4_LANE_A", "Z4_LANE_B", "Z4_LANE_C", "Z5_COLLECT_BELT"):
            o(n, True)

        # ---- Z1 emitter: only while fewer than 3 cells wait between the emitter and the gate ----
        # (11/19: the emitter kept making a cell every 2-3 s, the queue grew back to the emitter and cells
        # were created on top of each other.)
        if self.e.rise("Z1_IN_SENS"):
            self.z1_queue += 1
        o("Z1_EMITTER", self.z1_queue < 3 and not i("Z1_IN_SENS"))

        # ---- Z3 stations ----
        for n in (1, 2, 3):
            p = f"Z3_ST{n}"
            for b in ("_FEED_BELT", "_IN_BELT", "_OUT_BELT"):
                if p + b in OUT:
                    o(p + b, True)
            # Start: a 0.5 s pulse every 3 s while the station holds a cell and the machine is not busy.
            # (The robot is slow: in the 11/19 17:00 run Busy came ~16 s after the cell reached the entry bay.)
            if self.occupied[n] and not i(p + "_BUSY") and now - self.start_t[n] > 3.0:
                self.start_t[n] = now
            o(p + "_START", now - self.start_t[n] < 0.5)
            o(p + "_STOP", args.mc_stop_nc)
            o(p + "_RESET", False)
            if self.e.rise(p + "_IN"):
                self.reserved[n] = False
                log(f"ST{n} cell at entry")
            if self.e.rise(p + "_BUSY"):
                log(f"ST{n} busy")
            if self.e.rise(p + "_OUT"):                # finished part has left the machine -> station free again
                self.occupied[n] = False
                log(f"ST{n} part out -> free")
        for n in (1, 3):
            o(f"Z3_ST{n}_EXT_BELT", not (i(f"Z3_ST{n}_OUT") and i(f"Z3_MERGE_{n}")))

        # ---- Z2 dispatch ----
        # A station is occupied from the moment a cell is sent to it until its finished part reaches the
        # station's OUT sensor. (Before: "free 3 s after the cell passed the entry" sent a second cell while the
        # robot had not even picked up the first.)
        for n in (1, 2, 3):                            # safety: a lost part must not block a station forever
            if self.occupied[n] and now - self.occ_t[n] > 90:
                self.occupied[n] = False
                log(f"ST{n}: no part out within 90 s -> freed (check the station)")
        def free(n):
            return not self.occupied[n]
        # Gate lets exactly one cell through, timed from the blade going down (belt 0.60 m/s, cell 0.38 m):
        #   only release a cell that has been resting on the blade (sensor ON >= 0.6 s; it is 0.25 m before the blade)
        #   t+0.45 s  cell centre is past the Z1/Z2 joint -> stop Z1 so the next cell stays behind
        #   t+1.00 s  cell tail is past the blade -> raise the blade
        #   t+1.10 s  run Z1 again
        # No release while an entry-group pusher is working (the whole entry group is stopped then).
        if self.e.rise("Z2_AT_GATE"):
            self.gate_seen = now
        if self.gate_open:
            if now - self.gate_t >= 1.0:
                self.gate_open = False
        elif (i("Z2_AT_GATE") and now - self.gate_seen >= 0.6 and now - self.gate_t > 2.0
              and not any(p.startswith("Z2_PUSH") for p in self.push)):
            target = next((n for n in (2, 1, 3) if free(n)), None)
            if target:
                self.reserved[target] = True
                self.occupied[target] = True
                self.occ_t[target] = now
                self.q['Z2_1'].append(target)
                self.gate_open, self.gate_t = True, now
                self.z1_queue = max(0, self.z1_queue - 1)
                log(f"gate -> ST{target}")
        if 0.45 <= now - self.gate_t < 1.1:
            o("Z1_BELT", False)                      # hold the next cell back while the blade is still down
        o("Z2_GATE", not self.gate_open)             # TRUE = blade up = hold
        if self.sees("Z2_AT_PUSH_1", "Z2_PUSH_1", now) and self.q['Z2_1']:
            t = self.q['Z2_1'].popleft()
            if t == 1:
                self.push["Z2_PUSH_1"] = ["wait", now, 0.0]
            else:
                self.q['Z2_3'].append(t)
        if self.sees("Z2_AT_PUSH_3", "Z2_PUSH_3", now) and self.q['Z2_3']:
            if self.q['Z2_3'].popleft() == 3:
                self.push["Z2_PUSH_3"] = ["wait", now, 0.0]
        for n in ("Z2_PUSH_1", "Z2_PUSH_3"):
            self.pusher(n, now)

        # ---- Z4 rescan + sort (grades in turn, test only) ----
        v = hregs[NIN["Z4_QR_RESCAN"]]
        if v and not self.last_vision:
            g = ("NG", "A", "B", "C")[self.gi % 4]; self.gi += 1
            self.q['NG'].append(g)
            log(f"rescan {v / SCALE:g} -> {g}")
        self.last_vision = v
        order = ("NG", "A", "B", "C")
        for k, g in enumerate(order):
            if self.sees(f"Z4_AT_PUSH_{g}", f"Z4_PUSH_{g}", now) and self.q[g]:
                t = self.q[g].popleft()
                if t == g:
                    self.push[f"Z4_PUSH_{g}"] = ["wait", now, 0.0]
                    if g != "NG":
                        self.lane_n[g] += 1
                        log(f"lane {g}: {self.lane_n[g]} waiting")
                elif k + 1 < len(order):
                    self.q[order[k + 1]].append(t)      # passes on to the next pusher
            self.pusher(f"Z4_PUSH_{g}", now)

        # ---- lanes: release a full batch of one grade when the pallet station is free ----
        if self.release is None and not self.batch_open:
            g = next((g for g in ("A", "B", "C") if self.lane_n[g] >= args.batch), None)
            if g:
                self.release = [g, args.batch]
                self.batch_open, self.batch_grade, self.slot = True, g, 0
                log(f"release {args.batch} x {g}")
        # Same blade problem at the lane ends (HEAD sensor is 2 cells before the stop): after the last cell of the
        # batch clears the sensor, stop the lane belt, keep the blade down LANE_HOLD s, then raise it.
        LANE_HOLD = 0.8
        for g in ("A", "B", "C"):
            fell = self.e.fall(f"Z4_LANE_{g}_HEAD")
            if self.release and self.release[0] == g and fell and self.release[1] > 0:
                self.release[1] -= 1
                self.lane_n[g] -= 1
                if self.release[1] == 0:
                    self.release.append(now)             # time the last cell cleared the sensor
            if self.release and self.release[0] == g and self.release[1] == 0:
                o(f"Z4_LANE_{g}", False)
                if now - self.release[2] > LANE_HOLD:
                    self.release = None
            o(f"Z4_LANE_{g}_STOP", not (self.release and self.release[0] == g))

        # ---- Z5 pallet ----
        if self.pallet == "none" and self.batch_open:
            self.pallet, self.pallet_t = "coming", now
        o("Z5_PALLET_EMIT", self.pallet == "coming" and now - self.pallet_t < 0.15)
        if self.pallet == "coming" and i("Z5_PALLET_AT_PLACE"):
            self.pallet, self.pallet_t = "settle", now
        if self.pallet == "settle" and now - self.pallet_t > 0.5:
            self.pallet = "ready"; log("pallet ready")
        if self.pallet == "ready" and self.slot >= args.batch and self.pp == "home":
            self.pallet, self.pallet_t = "leaving", now
            log(f"pallet with {args.batch} x {self.batch_grade} -> 2B")
        if self.pallet == "leaving" and not i("Z5_PALLET_AT_PLACE") and now - self.pallet_t > 6:
            self.pallets += 1
            self.pallet, self.batch_open = "none", False
            log(f"pallet {self.pallets} handed to 2B")
        o("Z5_PALLET_ROLLER", self.pallet in ("coming", "leaving"))
        o("Z5_EXIT_ROLLER", self.pallet == "leaving")

        # ---- Z5 feed: hold the cell at the pick point ----
        o("Z5_FEED_BELT", not i("Z5_AT_PICK"))

        # ---- Pick & Place (XYZ analog) ----
        t = now - self.pp_t
        def go(state):
            self.pp, self.pp_t = state, now
        if self.pp == "home":
            self.sp = [vx(PICK[0]), vy(PICK[1]), Z_UP]
            o("Z5_PNP_GRAB", False)
            if self.pallet == "ready" and self.slot < args.batch and i("Z5_AT_PICK") and (self.at_sp() or t > 3):
                go("down")
        elif self.pp == "down":                      # lower step by step until the gripper sees the cell
            if i("Z5_PNP_DETECTED"):
                self.z_pick = self.sp[2]; o("Z5_PNP_GRAB", True); go("grab")
            elif 0 <= self.sp[2] + Z_STEP <= 10:
                self.sp[2] += Z_STEP * (1 if self.at_sp("z", 0.3) else 0)
            elif t > 8:
                log(f"pick: no cell detected (Z {num('Z5_PNP_Z'):.2f} V) -> back up"); go("home")
        elif self.pp == "grab" and t > 0.6:
            self.sp[2] = Z_UP; go("lift")
        elif self.pp == "lift" and (self.at_sp("z") or t > 3):
            x, z = SLOTS[self.slot]
            self.sp[0], self.sp[1] = vx(x), vy(z); go("move")
        elif self.pp == "move" and (self.at_sp("xy") or t > 4):
            self.sp[2] = self.z_pick - 0.5 * (1 if Z_STEP > 0 else -1); go("place")
        elif self.pp == "place" and (self.at_sp("z") or t > 3):
            o("Z5_PNP_GRAB", False); go("release")
        elif self.pp == "release" and t > 0.6:
            self.sp[2] = Z_UP
            self.slot += 1
            log(f"placed {self.slot}/{args.batch}  (X {num('Z5_PNP_X'):.2f} Y {num('Z5_PNP_Y'):.2f} V)")
            go("home")
        setnum("Z5_PNP_SP_X", self.sp[0]); setnum("Z5_PNP_SP_Y", self.sp[1]); setnum("Z5_PNP_SP_Z", self.sp[2])
        o("Z5_PNP_C_TURN", False)
        o("LAMP_GREEN_RUN", True)


def main():
    line = None
    with Server(("127.0.0.1", args.port), Modbus) as srv:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        print(f"prj01 test controller on 127.0.0.1:{args.port}  ({len(IN)} bit in / {len(OUT)} bit out / "
              f"{len(NIN)} num in / {len(NOUT)} num out)", flush=True)
        print("Factory I/O: driver Modbus TCP/IP Client, press Play. Ctrl+C to quit.", flush=True)
        linked_before = False
        trace = open(Path(__file__).with_name("testplc_trace.log"), "w", encoding="utf-8")
        names_in = {v: k for k, v in IN.items()}
        names_out = {v: k for k, v in OUT.items()}
        prev_in, prev_out = list(coils), list(outs)
        t_start = time.monotonic()
        try:
            while True:
                with lock:
                    linked = time.monotonic() - last_rx[0] < 1
                    if linked != linked_before:
                        log("Factory I/O connected" if linked else "Factory I/O not connected")
                        linked_before = linked
                    run = linked and coils[RUN_COIL] and not coils[RUN_COIL + 2]
                    if not run:
                        line = None
                        outs[:] = [False] * N
                        iregs[:] = [0] * N
                    elif not coils[RUN_COIL + 1]:
                        if line is None:
                            line = Line(); log("scene running")
                        line.scan()
                    # every signal change, with seconds since start: "+" = turned ON, "-" = turned OFF
                    ts = time.monotonic() - t_start
                    for a, n in names_in.items():
                        if coils[a] != prev_in[a]:
                            trace.write(f"{ts:8.2f} IN  {'+' if coils[a] else '-'} {n}\n")
                    for a, n in names_out.items():
                        if outs[a] != prev_out[a]:
                            trace.write(f"{ts:8.2f} OUT {'+' if outs[a] else '-'} {n}\n")
                    prev_in, prev_out = list(coils), list(outs)
                    trace.flush()
                time.sleep(0.01)
        except KeyboardInterrupt:
            pass
        finally:
            with lock:
                outs[:] = [False] * N


if __name__ == "__main__":
    main()
