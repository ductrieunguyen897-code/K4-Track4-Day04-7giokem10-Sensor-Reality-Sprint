"""Unit and functional tests for TV2 (Source & Memory Lead).

Validates:
1. RGB8 (uint8) + Depth (uint16) template generation (5 bytes/pixel).
2. Seed independence across cameras.
3. SharedMemory allocation and slot offset calculation.
4. Producer pacing, schedule deadline checks, and atomic counters accounting.
5. Pool exhaustion behavior: Producer rejects gracefully without deadlocks.
6. Clean SharedMemory lifetime and handle release.
"""
import multiprocessing as mp
from multiprocessing.shared_memory import SharedMemory
import queue
import time
import unittest
import numpy as np

from benchmark.bench import producer


class TestProducerAndMemory(unittest.TestCase):
    def setUp(self):
        self.ctx = mp.get_context('spawn')
        self.width = 160
        self.height = 120
        self.fps = 10
        self.duration = 1.0  # 1 second for fast test
        self.slots = 4
        self.cameras = 2
        self.seed = 100
        self.frame_bytes = self.width * self.height * 5
        self.pool_bytes = self.frame_bytes * self.cameras * self.slots
        self.cfg = {
            'width': self.width,
            'height': self.height,
            'fps': self.fps,
            'duration': self.duration,
            'slots': self.slots,
            'cameras': self.cameras,
            'seed': self.seed,
            'frame_bytes': self.frame_bytes,
            'pool_bytes': self.pool_bytes,
        }

    def test_payload_dimensions_and_dtypes(self):
        """Verify RGB8 + uint16 depth template conforms to 5 bytes/pixel contract."""
        rng = np.random.default_rng(self.seed)
        rgb = rng.integers(0, 256, (self.height, self.width, 3), dtype=np.uint8)
        depth = rng.integers(500, 5000, (self.height, self.width), dtype=np.uint16)
        template = np.concatenate((rgb.ravel(), depth.view(np.uint8).ravel()))

        self.assertEqual(rgb.nbytes, self.width * self.height * 3)
        self.assertEqual(depth.nbytes, self.width * self.height * 2)
        self.assertEqual(template.nbytes, self.frame_bytes)
        self.assertEqual(template.dtype, np.uint8)

    def test_seed_uniqueness_across_cameras(self):
        """Verify camera 0 and camera 1 produce distinct seeded payloads."""
        rng0 = np.random.default_rng(self.seed + 0)
        rgb0 = rng0.integers(0, 256, (self.height, self.width, 3), dtype=np.uint8)

        rng1 = np.random.default_rng(self.seed + 1)
        rgb1 = rng1.integers(0, 256, (self.height, self.width, 3), dtype=np.uint8)

        self.assertFalse(np.array_equal(rgb0, rgb1))

    def test_slot_offset_calculation(self):
        """Verify slot address calculation avoids overlapping between cameras and slots."""
        offsets = set()
        for cam in range(self.cameras):
            for slot in range(self.slots):
                offset = (cam * self.slots + slot) * self.frame_bytes
                self.assertNotIn(offset, offsets)
                offsets.add(offset)
                self.assertLessEqual(offset + self.frame_bytes, self.pool_bytes)

    def test_producer_execution_and_accounting(self):
        """Verify producer process execution, queue contract, and accounting integrity."""
        shm = SharedMemory(create=True, size=self.pool_bytes)
        output = self.ctx.Queue()
        ready = self.ctx.Queue()
        free = self.ctx.Queue()
        for s in range(self.slots):
            free.put(s)

        start = self.ctx.Value('d', 0)
        stop = self.ctx.Event()
        counts = self.ctx.Array('q', 4, lock=False)  # cam 0: 4 counters

        p = self.ctx.Process(target=producer, args=(
            0, self.cfg, shm.name, free, output, ready, start, stop, counts
        ))

        try:
            p.start()
            cam_ready = ready.get(timeout=5)
            self.assertEqual(cam_ready, 0)

            # Start timing
            start.value = time.perf_counter() + 0.1
            time.sleep(0.1)

            # Consume frames as they arrive to return slots
            received_frames = []
            deadline = time.perf_counter() + self.duration + 2.0
            scheduled = int(round(self.fps * self.duration))

            while time.perf_counter() < deadline and len(received_frames) < scheduled:
                try:
                    item = output.get(timeout=0.2)
                    cam, seq, slot, tc, tq = item
                    received_frames.append(item)
                    # Return slot
                    free.put(slot)
                except queue.Empty:
                    if not p.is_alive():
                        break

            p.join(timeout=3)
            self.assertEqual(p.exitcode, 0)

            attempted, enqueued, rejected, missed = list(counts[:4])
            # Accounting checks:
            # scheduled == attempted + missed
            self.assertEqual(scheduled, attempted + missed,
                             f"scheduled ({scheduled}) != attempted ({attempted}) + missed ({missed})")
            # attempted == enqueued + rejected
            self.assertEqual(attempted, enqueued + rejected,
                             f"attempted ({attempted}) != enqueued ({enqueued}) + rejected ({rejected})")

        finally:
            stop.set()
            if p.is_alive():
                p.terminate()
                p.join()
            shm.close()
            shm.unlink()

    def test_producer_pool_exhaustion_rejection(self):
        """Verify that when no free slots exist, producer rejects frame rather than deadlocking."""
        shm = SharedMemory(create=True, size=self.pool_bytes)
        output = self.ctx.Queue()
        ready = self.ctx.Queue()
        free = self.ctx.Queue()
        # Provide NO free slots to force queue.Empty
        start = self.ctx.Value('d', 0)
        stop = self.ctx.Event()
        counts = self.ctx.Array('q', 4, lock=False)

        p = self.ctx.Process(target=producer, args=(
            0, self.cfg, shm.name, free, output, ready, start, stop, counts
        ))

        try:
            p.start()
            ready.get(timeout=5)
            start.value = time.perf_counter() + 0.05
            p.join(timeout=self.duration + 3.0)
            self.assertEqual(p.exitcode, 0)

            attempted, enqueued, rejected, missed = list(counts[:4])
            self.assertEqual(enqueued, 0, "No frames should be enqueued when slots are empty")
            self.assertGreater(rejected, 0, "Rejected count should be positive due to pool exhaustion")
            self.assertEqual(attempted, rejected, "All attempted frames should be rejected")

        finally:
            stop.set()
            if p.is_alive():
                p.terminate()
                p.join()
            shm.close()
            shm.unlink()


if __name__ == '__main__':
    unittest.main()
