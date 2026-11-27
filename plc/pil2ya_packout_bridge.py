"""Analog Pick & Place 2 bridge. The ladder owns all motion sequencing."""
import argparse
from pathlib import Path
import struct

import pil2ya_packout_transport as base

# Provisional solo-test map, within the team's ② and ③ allocations.
# The bridge writes only the inputs below. The ladder owns all outputs.
INPUTS = {
    "Run": "M2501", "Pause": "M2502", "Reset": "M2503",
    "Diffuse Sensor 4": "M2510",
    "Pusher 1 (Front Limit)": "M2511", "Pusher 1 (Back Limit)": "M2512",
    "Retroreflective Sensor 0": "M2710", "Retroreflective Sensor 4": "M2711",
    "Unused coil 8": None, "Unused coil 9": None,
    "Pick & Place 2 (Box Detected)": "M2714",
    "Turntable 2 (Limit 0)": "M2715", "Turntable 2 (Limit 90)": "M2716",
    "Turntable 2 (Front Limit)": "M2717", "Turntable 2 (Back Limit)": "M2718",
    "Right Positioner 0 (Limit)": "M2719", "Right Positioner 0 (Clamped)": "M2720",
}
OUTPUTS = {
    "Emitter 0 (Emit)": "M2550", "Belt Conveyor (6m) 7": "M2551", "Pusher 1": "M2552",
    "Belt Conveyor (6m) 17": "M2750", "Emitter 3 (Emit)": "M2751",
    "Roller Conveyor (4m) 3": "M2752", "Roller Conveyor (6m) 2": "M2753",
    "Roller Stop 0": "M2768",
    "Unused input 8": None, "Unused input 9": None, "Unused input 10": None,
    "Unused input 11": None, "Unused input 12": None,
    "Pick & Place 2 (Grab)": "M2760", "Turntable 2 Turn": "M2761",
    "Turntable 2 Roll (+)": "M2762", "Turntable 2 Roll (-)": "M2763",
    "Roller Conveyor (4m) 2": "M2764", "Remover 0 (Remove)": "M2765",
    "Right Positioner 0 (Raise)": "M2766", "Right Positioner 0 (Clamp)": "M2767",
}

NUMERIC_DEVICES = ("D2030", "D2060", "D2061", "D2062")
TARGET_DEVICES = ("D2063", "D2064", "D2065")
READY = "M2721"
ARM = "M2781"


class AnalogBridge(base.ModbusBridge):
    input_devices = tuple(INPUTS.values())
    output_devices = tuple(OUTPUTS.values())
    numeric_devices = NUMERIC_DEVICES

    def handle(self):
        self.position_seen = set()
        self.ready = False
        self.hold = None
        self.armed = False
        try:
            super().handle()
        finally:
            self.server.mx.write([READY], [0])

    def write_inputs(self, mapping, cache, start, values):
        super().write_inputs(mapping, cache, start, values)
        if mapping is self.numeric_devices:
            self.position_seen.update(index for index in range(start, start + len(values)) if index > 0)
            if len(self.position_seen) == 3 and not self.ready:
                self.server.mx.write([READY], [1])
                self.ready = True
                self.hold = list(self.numeric[1:4])
                print(f"XYZ feedback ready: {self.hold}", flush=True)

    def dispatch(self, message):
        if message[0] != 4:
            return super().dispatch(message)
        if len(message) != 5:
            return bytes((0x84, 3))
        start, count = struct.unpack_from(">HH", message, 1)
        if not 1 <= count <= 3 or start + count > 3:
            return bytes((0x84, 2))
        run = self.ready and self.digital[0] and not (self.digital[1] or self.digital[2])
        enabled, *targets = self.server.mx.read((ARM, *TARGET_DEVICES)) if run else (0,)
        allowed = bool(enabled) and all(0 <= value <= 1000 for value in targets)
        if allowed:
            self.hold = targets
        elif self.armed and self.ready:
            self.hold = list(self.numeric[1:4])
        self.armed = allowed
        values = (self.hold or [0, 0, 0])[start:start + count]
        return bytes((4, 2 * count)) + struct.pack(">" + "H" * count, *values)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--station", type=int, default=1)
    parser.add_argument("--trace", action="store_true")
    args = parser.parse_args()
    folder = Path(__file__).resolve().parent.parent
    scene = folder / "factoryio" / "scenes" / "pil2ya_packout.factoryio"
    if not scene.is_file():
        parser.exit(1, f"Scene file missing: {scene}\n")
    print(f"Scene: {scene}", flush=True)
    try:
        with base.LocalServer(("127.0.0.1", 502), AnalogBridge) as server, base.MxStation(args.station) as mx:
            server.mx, server.trace = mx, args.trace
            inputs = [device for device in AnalogBridge.input_devices if device]
            inputs.extend((*NUMERIC_DEVICES, READY, ARM))
            mx.write(inputs, [0] * len(inputs))
            print(f"MX station {args.station} connected. Listening on 127.0.0.1:502.", flush=True)
            server.serve_forever()
    except KeyboardInterrupt:
        pass
    except (OSError, RuntimeError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
