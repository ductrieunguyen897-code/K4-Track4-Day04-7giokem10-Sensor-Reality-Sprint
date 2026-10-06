"""
Multi-Camera Bandwidth Profiling Benchmark (Topic T7)
Architecture: Producer-Consumer multi-processing with Synthetic RGB-D data.
Platform: Windows 11 / Laptop HP Victus 16

Team Allocation Notice:
- SECTION 1: COMMON CONTRACT & CONFIG (Managed by TV1 - Bùi Văn Quang [MSV: 2A202602688])
- SECTION 2: PRODUCER & BUFFER / SLOT LOGIC (Assigned to TV2 - Data Source & Memory)
- SECTION 3: CONSUMER, TELEMETRY & LOGGER (TV3 - Metrics & Telemetry)  <-- implemented here
- SECTION 4: BENCHMARK RUNNER & INTEGRATION (Managed by TV1 - Bùi Văn Quang & TV5)

Scope note: this benchmark measures a SYNTHETIC software pipeline on the host
CPU. It does NOT measure USB wire bandwidth, RealSense sensor/driver latency,
depth accuracy or GPU load. "Bandwidth" in configs is the raw application
payload computed from the frame geometry, not a measured bus throughput.

TV3 note (Metrics Lead): SECTION 3 is the authoritative implementation of the
frame counters, latency/throughput/resource metrics and CSV schema described in
docs/methodology.md and specs/contract_spec.md. Every run must satisfy the three
accounting identities below per camera, otherwise status is "invalid".
"""

import os
import sys
import csv
import json
import math
import time
import queue
import argparse
import platform
import subprocess
import multiprocessing as mp
from pathlib import Path
from multiprocessing import shared_memory

import numpy as np
import psutil

# ==============================================================================
# SECTION 1: COMMON CONTRACT & CONFIGURATION (TV1 - Bùi Văn Quang [MSV: 2A202602688])
# ==============================================================================

DEFAULT_WIDTH = 640
DEFAULT_HEIGHT = 480
DEFAULT_FPS = 30
DEFAULT_SLOTS = 32
RGB_CHANNELS = 3
DEPTH_CHANNELS = 1  # 16-bit uint16
COUNTER_BLOCK = 4   # attempted, enqueued, rejected, schedule_missed (producer-side)


def calculate_frame_sizes(width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT):
    """Raw application payload size of one RGB-D frameset (RGB8 + depth uint16)."""
    rgb_size = width * height * RGB_CHANNELS * np.dtype(np.uint8).itemsize
    depth_size = width * height * DEPTH_CHANNELS * np.dtype(np.uint16).itemsize
    total_size = rgb_size + depth_size
    return {
        "rgb_size_bytes": rgb_size,
        "depth_size_bytes": depth_size,
        "total_size_bytes": total_size,
    }


class FrameMetadata:
    """Standard metadata packet defined in specs/contract_spec.md.

    The hot path moves a plain tuple between processes (cheaper to pickle than a
    dict); this class documents and mirrors the agreed contract.
    """

    def __init__(self, camera_id, frame_id, slot_id, t_produced, t_pushed, payload_size):
        self.camera_id = camera_id
        self.frame_id = frame_id
        self.slot_id = slot_id
        self.t_produced = t_produced
        self.t_pushed = t_pushed
        self.payload_size = payload_size

    def to_dict(self):
        return {
            "camera_id": self.camera_id,
            "frame_id": self.frame_id,
            "slot_id": self.slot_id,
            "t_produced": self.t_produced,
            "t_pushed": self.t_pushed,
            "payload_size": self.payload_size,
        }


def percentile(values, p=95.0):
    """Percentile of completed-frame samples; None when there is no sample."""
    return float(np.percentile(values, p)) if values else None


