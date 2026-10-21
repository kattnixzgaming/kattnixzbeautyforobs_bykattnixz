import mmap
from pathlib import Path
import sys
import unittest
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'motor'))
import kb_obs_transport as transport


class Lock:
    def acquire(self): return True
    def release(self): pass


class Clock:
    def GetTickCount64(self): return 10000


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.camera = transport.ObsCamera.__new__(transport.ObsCamera)
        c = self.camera
        c.input = mmap.mmap(-1, transport.MAP_SIZE)
        c.output = mmap.mmap(-1, transport.MAP_SIZE)
        c.input_lock = c.output_lock = Lock()
        c.api = Clock(); c.last_heartbeat = 0; c.identity = c.last = None

    def tearDown(self):
        self.camera.input.close(); self.camera.output.close()

    def test_header_layout(self):
        self.assertEqual(transport.HEADER.size, 64)

    def test_roundtrip_and_flip(self):
        for flip in (0, 1):
            with self.subTest(flip=flip):
                pixels = np.arange(8*6*4, dtype=np.uint8).reshape(6, 8, 4)
                fields = [transport.MAGIC, 1, 8, 6, 32, 192, flip+1, flip, 123, 9990, 42, 0, 0]
                transport.HEADER.pack_into(self.camera.input, 0, *fields)
                self.camera.input[64:256] = pixels.tobytes()
                ok, frame = self.camera.read()
                expected = pixels[:, :, :3]
                if flip: expected = expected[::-1]
                self.assertTrue(ok); np.testing.assert_array_equal(frame, expected)
                self.assertTrue(self.camera.publish(frame))
                output = np.frombuffer(self.camera.output[64:256], np.uint8).reshape(6, 8, 4)
                np.testing.assert_array_equal(output[:, :, :3], pixels[:, :, :3])
                self.assertIsNone(self.camera.read()[1])

    def test_invalid_and_stale_packet(self):
        fields = [transport.MAGIC, 1, 8, 6, 32, 192, 1, 0, 123, 9000, 42, 0, 0]
        self.assertTrue(transport.valid_packet(fields))
        transport.HEADER.pack_into(self.camera.input, 0, *fields)
        self.assertIsNone(self.camera.read()[1])
        fields[4] = 99
        self.assertFalse(transport.valid_packet(fields))
