"""
Multi-Camera Bandwidth Profiling Benchmark (Topic T7)
Architecture: Producer-Consumer multi-processing with Synthetic RGB-D data.
Platform: Windows 11 / Laptop HP Victus 16

Team Allocation Notice:
- SECTION 1: COMMON CONTRACT & CONFIG (Managed by TV1 - Bùi Văn Quang [MSV: 2A202602688])
- SECTION 2: PRODUCER & BUFFER / SLOT LOGIC (Assigned to TV2 - Data Source & Memory)
- SECTION 3: CONSUMER, TELEMETRY & LOGGER (Assigned to TV3 - Metrics & Telemetry)
- SECTION 4: BENCHMARK RUNNER & INTEGRATION (Managed by TV1 - Bùi Văn Quang & TV5)
"""

import os
import sys
import time
import json
import argparse
import multiprocessing as mp
from multiprocessing import shared_memory
import numpy as np

# ==============================================================================
# SECTION 1: COMMON CONTRACT & CONFIGURATION (TV1 - Bùi Văn Quang [MSV: 2A202602688])
# ==============================================================================

DEFAULT_WIDTH = 640
DEFAULT_HEIGHT = 480
DEFAULT_FPS = 30
RGB_CHANNELS = 3
DEPTH_CHANNELS = 1  # 16-bit uint16

def calculate_frame_sizes(width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT):
    """Calculate raw payload size per RGB-D frame."""
    rgb_size = width * height * RGB_CHANNELS * np.dtype(np.uint8).itemsize
    depth_size = width * height * DEPTH_CHANNELS * np.dtype(np.uint16).itemsize
    total_size = rgb_size + depth_size
    return {
        "rgb_size_bytes": rgb_size,
        "depth_size_bytes": depth_size,
        "total_size_bytes": total_size
    }

class FrameMetadata:
    """Standard metadata packet sent from Producer to Consumer."""
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
            "payload_size": self.payload_size
        }

# ==============================================================================
# SECTION 2: PRODUCER & MEMORY SLOT MANAGEMENT (TV2 - Data Source & Memory)
# Note: TV2 implements pacing, realistic synthetic noise, and ring-buffer slots here.
# ==============================================================================

def generate_synthetic_rgbd(width, height, frame_id, seed=0):
    """
    Synthetic RGB-D generator simulating RealSense D435/D455 frames.
    - RGB: uint8 [0..255]
    - Depth: uint16 [0..65535] (distance in millimeters)
    """
    # Deterministic pattern based on seed and frame_id
    rng = np.random.default_rng(seed + frame_id)
    rgb = rng.integers(0, 256, size=(height, width, RGB_CHANNELS), dtype=np.uint8)
    depth = rng.integers(500, 5000, size=(height, width), dtype=np.uint16)
    return rgb, depth

def camera_producer(camera_id, num_frames, target_fps, width, height,
                    meta_queue, data_queue=None, shm_info=None,
                    stop_event=None, seed=42):
    """
    Producer worker process representing one RGB-D camera.
    (Assigned to TV2 for fine-tuning pacing, slot lifetimes, and overload policy)
    """
    frame_interval = 1.0 / target_fps
    sizes = calculate_frame_sizes(width, height)
    total_size = sizes["total_size_bytes"]
    cam_seed = seed + camera_id * 1000

    shm_block = None
    if shm_info is not None:
        try:
            shm_block = shared_memory.SharedMemory(name=shm_info["name"])
        except Exception as e:
            print(f"[Producer-{camera_id}] Error attaching to SHM: {e}")
            return

    next_frame_time = time.perf_counter()

    for frame_id in range(num_frames):
        if stop_event is not None and stop_event.is_set():
            break

        # Precise pacing
        now = time.perf_counter()
        sleep_dur = next_frame_time - now
        if sleep_dur > 0:
            time.sleep(sleep_dur)
        next_frame_time = max(time.perf_counter() + frame_interval, next_frame_time + frame_interval)

        t_produced = time.perf_counter()
        rgb, depth = generate_synthetic_rgbd(width, height, frame_id, seed=cam_seed)

        slot_id = -1
        t_pushed = time.perf_counter()

        if shm_block is not None:
            # Shared memory zero-copy transfer mode (TV2 slot assignment)
            num_slots = shm_info["num_slots"]
            slot_id = (camera_id * 1000 + frame_id) % num_slots
            offset = slot_id * total_size
            raw_bytes = rgb.tobytes() + depth.tobytes()
            shm_block.buf[offset:offset + total_size] = raw_bytes
            
            meta = FrameMetadata(
                camera_id=camera_id,
                frame_id=frame_id,
                slot_id=slot_id,
                t_produced=t_produced,
                t_pushed=t_pushed,
                payload_size=total_size
            )
            meta_queue.put(meta.to_dict())
        else:
            # Baseline Queue transfer mode (Copies raw frame into multiprocessing.Queue)
            meta = FrameMetadata(
                camera_id=camera_id,
                frame_id=frame_id,
                slot_id=-1,
                t_produced=t_produced,
                t_pushed=t_pushed,
                payload_size=total_size
            )
            data_queue.put((meta.to_dict(), rgb, depth))

    if shm_block is not None:
        shm_block.close()

