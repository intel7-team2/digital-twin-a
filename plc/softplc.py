"""Local simulation runtime for the generated MELSEC instruction list.

No hardware connection. Factory I/O Modbus TCP Client connects to 127.0.0.1:502.
Sensors are coils, vision is holding register 0, actuators are discrete inputs.
"""
import argparse
import collections
import json
import operator
from pathlib import Path
import re
import socketserver
import struct
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(__file__).resolve().parent
COMPARE = {'=': operator.eq, '<>': operator.ne, '<': operator.lt,
           '>': operator.gt, '<=': operator.le, '>=': operator.ge}


class Ladder:
    """Only the instructions used by line_v0; unknown instructions fail closed."""
    def __init__(self, path=ROOT / 'line_v0.txt'):
        self.code = [s.split() for line in path.read_text(encoding='utf-8').splitlines()
                     if (s := line.split(';')[0].strip())]
        allowed = {'LD', 'LDI', 'LDP', 'OR', 'ORI', 'AND', 'ANI', 'ORB', 'ANB',
                   'MOV', 'FMOV', 'BKRST', 'INC', '/', 'OUT', 'SET', 'RST', 'END'}
        allowed |= {p + c for p in ('LD', 'OR', 'AND') for c in COMPARE}
        for ins in self.code:
            if ins[0] not in allowed:
                raise ValueError(f'Unsupported instruction: {ins}')
        self.mem = collections.defaultdict(int)
        self.elapsed = collections.defaultdict(float)
        self.edges = {}
        self.first = True

    def addr(self, text):
        match = re.fullmatch(r'([A-Z]+)(\d+)(?:Z(\d+))?', text)
        if not match:
            raise ValueError(f'Invalid device: {text}')
        bank, index, z = match.groups()
        return bank + str(int(index) + (self.mem['Z' + z] if z is not None else 0))

    def get(self, text):
        return int(text[1:]) if text.startswith('K') else self.mem[self.addr(text)]

    def put(self, text, value):
        self.mem[self.addr(text)] = int(value)

    def scan(self, dt):
        self.mem['SM400'], self.mem['SM402'] = 1, int(self.first)
        acc, stack = False, []
        for pc, (op, *args) in enumerate(self.code):
            if op == 'END':
                break
            prefix = 'AND' if op == 'ANI' else next((p for p in ('AND', 'LD', 'OR') if op.startswith(p)), None)
            suffix = op[len(prefix):] if prefix else None
            if suffix in COMPARE:
                value = COMPARE[suffix](self.get(args[0]), self.get(args[1]))
            elif op in ('LD', 'LDI', 'LDP', 'OR', 'ORI', 'AND', 'ANI'):
                value = bool(self.get(args[0]))
                if op in ('LDI', 'ORI', 'ANI'):
                    value = not value
                if op == 'LDP':
                    old = self.edges.get(pc, False)
                    self.edges[pc] = value
                    value = value and not old
            else:
                value = None
            if value is not None:
                if prefix == 'LD':
                    stack.append(acc)
                    acc = value
                elif prefix == 'AND':
                    acc = acc and value
                else:
                    acc = acc or value
            elif op in ('ORB', 'ANB'):
                left = stack.pop()
                acc = (left or acc) if op == 'ORB' else (left and acc)
            elif op == 'OUT':
                if args[0].startswith('T'):
                    self.elapsed[args[0]] = self.elapsed[args[0]] + dt if acc else 0
                    self.put(args[0], acc and self.elapsed[args[0]] + 1e-9 >= self.get(args[1]) * .1)
                else:
                    self.put(args[0], acc)
            elif op in ('SET', 'RST') and acc:
                self.put(args[0], op == 'SET')
                if op == 'RST' and args[0].startswith('T'):
                    self.elapsed[args[0]] = 0
            elif op == 'MOV' and acc:
                self.put(args[1], self.get(args[0]))
            elif op in ('FMOV', 'BKRST') and acc:
                base = self.addr(args[1] if op == 'FMOV' else args[0])
                bank, n = re.fullmatch(r'([A-Z]+)(\d+)', base).groups()
                count = self.get(args[2] if op == 'FMOV' else args[1])
                for i in range(count):
                    self.mem[bank + str(int(n) + i)] = self.get(args[0]) if op == 'FMOV' else 0
            elif op == 'INC' and acc:
                self.put(args[0], self.get(args[0]) + 1)
            elif op == '/' and acc:
                a, b = self.get(args[0]), self.get(args[1])
                q = abs(a) // abs(b) * (-1 if (a < 0) != (b < 0) else 1)
                target = self.addr(args[2])
                self.put(target, q)
                self.put('D' + str(int(target[1:]) + 1), a - q * b)
        self.first = False


