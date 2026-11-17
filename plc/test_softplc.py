import unittest
import socket
import struct
import threading
from softplc import Ladder, Runtime, Server, Modbus


class ModbusTests(unittest.TestCase):
    def test_wire_bit_order_registers_and_fragmented_frame(self):
        with Server(('127.0.0.1', 0), Modbus) as server:
            server.runtime = Runtime()
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            try:
                with socket.create_connection(server.server_address, timeout=2) as client:
                    def exchange(pdu):
                        request = struct.pack('>HHHB', 123, 0, len(pdu)+1, 1) + pdu
                        client.sendall(request[:4])
                        client.sendall(request[4:])
                        data = b''
                        while len(data) < 7:
                            data += client.recv(7-len(data))
                        _, _, length, _ = struct.unpack('>HHHB', data)
                        body = b''
                        while len(body) < length-1:
                            body += client.recv(length-1-len(body))
                        return body
                    self.assertEqual(exchange(bytes.fromhex('0f0000001603555501')),
                                     bytes.fromhex('0f00000016'))
                    self.assertTrue(server.runtime.coils[0])
                    self.assertFalse(server.runtime.coils[1])
                    self.assertTrue(server.runtime.coils[16])
                    self.assertEqual(exchange(bytes.fromhex('1000000001020007')),
                                     bytes.fromhex('1000000001'))
                    self.assertEqual(server.runtime.registers[0], 7)
                    server.runtime.outputs[19] = True
                    self.assertEqual(exchange(bytes.fromhex('0200000014')),
                                     bytes.fromhex('0203000008'))
                    self.assertEqual(exchange(bytes.fromhex('02007f0002')),
                                     bytes.fromhex('8202'))
            finally:
                server.shutdown()


class LineTests(unittest.TestCase):
    def setUp(self):
        self.p = Ladder()
        self.p.mem.update(M1016=1, M1018=1, M1015=1,
                          M1003=1, M1006=1, M1009=1, M1012=1)
        self.p.scan(.01)
        self.p.mem['M1015'] = 0

    def step(self, n):
        for _ in range(n):
            self.p.scan(.01)

    def test_start_emit_single_and_classify_B(self):
        self.assertEqual(self.p.mem['M0'], 1)
        self.assertEqual(self.p.mem['M1104'], 0)
        self.step(30)
        self.assertEqual(self.p.mem['M1100'], 0)
        self.assertEqual(self.p.mem['M10'], 1)
        self.p.mem.update(D1000=4, M1001=1)
        self.step(110)
        self.assertEqual(self.p.mem['D0'], 1)
        self.assertEqual(self.p.mem['D23'], 2)
        self.assertEqual(self.p.mem['M1103'], 0)
        self.p.mem.update(M1001=0, D1000=0)
        self.step(40)
        self.assertEqual(self.p.mem['M12'], 1)
        self.assertEqual(self.p.mem['M1103'], 1)
        self.assertEqual(self.p.mem['M1100'], 0)
        self.p.mem['M1010'] = 1
        self.step(40)
        self.assertEqual(self.p.mem['M1106'], 1)
        self.assertEqual(self.p.mem['M1105'], 0)
        self.p.mem.update(M1008=1, M1009=0, M1010=0)
        self.step(2)
        self.assertEqual(self.p.mem['M1106'], 0)
        self.p.mem.update(M1008=0, M1009=1)
        self.step(2)
        self.assertEqual(self.p.mem['D52'], 1)
        self.assertEqual(self.p.mem['M12'], 0)

    def test_stop_and_emergency_break_latch(self):
        self.p.mem['M1018'] = 0
        self.step(1)
        self.assertEqual(self.p.mem['M0'], 0)
        self.assertEqual(self.p.mem['M1102'], 0)
        self.p.mem['M1018'] = 1
        self.step(10)
        self.assertEqual(self.p.mem['M0'], 0)

    def test_routing_timeout_fault(self):
        self.p.mem['M12'] = 1
        self.step(2001)
        self.assertEqual(self.p.mem['M90'], 1)
        self.step(1)
        self.assertEqual(self.p.mem['M0'], 0)

    def test_lost_link_resets_and_clears_outputs(self):
        rt = Runtime()
        rt.outputs[2] = True
        rt.running = True
        rt.tick(.01)
        self.assertFalse(any(rt.outputs))
        self.assertFalse(rt.running)

    def test_batch_requires_real_exit_detection(self):
        self.p.mem.update(M1001=1, D41=4, D42=4, D43=4)
        self.p.mem['M30'] = 1
        self.step(1500)
        self.assertEqual(self.p.mem['D60'], 0)
        self.assertEqual(self.p.mem['M30'], 1)
        self.p.mem['M1014'] = 1
        self.step(10)
        self.p.mem['M1014'] = 0
        self.step(810)
        self.assertEqual(self.p.mem['D60'], 1)
        self.step(900)
        self.assertEqual(self.p.mem['D60'], 1)

    def test_supply_timeout_fault(self):
        self.p.mem.update(M1001=1, D41=4, D42=4, D43=4)
        self.p.mem['M30'] = 1
        self.step(4002)
        self.assertEqual(self.p.mem['M90'], 1)
        self.assertEqual(self.p.mem['D60'], 0)

    def test_inspection_release_jam_fault(self):
        self.p.mem.update(M1001=1, D1000=4)
        self.step(620)
        self.assertEqual(self.p.mem['M90'], 1)
        self.assertEqual(self.p.mem['M0'], 0)


if __name__ == '__main__':
    unittest.main()
