"""Factory I/O <-> GX Simulator2 signal bridge. All sequencing lives in GX Works2."""
import base64
import json
import os
from pathlib import Path
import socketserver
import struct
import subprocess
import time

# Use the installed Mitsubishi 32-bit ACT control for direct PLC device addresses.
# JSON lines keep the CLR and the logical station open for the life of the bridge.
MX_WORKER = r"""
$ErrorActionPreference = 'Stop'
function Reply($data) {
    [Console]::WriteLine((ConvertTo-Json -InputObject $data -Compress))
}
function Check($code, $operation) {
    if ($code -ne 0) { throw ('{0}: MX return 0x{1:X8}' -f $operation, [int]$code) }
}
$opened = $false
try {
    $settings = ConvertFrom-Json -InputObject ([Console]::ReadLine())
    $mx = New-Object -ComObject ActUtlType.ActUtlType.1
    $mx.ActLogicalStationNumber = [int]$settings.station
    Check ($mx.Open()) 'Open logical station'
    $opened = $true
    Reply @{ok=$true}
    while ($null -ne ($line = [Console]::ReadLine())) {
        $request = ConvertFrom-Json -InputObject $line
        try {
            [string[]]$devices = @($request.devices)
            if ($request.op -eq 'read') {
                $values = foreach ($device in $devices) {
                    [int]$value = 0
                    Check ($mx.GetDevice($device, [ref]$value)) "Read $device"
                    $value
                }
                Reply @{ok=$true; values=@($values)}
            } else {
                for ($index = 0; $index -lt $devices.Length; $index++) {
                    $device = $devices[$index]
                    Check ($mx.SetDevice($device, [int]$request.values[$index])) "Write $device"
                }
                Reply @{ok=$true}
            }
        } catch {
            Reply @{ok=$false; error=$_.Exception.Message}
        }
    }
} catch {
    Reply @{ok=$false; error=$_.Exception.Message}
} finally {
    if ($opened) { [void]$mx.Close() }
}
"""


class MxStation:
    def __init__(self, station):
        self.station = station
        self.grouped_reads = True

    def __enter__(self):
        script = base64.b64encode(MX_WORKER.encode("utf-16-le")).decode("ascii")
        windows = Path(os.environ["SystemRoot"])
        powershell = windows / "SysWOW64/WindowsPowerShell/v1.0/powershell.exe"
        self.worker = subprocess.Popen(
            [str(powershell), "-NoProfile", "-NonInteractive", "-EncodedCommand", script],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
        )
        try:
            self.exchange({"station": self.station})
        except BaseException:
            self.__exit__(None, None, None)
            raise
        return self

    def __exit__(self, *_):
        self.worker.stdin.close()
        try:
            self.worker.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.worker.terminate()
            self.worker.wait()

    def exchange(self, request):
        self.worker.stdin.write(json.dumps(request, ensure_ascii=True) + "\n")
        self.worker.stdin.flush()
        line = self.worker.stdout.readline()
        if not line:
            raise RuntimeError("MX worker exited")
        reply = json.loads(line)
        if not reply["ok"]:
            raise RuntimeError(reply["error"])
        return reply

    def read(self, devices):
        if self.grouped_reads and all(device.startswith("M") for device in devices):
            numbers = [int(device[1:]) for device in devices]
            bases = []
            for number in sorted(set(numbers)):
                if not bases or number >= bases[-1] + 32:
                    bases.append(number)
            blocks = [f"K8M{base}" for base in bases]
            try:
                words = self.exchange({"op": "read", "devices": blocks})["values"]
            except RuntimeError as error:
                print(f"Packed MX reads unavailable; using point reads: {error}", flush=True)
                self.grouped_reads = False
            else:
                values = {base + bit: (word >> bit) & 1
                          for base, word in zip(bases, words, strict=True) for bit in range(32)}
                return [values[number] for number in numbers]
        return self.exchange({"op": "read", "devices": devices})["values"]

    def write(self, devices, values):
        self.exchange({"op": "write", "devices": devices, "values": values})