def git_value(*args):
    """Best-effort git lookup for provenance; never raises."""
    try:
        return subprocess.check_output(
            ["git", *args], stderr=subprocess.DEVNULL, text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


# ==============================================================================
# SECTION 2: PRODUCER & MEMORY SLOT MANAGEMENT (TV2 - Data Source & Memory)
# TV2 owns pacing, synthetic noise and the ring-buffer slot lifetime. TV3 keeps
# the counter hooks the metrics layer depends on (attempted/enqueued/rejected/
# schedule_missed) so the accounting identities in SECTION 3 can be checked.
# ==============================================================================

def generate_synthetic_rgbd(width, height, frame_id, seed=0):
    """
    Synthetic RGB-D generator simulating RealSense D435/D455 frames.
    - RGB: uint8 [0..255]
    - Depth: uint16 [500..4999] (payload only, NOT a calibrated distance)
    """
    rng = np.random.default_rng(seed + frame_id)
    rgb = rng.integers(0, 256, size=(height, width, RGB_CHANNELS), dtype=np.uint8)
    depth = rng.integers(500, 5000, size=(height, width), dtype=np.uint16)
    return rgb, depth


def camera_producer(camera_id, cfg, shm_name, free, meta_queue, data_queue,
                    ready, start, stop, counts):
    """
    Producer worker process representing one RGB-D camera.

    Ownership contract:
    - The parent process creates and holds the SharedMemory block for the whole
      run (required on Windows, where the mapping dies when every handle closes).
    - The producer takes a free slot, copies the full payload into it, then
      enqueues metadata only. It never overwrites a slot it did not take.
    - A slot is returned to `free` by whoever releases the frame (consumer or
      shutdown drain), never by the producer after a successful enqueue.

    Counters written to `counts[camera_id*4 : camera_id*4+4]`:
    attempted, enqueued, rejected, schedule_missed.
    """
    frame_bytes = cfg["frame_bytes"]
    width, height = cfg["width"], cfg["height"]
    fps, duration, slots, seed = cfg["fps"], cfg["duration"], cfg["slots"], cfg["seed"]

    shm = None
    view = None
    if shm_name is not None:
        shm = shared_memory.SharedMemory(name=shm_name)
        view = np.ndarray((cfg["pool_bytes"],), np.uint8, buffer=shm.buf)

    rng = np.random.default_rng(seed + camera_id)
    rgb = rng.integers(0, 256, (height, width, 3), dtype=np.uint8)
    depth = rng.integers(500, 5000, (height, width), dtype=np.uint16)
    # Static template reused every frame: isolates the software transfer cost
    # from random-number generation, as documented in docs/methodology.md.
    template = np.concatenate((rgb.ravel(), depth.view(np.uint8).ravel()))

    base = camera_id * COUNTER_BLOCK
    n_sched = int(round(fps * duration))
    ready.put(camera_id)
    try:
        while not start.value and not stop.is_set():
            time.sleep(0.001)
        end = start.value + duration
        for seq in range(n_sched):
            deadline = start.value + seq / fps
            if stop.wait(max(0.0, deadline - time.perf_counter())):
                break  # interrupted; run will be flagged invalid by the caller
            now = time.perf_counter()
            if now >= end or (now - deadline) >= (1.0 / fps):
                counts[base + 3] += 1          # schedule_missed
                continue                        # never emit a catch-up burst
            counts[base] += 1                   # attempted
            if shm_name is not None:
                try:
                    slot = free.get(timeout=0.002)
                except queue.Empty:
                    counts[base + 2] += 1       # rejected: no free slot
                    continue
                offset = (camera_id * slots + slot) * frame_bytes
                t_capture = time.perf_counter()
                np.copyto(view[offset:offset + frame_bytes], template)
                t_enqueue = time.perf_counter()
                if t_enqueue >= end:
                    free.put(slot)
                    counts[base + 2] += 1       # rejected: copy finished late
                    continue
                meta_queue.put((camera_id, seq, slot, t_capture, t_enqueue))
                counts[base + 1] += 1           # enqueued
            else:
                # Baseline queue mode: payload itself goes through the IPC pipe.
                t_capture = time.perf_counter()
                payload = (rgb, depth)
                try:
                    data_queue.put_nowait(
                        (camera_id, seq, -1, t_capture, time.perf_counter(), payload)
                    )
                    counts[base + 1] += 1
                except queue.Full:
                    counts[base + 2] += 1
    finally:
        if view is not None:
            del view
        if shm is not None:
            shm.close()  # parent retains the lifetime handle


# ==============================================================================
# SECTION 3: CONSUMER, TELEMETRY & LOGGER (TV3 - Metrics & CSV Telemetry)
# TV3 owns: frame counters, timestamps, latency/throughput, CPU/RAM sampling,
# the FIFO/latest policy and every CSV/JSON metric file. Validity rules from
# docs/methodology.md and the action items in docs/integration_review.md are
# enforced here.
# ==============================================================================

class MetricsCollector:
    """Consumer + telemetry recorder driven by the parent process.

    The parent acts as the single consumer so that slot release, resource
    sampling and metric aggregation all share one clock and one process image.
    """

    def __init__(self, cfg, out_dir, counts, start):
        self.cfg = cfg
        self.out = Path(out_dir)
        self.mode = cfg["mode"]
        self.cameras = cfg["cameras"]
        self.slots = cfg["slots"]
        self.frame_bytes = cfg["frame_bytes"]
        self.policy = cfg["policy"]
        self.delay = cfg["delay_ms"] / 1000.0
        self.duration = cfg["duration"]
        self.fps = cfg["fps"]
        self.counts = counts
        self.start = start

        # Consumer-side counters (per camera)
        self.completed = [0] * self.cameras
        self.stale = [0] * self.cameras
        self.late = [0] * self.cameras
        self.shutdown = [0] * self.cameras

        self.pending = {}          # latest-policy holding area: camera -> item
        self.frames = []           # one row per enqueued frame (lifecycle)
        self.latencies = []        # completed only, ms
        self.waits = []            # queue wait, ms
        self.copies = []           # consumer copy, ms
        self.resource_rows = []
        self.resource_valid = 0    # samples where every monitored process answered
        self.resource_total = 0
        self.forced_termination = False

    # -- queue plumbing ------------------------------------------------------
    def _get(self, meta_queue, data_queue, timeout):
        """Non-blocking read from the active queue; None on empty."""
        q = meta_queue if self.mode == "shm" else data_queue
        try:
            if timeout and timeout > 0:
                item = q.get(timeout=timeout)
            else:
                item = q.get_nowait()
        except queue.Empty:
            return None
        return item

    # -- frame lifecycle -----------------------------------------------------
    def _record(self, item, state, finish, frees):
        """Return the slot to its free list and log the frame lifecycle row."""
        cam, seq, slot, tc, tq = item[0], item[1], item[2], item[3], item[4]
        if frees is not None and slot >= 0:
            frees[cam].put(slot)
        # row: camera, seq, status, slot, capture_s, enqueue_s, finish_s, latency_ms
        self.frames.append([
            cam, seq, state, slot, tc, tq,
            finish if finish is not None else "",
            (finish - tc) * 1000 if finish is not None else "",
        ])

    def _process(self, item, view, copied, frees, end):
        """Copy one frameset out, apply the injected delay, then account it."""
        cam, seq, slot, tc, tq = item[0], item[1], item[2], item[3], item[4]
        t_receive = time.perf_counter()
        if view is not None:
            offset = (cam * self.slots + slot) * self.frame_bytes
            np.copyto(copied, view[offset:offset + self.frame_bytes])
        # queue mode: the payload was already copied by pickle into `item[5]`
        t_copy = time.perf_counter()
        if self.delay > 0:
            time.sleep(self.delay)  # delay per RGB-D frameset, not per camera set
        finish = time.perf_counter()
        if finish < end:
            self.completed[cam] += 1
            self.latencies.append((finish - tc) * 1000.0)
            self.waits.append((t_receive - tq) * 1000.0)
            self.copies.append((t_copy - t_receive) * 1000.0)
            self._record(item, "completed", finish, frees)
        else:
            self.late[cam] += 1
            self._record(item, "completed_after_window", finish, frees)

    def _drain_latest(self, meta_queue, data_queue, frees):
        """Latest policy: keep only the newest frameset per camera in the batch."""
        for _ in range(self.cameras * self.slots):
            item = self._get(meta_queue, data_queue, timeout=0)
            if item is None:
                break
            cam = item[0]
            if cam in self.pending:
                self.stale[cam] += 1
                self._record(self.pending[cam], "stale", None, frees)
            self.pending[cam] = item  # replacement preserves fair camera order

    # -- resource sampling ---------------------------------------------------
    def _sample(self, elapsed, probes, expected):
        """Sample CPU/RSS for parent + producers; record n_valid (TV4 review)."""
        cpu_sum, rss_sum, ok = 0.0, 0, 0
        for probe in probes:
            try:
                cpu_sum += probe.cpu_percent(None)
                rss_sum += probe.memory_info().rss
                ok += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        complete = ok == expected
        self.resource_total += 1
        if complete:
            self.resource_valid += 1
        cpu_norm = cpu_sum / (psutil.cpu_count() or 1) if complete else None
        rss_mb = rss_sum / 1e6 if complete else None
        backlog = sum(
            max(0, self.counts[c * COUNTER_BLOCK + 1] - self.completed[c]
                - self.stale[c] - self.late[c])
            for c in range(self.cameras)
        )
        self.resource_rows.append([
            elapsed, cpu_norm, psutil.cpu_percent(None), rss_mb,
            psutil.virtual_memory().percent, backlog, ok,
        ])

    # -- main loop -----------------------------------------------------------
    def consume(self, meta_queue, data_queue, view, copied, frees, probes, expected, end, workers):
        next_sample = self.start.value + 0.5
        while time.perf_counter() < end:
            if any(w.exitcode not in (None, 0) for w in workers):
                raise RuntimeError("Producer process failed")
            now = time.perf_counter()
            if now >= next_sample:
                self._sample(now - self.start.value, probes, expected)
                next_sample = now + 0.5
            if self.policy == "latest":
                self._drain_latest(meta_queue, data_queue, frees)
                if not self.pending:
                    item = self._get(meta_queue, data_queue, timeout=0.005)
                    if item is None:
                        continue
                    self.pending[item[0]] = item
                cam = next(iter(self.pending))
                item = self.pending.pop(cam)
            else:
                item = self._get(meta_queue, data_queue, timeout=0.005)
                if item is None:
                    continue
            self._process(item, view, copied, frees, end)

    def drain_shutdown(self, meta_queue, data_queue, frees):
        """Move every still-queued frame to shutdown_backlog and free its slot."""
        while True:
            item = self._get(meta_queue, data_queue, timeout=0)
            if item is None:
                break
            self.shutdown[item[0]] += 1
            self._record(item, "shutdown_backlog", None, frees)
        for item in self.pending.values():
            self.shutdown[item[0]] += 1
            self._record(item, "shutdown_backlog", None, frees)
        self.pending.clear()

    # -- finalize ------------------------------------------------------------
    def finalize(self, status, failure):
        scheduled = int(round(self.fps * self.duration))
        percam = []
        accounting_all_ok = True
        for cam in range(self.cameras):
            attempted, enqueued, rejected, missed = list(
                self.counts[cam * COUNTER_BLOCK:cam * COUNTER_BLOCK + COUNTER_BLOCK]
            )
            accounting_ok = (
                scheduled == attempted + missed
                and attempted == enqueued + rejected
                and enqueued == self.completed[cam] + self.stale[cam]
                + self.late[cam] + self.shutdown[cam]
            )
            accounting_all_ok = accounting_all_ok and accounting_ok
            percam.append({
                "camera": cam, "scheduled": scheduled, "attempted": attempted,
                "enqueued": enqueued, "rejected": rejected, "schedule_missed": missed,
                "completed": self.completed[cam], "stale": self.stale[cam],
                "late_completion": self.late[cam],
                "shutdown_backlog": self.shutdown[cam],
                "fps": self.completed[cam] / self.duration,
                "accounting_ok": accounting_ok,
            })

        done = sum(self.completed)
        total_scheduled = self.cameras * scheduled
        finite = all(math.isfinite(x) and x >= 0 for x in self.latencies)
        # Validity beyond `status` alone (integration_review.md, TV4 item):
        # a run is usable only if accounting holds, frames completed, latencies
        # are finite/non-negative and no worker had to be killed.
        if not accounting_all_ok:
            status, failure = "invalid", failure or "accounting identity failed"
        if done == 0:
            status, failure = "invalid", failure or "no completed frames"
        if not finite:
            status, failure = "invalid", failure or "non-finite latency sample"
        if self.forced_termination:
            status, failure = "invalid", failure or "worker required forced termination"

        summary = {
            "run_id": self.out.name,
            "status": status,
            "valid": status == "ok",
            "failure": failure,
            "mode": self.mode,
            "cameras": self.cameras,
            "width": self.cfg["width"],
            "height": self.cfg["height"],
            "target_fps": self.fps,
            "duration_s": self.duration,
            "slots": self.slots,
            "delay_ms": self.cfg["delay_ms"],
            "policy": self.policy,
            "seed": self.cfg["seed"],
            "family": self.cfg.get("family"),
            "code_commit": self.cfg.get("code_commit"),
            "frame_bytes": self.frame_bytes,
            "aggregate_fps": done / self.duration,
            "min_camera_fps": min(self.completed) / self.duration,
            "completion_ratio": done / total_scheduled,
            "explicit_drop_pct": 100.0 * (
                sum(p["rejected"] for p in percam) + sum(self.stale)
            ) / total_scheduled,
            "deadline_miss_pct": 100.0 * sum(
                p["schedule_missed"] for p in percam
            ) / total_scheduled,
            "backlog_at_end": sum(self.shutdown) + sum(self.late),
            "latency_mean_ms": float(np.mean(self.latencies)) if self.latencies else None,
            "latency_p95_ms": percentile(self.latencies),
            "queue_wait_p95_ms": percentile(self.waits),
            "copy_p95_ms": percentile(self.copies),
            "target_payload_Mbps": self.cameras * self.cfg["width"] * self.cfg["height"] * self.fps * 40 / 1e6,
            "completed_payload_MBps": done * self.frame_bytes / self.duration / 1e6,
            "pool_MB": self.cfg["pool_bytes"] / 1e6,
            "cpu_normalized_mean_pct": (
                float(np.mean([r[1] for r in self.resource_rows if r[1] is not None]))
                if any(r[1] is not None for r in self.resource_rows) else None
            ),
            "rss_sum_peak_MB": max(
                (r[3] for r in self.resource_rows if r[3] is not None), default=None
            ),
            "backlog_sample_peak": max((r[5] for r in self.resource_rows), default=None),
            "resource_samples": self.resource_total,
            "resource_samples_valid": self.resource_valid,
            "resource_monitor_processes": self.cfg.get("resource_monitor_processes"),
            "resource_monitor_expected": self.cameras + 1,
            "gpu": "NA",
            "accounting_all_ok": accounting_all_ok,
            # TV1 contract_spec.md compatibility fields
            "frames_received": done,
            "total_expected_frames": total_scheduled,
            "achieved_total_fps": done / self.duration,
            "per_camera": percam,
        }

        with (self.out / "per_camera.csv").open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(list(percam[0]))
            writer.writerows([list(row.values()) for row in percam])

        with (self.out / "frames.csv").open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                ["camera", "seq", "status", "slot_id", "capture_s",
                 "enqueue_s", "finish_s", "latency_ms"]
            )
            writer.writerows(self.frames)

        with (self.out / "resources.csv").open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                ["elapsed_s", "cpu_normalized_pct", "system_cpu_pct", "rss_sum_MB",
                 "system_memory_pct", "backlog_proxy", "n_valid_processes"]
            )
            writer.writerows(self.resource_rows)

        # specs/contract_spec.md schema kept for TV1's smoke_test.py gate.
        with (self.out / "frames_telemetry.csv").open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                ["timestamp", "camera_id", "frame_id", "slot_id", "t_produced",
                 "t_consumed", "latency_ms", "payload_bytes"]
            )
            for row in self.frames:
                cam, seq, state, slot, tc, tq, finish, lat = row
                writer.writerow([
                    f"{tc:.6f}", cam, seq, slot, f"{tc:.6f}",
                    f"{finish:.6f}" if finish != "" else "",
                    f"{lat:.3f}" if lat != "" else "", self.frame_bytes,
                ])

        (self.out / "summary.json").write_text(
            json.dumps(summary, indent=2), encoding="utf-8"
        )
        print(json.dumps(
            {k: v for k, v in summary.items() if k != "per_camera"}, indent=2
        ), flush=True)
        return summary