class Runtime:
    def __init__(self):
        self.lock = threading.RLock()
        self.coils = [False] * 128
        self.registers = [0] * 128
        self.outputs = [False] * 128
        self.plc = Ladder()
        self.last_rx = 0
        self.running = False
        self.events = collections.deque(maxlen=100)
        self.last_state = None
        self.shutdown = threading.Event()

    def tick(self, dt):
        with self.lock:
            linked = time.monotonic() - self.last_rx < 1
            run = linked and self.coils[19]
            pause = self.coils[20]
            if not run or self.coils[21]:
                if self.running:
                    self.plc = Ladder()
                self.running = False
                self.outputs[:] = [False] * 128
                return
            if pause:
                return
            start = not self.running
            if start:
                self.plc = Ladder()
            self.running = True
            for i in range(19):
                self.plc.mem[f'M{1000+i}'] = int(self.coils[i])
            if start:
                self.plc.mem['M1015'] = 1  # ▶ starts a fresh simulation cycle.
            self.plc.mem['D1000'] = self.registers[0]
            self.plc.scan(dt)
            for i in range(20):
                self.outputs[i] = bool(self.plc.mem[f'M{1100+i}'])
            # Remove actuating energy on Stop, E-stop or fault in the same scan.
            if not self.plc.mem['M0']:
                for i in range(17):
                    self.outputs[i] = False
            self.outputs[8] = self.outputs[16] = True
            state = tuple(self.plc.mem[k] for k in ('D0', 'D23', 'M90', 'D51', 'D52', 'D53', 'D60'))
            if state != self.last_state:
                self.events.append({'time': time.strftime('%H:%M:%S'), 'state': state})
                self.last_state = state

    def status(self):
        with self.lock:
            return {'connected': time.monotonic() - self.last_rx < 1,
                    'simulation_running': self.running, 'sensors': self.coils[:22],
                    'outputs': self.outputs[:20], 'vision': self.registers[0],
                    'memory': dict(self.plc.mem), 'events': list(self.events)}


class Modbus(socketserver.BaseRequestHandler):
    def read_exact(self, n):
        data = b''
        while len(data) < n:
            part = self.request.recv(n - len(data))
            if not part:
                raise EOFError
            data += part
        return data

    def handle(self):
        self.request.settimeout(3)
        try:
            while True:
                tid, proto, length, unit = struct.unpack('>HHHB', self.read_exact(7))
                if proto or not 2 <= length <= 254:
                    return
                pdu = self.read_exact(length - 1)
                try:
                    with self.server.runtime.lock:
                        response = self.dispatch(pdu)
                        self.server.runtime.last_rx = time.monotonic()
                except (ValueError, IndexError, struct.error):
                    response = bytes([pdu[0] | 128, 3])
                self.request.sendall(struct.pack('>HHHB', tid, 0, len(response) + 1, unit) + response)
        except (EOFError, OSError):
            pass

    def dispatch(self, pdu):
        rt, fc = self.server.runtime, pdu[0]
        if len(pdu) < 5:
            raise ValueError('short request')
        address, count = struct.unpack('>HH', pdu[1:5])
        if fc in (1, 2, 3, 4, 15, 16) and (not count or address + count > 128):
            return bytes([fc | 128, 2])
        if fc in (1, 2):
            bits = rt.coils if fc == 1 else rt.outputs
            packed = bytearray((count + 7) // 8)
            for i in range(count):
                packed[i // 8] |= int(bits[address+i]) << (i % 8)
            return bytes([fc, len(packed)]) + packed
        if fc in (3, 4):
            values = rt.registers if fc == 3 else [0] * 128
            return bytes([fc, count*2]) + struct.pack('>' + 'H'*count, *values[address:address+count])
        if fc == 15:
            if pdu[5] != (count + 7)//8 or len(pdu) != 6 + pdu[5]:
                raise ValueError('invalid coils')
            for i in range(count):
                rt.coils[address+i] = bool(pdu[6+i//8] & (1 << (i % 8)))
            return pdu[:5]
        if fc == 16:
            if pdu[5] != count*2 or len(pdu) != 6 + count*2:
                raise ValueError('invalid registers')
            rt.registers[address:address+count] = struct.unpack('>'+'H'*count, pdu[6:])
            return pdu[:5]
        if fc in (5, 6):
            if address >= 128 or (fc == 5 and count not in (0, 0xff00)):
                raise ValueError('invalid write')
            (rt.coils if fc == 5 else rt.registers)[address] = bool(count) if fc == 5 else count
            return pdu[:5]
        return bytes([fc | 128, 1])


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=502)
    parser.add_argument('--status-port', type=int, default=8765)
    args = parser.parse_args()
    rt = Runtime()

    class Status(BaseHTTPRequestHandler):
        def do_GET(self):
            data = json.dumps(rt.status(), ensure_ascii=False).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        def log_message(self, *args):
            pass

    with Server(('127.0.0.1', args.port), Modbus) as server:
        server.runtime = rt
        status = ThreadingHTTPServer(('127.0.0.1', args.status_port), Status)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        threading.Thread(target=status.serve_forever, daemon=True).start()
        print(f'Factory I/O soft PLC ready: 127.0.0.1:{args.port}', flush=True)
        print('Open line_v0, connect the driver, press Play. Ctrl+C exits.', flush=True)
        try:
            last = time.monotonic()
            while True:
                now = time.monotonic()
                rt.tick(min(now-last, .1))
                last = now
                time.sleep(.01)
        except KeyboardInterrupt:
            pass
        finally:
            with rt.lock:
                rt.outputs[:] = [False] * 128
            server.shutdown()
            status.shutdown()


if __name__ == '__main__':
    main()