# ==============================================================================
# SECTION 3: CONSUMER, TELEMETRY & LOGGER (TV3 - Metrics & CSV Telemetry)
# Note: TV3 implements telemetry recording, statistical calculations, and CSV schemas.
# ==============================================================================

def consumer_logger(meta_queue, data_queue, total_expected_frames, 
                    out_csv_path, shm_info=None, stop_event=None):
    """
    Consumer process acting as perception ingest pipeline.
    Measures latency, throughput, frame drops, and writes telemetry CSV.
    (Assigned to TV3 for metric calculation and schema compliance)
    """
    records = []
    received_count = 0
    shm_block = None

    if shm_info is not None:
        try:
            shm_block = shared_memory.SharedMemory(name=shm_info["name"])
        except Exception as e:
            print(f"[Consumer] Error attaching to SHM: {e}")
            return

    os.makedirs(os.path.dirname(os.path.abspath(out_csv_path)), exist_ok=True)

    with open(out_csv_path, "w", encoding="utf-8") as f:
        # Standard telemetry header agreed in contract_spec.md
        f.write("timestamp,camera_id,frame_id,slot_id,t_produced,t_consumed,latency_ms,payload_bytes\n")

        while received_count < total_expected_frames:
            if stop_event is not None and stop_event.is_set() and meta_queue.empty():
                break

            try:
                if shm_block is not None:
                    # In SHM mode, read metadata from queue and access payload from memory buffer
                    meta_dict = meta_queue.get(timeout=2.0)
                    slot_id = meta_dict["slot_id"]
                    payload_size = meta_dict["payload_size"]
                    
                    # Simulate zero-copy buffer read access by consumer
                    offset = slot_id * payload_size
                    _ = shm_block.buf[offset:offset + payload_size]

                    t_consumed = time.perf_counter()
                    latency_ms = (t_consumed - meta_dict["t_produced"]) * 1000.0

                    row = f"{t_consumed:.6f},{meta_dict['camera_id']},{meta_dict['frame_id']}," \
                          f"{slot_id},{meta_dict['t_produced']:.6f}," \
                          f"{t_consumed:.6f},{latency_ms:.3f},{payload_size}\n"
                    f.write(row)
                    received_count += 1
                else:
                    # In Queue mode, read tuple from data_queue
                    packet = data_queue.get(timeout=2.0)
                    meta_dict, rgb, depth = packet
                    t_consumed = time.perf_counter()
                    latency_ms = (t_consumed - meta_dict["t_produced"]) * 1000.0

                    row = f"{t_consumed:.6f},{meta_dict['camera_id']},{meta_dict['frame_id']}," \
                          f"-1,{meta_dict['t_produced']:.6f}," \
                          f"{t_consumed:.6f},{latency_ms:.3f},{meta_dict['payload_size']}\n"
                    f.write(row)
                    received_count += 1

                if received_count % 100 == 0:
                    f.flush()

            except Exception:
                # Timeout or empty queue during shutdown
                if stop_event is not None and stop_event.is_set():
                    break

        f.flush()

    if shm_block is not None:
        shm_block.close()

# ==============================================================================
# SECTION 4: BENCHMARK RUNNER & INTEGRATION (TV1 - Bùi Văn Quang & TV5)
# ==============================================================================

