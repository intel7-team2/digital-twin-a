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
        self.p.mem.update(M2016=1, M2018=1, M2015=1,
                          M2003=1, M2006=1, M2009=1, M2012=1)
        self.p.scan(.01)
        self.p.mem['M2015'] = 0

    def step(self, n):
        for _ in range(n):
            self.p.scan(.01)

    def test_start_emit_single_and_classify_B(self):
        self.assertEqual(self.p.mem['M2300'], 1)
        self.assertEqual(self.p.mem['M2104'], 0)
        self.step(30)
        self.assertEqual(self.p.mem['M2100'], 0)
        self.assertEqual(self.p.mem['M2310'], 1)
        self.p.mem.update(D2000=4, M2001=1)
        self.step(110)
        self.assertEqual(self.p.mem['D2400'], 1)
        self.assertEqual(self.p.mem['D2423'], 2)
        self.assertEqual(self.p.mem['M2103'], 0)
        self.p.mem.update(M2001=0, D2000=0)
        self.step(40)
        self.assertEqual(self.p.mem['M2312'], 1)
        self.assertEqual(self.p.mem['M2103'], 1)
        self.assertEqual(self.p.mem['M2100'], 0)
        self.p.mem['M2010'] = 1
        self.step(40)
        self.assertEqual(self.p.mem['M2106'], 1)
        self.assertEqual(self.p.mem['M2105'], 0)
        self.p.mem.update(M2008=1, M2009=0, M2010=0)
        self.step(2)
        self.assertEqual(self.p.mem['M2106'], 0)
        self.p.mem.update(M2008=0, M2009=1)
        self.step(2)
        self.assertEqual(self.p.mem['D2452'], 1)
        self.assertEqual(self.p.mem['M2312'], 0)

    def test_stop_and_emergency_break_latch(self):
        self.p.mem['M2018'] = 0
        self.step(1)
        self.assertEqual(self.p.mem['M2300'], 0)
        self.assertEqual(self.p.mem['M2102'], 0)
        self.p.mem['M2018'] = 1
        self.step(10)
        self.assertEqual(self.p.mem['M2300'], 0)

    def test_routing_timeout_fault(self):
        self.p.mem['M2312'] = 1
        self.step(2001)
        self.assertEqual(self.p.mem['M2390'], 1)
        self.step(1)
        self.assertEqual(self.p.mem['M2300'], 0)

    def test_lost_link_resets_and_clears_outputs(self):
        rt = Runtime()
        rt.outputs[2] = True
        rt.running = True
        rt.tick(.01)
        self.assertFalse(any(rt.outputs))
        self.assertFalse(rt.running)

    def test_batch_requires_real_exit_detection(self):
        self.p.mem.update(M2001=1, D2441=4, D2442=4, D2443=4)
        self.p.mem['M2330'] = 1
        self.step(1500)
        self.assertEqual(self.p.mem['D2460'], 0)
        self.assertEqual(self.p.mem['M2330'], 1)
        self.p.mem['M2014'] = 1
        self.step(10)
        self.p.mem['M2014'] = 0
        self.step(810)
        self.assertEqual(self.p.mem['D2460'], 1)
        self.step(900)
        self.assertEqual(self.p.mem['D2460'], 1)

    def test_supply_timeout_fault(self):
        self.p.mem.update(M2001=1, D2441=4, D2442=4, D2443=4)
        self.p.mem['M2330'] = 1
        self.step(4002)
        self.assertEqual(self.p.mem['M2390'], 1)
        self.assertEqual(self.p.mem['D2460'], 0)

    def test_inspection_release_jam_fault(self):
        self.p.mem.update(M2001=1, D2000=4)
        self.step(620)
        self.assertEqual(self.p.mem['M2390'], 1)
        self.assertEqual(self.p.mem['M2300'], 0)


if __name__ == '__main__':
    unittest.main()