class ModbusBridge(socketserver.StreamRequestHandler):
    # Small Modbus replies are latency-sensitive on the local connection.
    disable_nagle_algorithm = True

    def handle(self):
        self.request.settimeout(2.0)
        self.digital = [0] * len(self.input_devices)
        self.numeric = [0] * len(self.numeric_devices)
        self.last_traced = {}
        self.connected_at = time.monotonic()
        print("Factory I/O connected.", flush=True)
        try:
            while header := self.rfile.read(7):
                if len(header) != 7:
                    break
                transaction, protocol, length, unit = struct.unpack(">HHHB", header)
                if protocol != 0 or not 2 <= length <= 254:
                    break
                message = self.rfile.read(length - 1)
                if len(message) != length - 1:
                    break
                response = self.dispatch(message)
                self.wfile.write(struct.pack(">HHHB", transaction, 0, len(response) + 1, unit) + response)
        except OSError:
            pass
        except RuntimeError as error:
            print(f"MX communication stopped: {error}", flush=True)
        finally:
            # Remove stale run and sensor requests from the PLC on a normal disconnect.
            try:
                devices = [device for device in (*self.input_devices, *self.numeric_devices) if device]
                self.server.mx.write(devices, [0] * len(devices))
            except (OSError, RuntimeError) as error:
                print(f"Could not clear PLC inputs: {error}", flush=True)
            print("Factory I/O disconnected.", flush=True)

    def trace(self, addresses, values, elapsed=None):
        if not self.server.trace:
            return
        watched = {"M2510", "M2511", "M2512", "M2551", "M2552", "M2711", "M2752", "M2753", "M2768"}
        changes = []
        for address, value in zip(addresses, values):
            if address in watched and self.last_traced.get(address) != value:
                self.last_traced[address] = value
                changes.append(f"{address}={int(bool(value))}")
        if changes:
            stamp = time.monotonic() - self.connected_at
            latency = f" [MX read {elapsed * 1000:.1f} ms]" if elapsed is not None else ""
            print(f"{stamp:8.3f}s  {' '.join(changes)}{latency}", flush=True)

    def write_inputs(self, mapping, cache, start, values):
        changed = [(index, value) for index, value in enumerate(values, start) if mapping[index] is not None and cache[index] != value]
        if changed:
            devices = [mapping[index] for index, _ in changed]
            changed_values = [value for _, value in changed]
            self.server.mx.write(devices, changed_values)
            self.trace(devices, changed_values)
            for index, value in changed:
                cache[index] = value

    def dispatch(self, message):
        function = message[0]
        if len(message) < 5:
            return bytes((function | 128, 3))
        start, arg = struct.unpack_from(">HH", message, 1)
        if function in (1, 2):
            available = self.digital if function == 1 else self.output_devices
            if not 1 <= arg <= 2000 or start + arg > len(available):
                return bytes((function | 128, 2))
            if function == 1:
                bits = available[start:start + arg]
            elif self.digital[0] and not (self.digital[1] or self.digital[2]):
                addresses = available[start:start + arg]
                started = time.monotonic()
                devices = [address for address in addresses if address is not None]
                values = self.server.mx.read(devices) if devices else []
                self.trace(devices, values, time.monotonic() - started)
                values = iter(values)
                bits = [0 if address is None else next(values) for address in addresses]
            else:
                bits = [0] * arg
            data = bytearray((arg + 7) // 8)
            for index, bit in enumerate(bits):
                if bit:
                    data[index // 8] |= 1 << (index % 8)
            return bytes((function, len(data))) + data
        if function in (5, 15):
            count = 1 if function == 5 else arg
            if not count or start + count > len(self.digital):
                return bytes((function | 128, 2))
            if function == 5 and arg in (0, 0xFF00):
                values = [int(arg != 0)]
            elif function == 15 and len(message) == 6 + (count + 7) // 8 and message[5] == len(message) - 6:
                values = [(message[6 + bit // 8] >> (bit % 8)) & 1 for bit in range(count)]
            else:
                return bytes((function | 128, 3))
            self.write_inputs(self.input_devices, self.digital, start, values)
            return message[:5]
        if function in (6, 16):
            count = 1 if function == 6 else arg
            if not count or start + count > len(self.numeric):
                return bytes((function | 128, 2))
            offset = 3 if function == 6 else 6
            if len(message) != offset + 2 * count or (function == 16 and message[5] != 2 * count):
                return bytes((function | 128, 3))
            values = struct.unpack_from(">" + "h" * count, message, offset)
            self.write_inputs(self.numeric_devices, self.numeric, start, values)
            return message[:5]
        return bytes((function | 128, 1))


class LocalServer(socketserver.TCPServer):
    allow_reuse_address = True