# ==============================================================================
# SECTION 4: BENCHMARK RUNNER & INTEGRATION (TV1 - Bùi Văn Quang & TV5)
# ==============================================================================

def _resolve_out_dir(args):
    """Explicit --out (protocol) wins; otherwise auto-tag under --outdir (TV1)."""
    if args.out:
        return Path(args.out)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    tag = f"run_{stamp}_{args.cameras}cam_{args.fps}fps_{args.mode}"
    return Path(args.outdir) / tag


def run_benchmark(args):
    out = _resolve_out_dir(args)
    out.mkdir(parents=True, exist_ok=False)  # never overwrite earlier evidence

    sizes = calculate_frame_sizes(args.width, args.height)
    frame_bytes = sizes["total_size_bytes"]
    pool_bytes = frame_bytes * args.cameras * args.slots
    if pool_bytes > min(1_500_000_000, max(psutil.virtual_memory().available * 0.85, psutil.virtual_memory().total * 0.20)):
        raise RuntimeError(
            "Pool exceeds memory budget. Lower resolution/slots; record the change."
        )

    cfg = {
        "cameras": args.cameras, "width": args.width, "height": args.height,
        "fps": args.fps, "duration": args.duration, "slots": args.slots,
        "delay_ms": args.delay_ms, "policy": args.policy, "seed": args.seed,
        "mode": args.mode, "family": args.family,
        "frame_bytes": frame_bytes, "pool_bytes": pool_bytes,
        "code_commit": git_value("rev-parse", "HEAD"),
    }
    config = {
        **cfg,
        "source": "seeded static RGB8 + uint16 depth; full copy each frame",
        "clock": "time.perf_counter; host software clock",
        "viewer": False,
        "gpu": "NA",
        "python": platform.python_version(),
        "platform": platform.platform(),
        "logical_cpus": psutil.cpu_count(),
        "ram_bytes": psutil.virtual_memory().total,
        "git_commit": cfg["code_commit"],
        "git_dirty": git_value("status", "--porcelain"),
        "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    (out / "config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")

    print("=" * 70)
    print(f"STARTING BENCHMARK: {out.name}")
    print(f"Cameras: {args.cameras} | Target FPS: {args.fps} | Duration: {args.duration}s")
    print(f"Resolution: {args.width}x{args.height} RGB-D ({frame_bytes} bytes/frameset)")
    print(f"Policy: {args.policy} | Delay: {args.delay_ms} ms | Slots: {args.slots} | Mode: {args.mode}")
    print("=" * 70)

    ctx = mp.get_context("spawn")
    meta_queue = ctx.Queue()
    data_queue = ctx.Queue(maxsize=args.cameras * args.slots) if args.mode == "queue" else None
    ready = ctx.Queue()
    frees = [ctx.Queue(maxsize=args.slots) for _ in range(args.cameras)]
    for free in frees:
        for slot in range(args.slots):
            free.put(slot)
    start, stop = ctx.Value("d", 0), ctx.Event()
    counts = ctx.Array("q", args.cameras * COUNTER_BLOCK, lock=False)

    shm, view, copied = None, None, None
    if args.mode == "shm":
        shm = shared_memory.SharedMemory(create=True, size=pool_bytes)
        view = np.ndarray((pool_bytes,), np.uint8, buffer=shm.buf)
        copied = np.empty(frame_bytes, np.uint8)
        print(f"[SHM] Allocated {pool_bytes / 1e6:.3f} MB across "
              f"{args.cameras}x{args.slots} slots.")

    workers = [
        ctx.Process(target=camera_producer, args=(
            cam, cfg, shm.name if shm is not None else None, frees[cam],
            meta_queue, data_queue, ready, start, stop, counts))
        for cam in range(args.cameras)
    ]
    collector = MetricsCollector(cfg, out, counts, start)
    status, failure = "ok", None

    try:
        for worker in workers:
            worker.start()
        for _ in workers:
            ready.get(timeout=60)
        probes = []
        for pid in [os.getpid(), *[w.pid for w in workers]]:
            try:
                probes.append(psutil.Process(pid))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        config["resource_monitor_processes"] = len(probes)
        config["resource_monitor_expected"] = args.cameras + 1
        cfg["resource_monitor_processes"] = len(probes)
        (out / "config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
        for probe in probes:
            probe.cpu_percent(None)
        psutil.cpu_percent(None)
        start.value = time.perf_counter() + 1  # exclude startup from the window
        stop.wait(max(0.0, start.value - time.perf_counter()))
        end = start.value + args.duration
        collector.consume(meta_queue, data_queue, view, copied, frees,
                          probes, args.cameras + 1, end, workers)
    except BaseException as exc:  # noqa: BLE001 - record any failure as invalid
        status, failure = "invalid", repr(exc)
    finally:
        stop.set()
        join_deadline = time.perf_counter() + 10
        while any(w.is_alive() for w in workers) and time.perf_counter() < join_deadline:
            item = collector._get(meta_queue, data_queue, timeout=0.02)
            if item is not None:
                collector.shutdown[item[0]] += 1
                collector._record(item, "shutdown_backlog", None, frees)
            for worker in workers:
                if worker.pid:
                    worker.join(timeout=0)
        for worker in workers:
            if worker.pid and worker.is_alive():
                worker.terminate()
                collector.forced_termination = True
            if worker.pid:
                worker.join(timeout=2)
                if worker.exitcode not in (0, None):
                    status = "invalid"
        collector.drain_shutdown(meta_queue, data_queue, frees)
        if view is not None:
            del view
        if shm is not None:
            shm.close()
            shm.unlink()  # Windows: mapping is removed once all handles close
        for q in [meta_queue, ready, *frees] + ([data_queue] if data_queue else []):
            q.cancel_join_thread()
            q.close()

    summary = collector.finalize(status, failure)
    print(f"Status: {summary['status']} | Aggregate FPS: {summary['aggregate_fps']:.2f} "
          f"| Min-camera FPS: {summary['min_camera_fps']:.2f} | "
          f"P95 latency: {summary['latency_p95_ms']}")
    print(f"Results stored at: {out}")
    print("=" * 70)
    return 0 if summary["status"] == "ok" else 2


def main():
    parser = argparse.ArgumentParser(
        description="Multi-Camera RGB-D Bandwidth Profiler (Topic T7)"
    )
    parser.add_argument("--cameras", type=int, default=2)
    parser.add_argument("--fps", type=int, default=DEFAULT_FPS)
    parser.add_argument("--duration", type=float, default=5)
    parser.add_argument("--width", type=int, default=DEFAULT_WIDTH)
    parser.add_argument("--height", type=int, default=DEFAULT_HEIGHT)
    parser.add_argument("--slots", type=int, default=DEFAULT_SLOTS)
    parser.add_argument("--delay-ms", type=float, default=0.0)
    parser.add_argument("--policy", choices=["fifo", "latest"], default="fifo")
    parser.add_argument("--mode", choices=["shm", "queue"], default="shm")
    parser.add_argument("--outdir", type=str, default="results")
    parser.add_argument("--out", type=str, default=None,
                        help="Explicit run directory (protocol). Rejected if it exists.")
    parser.add_argument("--family", type=str, default=None,
                        help="Optional suite family label: matrix/failure/manual/...")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    if min(args.cameras, args.width, args.height, args.fps, args.slots) <= 0 \
            or args.duration <= 0 or args.delay_ms < 0:
        parser.error("Dimensions/count/FPS/duration must be positive; delay must be >= 0")
    if abs(args.fps * args.duration - round(args.fps * args.duration)) > 1e-6:
        parser.error("fps * duration must be an integer")
    raise SystemExit(run_benchmark(args))


if __name__ == "__main__":
    mp.freeze_support()  # Crucial for Windows multiprocessing support
    main()