def run_benchmark(num_cameras=1, target_fps=30, duration_sec=5,
                  width=640, height=480, mode="shm", out_dir="results", seed=42):
    """
    Main orchestration entrypoint for single benchmark run.
    Integrates producers and consumer, enforces resource cleanup.
    """
    total_frames_per_camera = int(target_fps * duration_sec)
    total_expected = total_frames_per_camera * num_cameras
    sizes = calculate_frame_sizes(width, height)
    frame_size_bytes = sizes["total_size_bytes"]

    timestamp_str = time.strftime("%Y%m%d_%H%M%S")
    run_tag = f"run_{timestamp_str}_{num_cameras}cam_{target_fps}fps_{mode}"
    run_dir = os.path.join(out_dir, run_tag)
    os.makedirs(run_dir, exist_ok=True)

    telemetry_csv = os.path.join(run_dir, "frames_telemetry.csv")
    config_file = os.path.join(run_dir, "config.json")
    summary_file = os.path.join(run_dir, "summary.json")

    run_config = {
        "run_tag": run_tag,
        "num_cameras": num_cameras,
        "target_fps": target_fps,
        "duration_sec": duration_sec,
        "width": width,
        "height": height,
        "mode": mode,
        "seed": seed,
        "frame_size_bytes": frame_size_bytes,
        "total_expected_frames": total_expected
    }

    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(run_config, f, indent=2)

    print("=" * 70)
    print(f"STARTING BENCHMARK: {run_tag}")
    print(f"Cameras: {num_cameras} | Target FPS: {target_fps} | Duration: {duration_sec}s")
    print(f"Resolution: {width}x{height} RGB-D ({frame_size_bytes / 1024 / 1024:.2f} MB/frame)")
    print(f"IPC Mode: {mode.upper()} | Output Dir: {run_dir}")
    print("=" * 70)

    # Windows multiprocessing safety
    ctx = mp.get_context("spawn")
    meta_queue = ctx.Queue()
    data_queue = ctx.Queue() if mode == "queue" else None
    stop_event = ctx.Event()

    shm = None
    shm_info = None

    if mode == "shm":
        num_slots = max(16, num_cameras * 4)
        total_shm_size = num_slots * frame_size_bytes
        shm_name = f"t7_bench_{os.getpid()}_{int(time.time())}"
        try:
            shm = shared_memory.SharedMemory(name=shm_name, create=True, size=total_shm_size)
            shm_info = {"name": shm_name, "num_slots": num_slots, "size": total_shm_size}
            print(f"[SHM] Allocated {total_shm_size / 1024 / 1024:.2f} MB across {num_slots} slots.")
        except Exception as e:
            print(f"[!] Fatal: Could not create shared memory: {e}")
            return False

    producers = []
    t_start = time.perf_counter()

    # Launch consumer
    consumer = ctx.Process(
        target=consumer_logger,
        args=(meta_queue, data_queue, total_expected, telemetry_csv, shm_info, stop_event)
    )
    consumer.start()

    # Launch producers
    for cam_id in range(num_cameras):
        p = ctx.Process(
            target=camera_producer,
            args=(cam_id, total_frames_per_camera, target_fps, width, height,
                  meta_queue, data_queue, shm_info, stop_event, seed)
        )
        p.start()
        producers.append(p)

    # Await producers completion
    for p in producers:
        p.join()

    # Allow consumer to drain remaining items
    time.sleep(0.5)
    stop_event.set()
    consumer.join(timeout=5.0)
    if consumer.is_alive():
        consumer.terminate()

    t_end = time.perf_counter()
    actual_duration = t_end - t_start

    # Clean up Shared Memory safely (Windows strict requirement)
    if shm is not None:
        try:
            shm.close()
            shm.unlink()
            print("[SHM] Shared memory successfully released and unlinked.")
        except Exception as e:
            print(f"[!] Warning cleaning SHM: {e}")

    # Compute quick summary
    frames_received = 0
    if os.path.exists(telemetry_csv):
        with open(telemetry_csv, "r", encoding="utf-8") as f:
            lines = f.readlines()
            frames_received = max(0, len(lines) - 1)

    achieved_fps = frames_received / actual_duration if actual_duration > 0 else 0
    throughput_mb_s = (frames_received * frame_size_bytes) / (actual_duration * 1024 * 1024) if actual_duration > 0 else 0

    summary = {
        "run_tag": run_tag,
        "mode": mode,
        "num_cameras": num_cameras,
        "actual_duration_sec": round(actual_duration, 3),
        "total_expected_frames": total_expected,
        "frames_received": frames_received,
        "achieved_total_fps": round(achieved_fps, 2),
        "throughput_mb_s": round(throughput_mb_s, 2),
        "status": "VALID" if frames_received >= total_expected * 0.9 else "DEGRADED"
    }

    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("-" * 70)
    print(f"BENCHMARK COMPLETE:")
    print(f"Duration: {actual_duration:.2f}s | Received: {frames_received}/{total_expected} frames")
    print(f"Throughput: {throughput_mb_s:.2f} MB/s | Achieved Total FPS: {achieved_fps:.2f}")
    print(f"Results stored at: {run_dir}")
    print("=" * 70)
    return True

def main():
    parser = argparse.ArgumentParser(description="Multi-Camera RGB-D Bandwidth Profiler (Topic T7)")
    parser.add_argument("--cameras", type=int, default=2, help="Number of simulated cameras (e.g. 1, 2, 4, 8)")
    parser.add_argument("--fps", type=int, default=30, help="Target FPS per camera")
    parser.add_argument("--duration", type=int, default=5, help="Test duration in seconds")
    parser.add_argument("--width", type=int, default=DEFAULT_WIDTH, help="Image width")
    parser.add_argument("--height", type=int, default=DEFAULT_HEIGHT, help="Image height")
    parser.add_argument("--mode", type=str, choices=["shm", "queue"], default="shm",
                        help="Transfer mechanism: 'shm' (Zero-copy Shared Memory) or 'queue' (Copy-based IPC Queue)")
    parser.add_argument("--outdir", type=str, default="results", help="Directory to save telemetry and metrics")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducible synthetic frames")

    args = parser.parse_args()

    run_benchmark(
        num_cameras=args.cameras,
        target_fps=args.fps,
        duration_sec=args.duration,
        width=args.width,
        height=args.height,
        mode=args.mode,
        out_dir=args.outdir,
        seed=args.seed
    )

if __name__ == "__main__":
    mp.freeze_support()  # Crucial for Windows multiprocessing support
    main()

