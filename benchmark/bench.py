"""Synthetic RGB-D software benchmark; no USB/camera measurement.

Lead Owner (Producer & Memory): Thành viên 2 (TV2 - Source & Memory Lead)
Collaborator (Consumer & Metrics): Thành viên 3 (TV3 - Metrics Lead)
"""
import argparse
import csv
import json
import multiprocessing as mp
import platform
import queue
import subprocess
import time
from pathlib import Path
from multiprocessing.shared_memory import SharedMemory
import numpy as np
import psutil


def producer(cam, cfg, name, free, output, ready, start, stop, counts):
    """Producer process for a single virtual camera (Owned by TV2).

    Responsibilities:
    1. Generate seeded static RGB8 + uint16 depth payload (5 bytes/pixel).
    2. Synchronize start using host perf_counter clock and start.value.
    3. Maintain pacing: pace frames at fixed 1/fps intervals without burst catch-up.
    4. Acquire free slot from `free` Queue (zero-copy buffer allocated in SharedMemory).
    5. Copy payload template into slot slice: (cam * slots + slot) * frame_bytes.
    6. Send metadata tuple: (cam, seq, slot, t_capture, t_enqueue) via output Queue.
    7. Update atomic counters: attempted, enqueued, rejected, schedule_missed.
    8. Adhere to SharedMemory lifetime: close local handle upon exit without unlinking.
    """
    shm = SharedMemory(name=name)
    view = np.ndarray((cfg['pool_bytes'],), np.uint8, buffer=shm.buf)
    rng = np.random.default_rng(cfg['seed'] + cam)
    rgb = rng.integers(0, 256, (cfg['height'], cfg['width'], 3), dtype=np.uint8)
    depth = rng.integers(500, 5000, (cfg['height'], cfg['width']), dtype=np.uint16)
    template = np.concatenate((rgb.ravel(), depth.view(np.uint8).ravel()))
    base = cam * 4  # attempted, enqueued, rejected, schedule_missed
    ready.put(cam)
    try:
        while not start.value and not stop.is_set():
            time.sleep(.001)
        end = start.value + cfg['duration']
        for seq in range(int(round(cfg['fps'] * cfg['duration']))):
            deadline = start.value + seq / cfg['fps']
            if stop.wait(max(0, deadline - time.perf_counter())):
                break
            now = time.perf_counter()
            if now >= end or now - deadline >= 1 / cfg['fps']:
                counts[base + 3] += 1
                continue  # skip missed schedule slots; do not emit a catch-up burst
            counts[base] += 1
            try:
                slot = free.get(timeout=.002)
            except queue.Empty:
                counts[base + 2] += 1
                continue
            offset = (cam * cfg['slots'] + slot) * cfg['frame_bytes']
            t_capture = time.perf_counter()
            np.copyto(view[offset:offset + cfg['frame_bytes']], template)
            t_enqueue = time.perf_counter()
            if t_enqueue >= end:
                free.put(slot)
                counts[base + 2] += 1
                continue
            output.put((cam, seq, slot, t_capture, t_enqueue))
            counts[base + 1] += 1
    finally:
        del view
        shm.close()  # Parent retains the lifetime handle, including on Windows


def git_value(*args):
    try:
        return subprocess.check_output(['git', *args], stderr=subprocess.DEVNULL,
                                       text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return 'unavailable'


def run(args):
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)  # never overwrite an earlier run
    cfg = vars(args).copy()
    cfg['frame_bytes'] = args.width * args.height * 5
    cfg['pool_bytes'] = cfg['frame_bytes'] * args.cameras * args.slots
    if cfg['pool_bytes'] > min(1_500_000_000, max(psutil.virtual_memory().available * 0.85, psutil.virtual_memory().total * 0.20)):
        raise RuntimeError('Pool exceeds memory budget. Lower resolution/slots; record the change.')
    config = {**cfg, 'python': platform.python_version(), 'platform': platform.platform(),
              'logical_cpus': psutil.cpu_count(), 'ram_bytes': psutil.virtual_memory().total,
              'git_commit': git_value('rev-parse', 'HEAD'),
              'git_dirty': git_value('status', '--porcelain'),
              'source': 'seeded static RGB8 + uint16 depth; full copy each frame',
              'clock': 'time.perf_counter; host software clock', 'gpu': 'NA',
              'viewer': False, 'utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
    (out / 'config.json').write_text(json.dumps(config, indent=2), encoding='utf-8')
    ctx = mp.get_context('spawn')
    shm = SharedMemory(create=True, size=cfg['pool_bytes'])
    output = ctx.Queue(maxsize=args.cameras * args.slots)
    ready = ctx.Queue()
    frees = [ctx.Queue(maxsize=args.slots) for _ in range(args.cameras)]
    for free in frees:
        for slot in range(args.slots):
            free.put(slot)
    start, stop = ctx.Value('d', 0), ctx.Event()
    counts = ctx.Array('q', args.cameras * 4, lock=False)
    workers = [ctx.Process(target=producer, args=(cam, cfg, shm.name, frees[cam],
                  output, ready, start, stop, counts)) for cam in range(args.cameras)]
    completed = [0] * args.cameras
    stale = [0] * args.cameras
    late = [0] * args.cameras
    shutdown = [0] * args.cameras
    pending = {}
    latencies, waits, copy_ms, resource_rows = [], [], [], []
    frames = []
    view = np.ndarray((cfg['pool_bytes'],), np.uint8, buffer=shm.buf)
    copied = np.empty(cfg['frame_bytes'], np.uint8)
    status = 'ok'
    failure = None

    def release(item, state, finish=None):
        cam, seq, slot, tc, tq = item
        frees[cam].put(slot)
        frames.append([cam, seq, state, tc, tq, finish if finish is not None else '',
                       (finish - tc) * 1000 if finish is not None else ''])

    try:
        for worker in workers:
            worker.start()
        for _ in workers:
            ready.get(timeout=30)
        probes = []
        for pid in [__import__('os').getpid(), *[w.pid for w in workers]]:
            try:
                probes.append(psutil.Process(pid))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        config['resource_monitor_processes'] = len(probes)
        config['resource_monitor_expected'] = args.cameras + 1
        (out / 'config.json').write_text(json.dumps(config, indent=2), encoding='utf-8')
        for probe in probes:
            probe.cpu_percent(None)
        psutil.cpu_percent(None)
        start.value = time.perf_counter() + 1  # exclude process startup from measurement
        stop.wait(max(0, start.value - time.perf_counter()))
        end = start.value + args.duration
        next_sample = start.value + .5
        while time.perf_counter() < end:
            if any(w.exitcode not in (None, 0) for w in workers):
                raise RuntimeError('Producer process failed')
            now = time.perf_counter()
            if now >= next_sample:
                cpu, rss = 0., 0
                for probe in probes:
                    try:
                        cpu += probe.cpu_percent(None)
                        rss += probe.memory_info().rss
                    except psutil.NoSuchProcess:
                        pass
                backlog = sum(counts[c * 4 + 1] - completed[c] - stale[c] - late[c]
                              for c in range(args.cameras))
                resource_rows.append([now - start.value, cpu / (psutil.cpu_count() or 1) if len(probes) == args.cameras + 1 else None,
                                      psutil.cpu_percent(None), rss / 1e6 if len(probes) == args.cameras + 1 else None,
                                      psutil.virtual_memory().percent, max(0, backlog)])
                next_sample = now + .5
            if args.policy == 'latest':
                # Drain only a bounded batch, keeping the newest per camera.
                for _ in range(args.cameras * args.slots):
                    try:
                        item = output.get_nowait()
                    except queue.Empty:
                        break
                    cam = item[0]
                    if cam in pending:
                        stale[cam] += 1
                        release(pending[cam], 'stale')
                    pending[cam] = item  # replacement preserves fair camera order
                if not pending:
                    try:
                        item = output.get(timeout=.005)
                        pending[item[0]] = item
                    except queue.Empty:
                        continue
                cam = next(iter(pending))
                item = pending.pop(cam)
            else:
                try:
                    item = output.get(timeout=.005)
                except queue.Empty:
                    continue
            cam, seq, slot, tc, tq = item
            t_receive = time.perf_counter()
            offset = (cam * args.slots + slot) * cfg['frame_bytes']
            np.copyto(copied, view[offset:offset + cfg['frame_bytes']])
            t_copy = time.perf_counter()
            time.sleep(args.delay_ms / 1000)  # delay per RGB-D frameset, not per camera set
            finish = time.perf_counter()
            if finish < end:
                completed[cam] += 1
                latencies.append((finish - tc) * 1000)
                waits.append((t_receive - tq) * 1000)
                copy_ms.append((t_copy - t_receive) * 1000)
                release(item, 'completed', finish)
            else:
                late[cam] += 1
                release(item, 'completed_after_window', finish)
    except BaseException as exc:
        status, failure = 'invalid', repr(exc)
    finally:
        stop.set()
        # Draining frees queue feeder threads before join; never use empty()/qsize().
        join_deadline = time.perf_counter() + 10
        while any(w.is_alive() for w in workers) and time.perf_counter() < join_deadline:
            try:
                item = output.get(timeout=.02)
                shutdown[item[0]] += 1
                release(item, 'shutdown_backlog')
            except queue.Empty:
                pass
            for worker in workers:
                if worker.pid:
                    worker.join(timeout=0)
        for worker in workers:
            if worker.pid and worker.is_alive():
                worker.terminate()
                status = 'invalid'
                failure = 'Worker required forced termination'
            if worker.pid:
                worker.join(timeout=2)
                if worker.exitcode != 0:
                    status = 'invalid'
        while True:
            try:
                item = output.get_nowait()
                shutdown[item[0]] += 1
                release(item, 'shutdown_backlog')
            except queue.Empty:
                break
        for item in pending.values():
            shutdown[item[0]] += 1
            release(item, 'shutdown_backlog')
        pending.clear()
        del view
        shm.close()
        shm.unlink()  # on Windows deletion occurs after all handles are closed
        for q in [output, ready, *frees]:
            q.cancel_join_thread()
            q.close()
    scheduled = int(round(args.fps * args.duration))
    percam = []
    for cam in range(args.cameras):
        attempted, enqueued, rejected, missed = list(counts[cam * 4:cam * 4 + 4])
        accounting_ok = (scheduled == attempted + missed and attempted == enqueued + rejected
                         and enqueued == completed[cam] + stale[cam] + late[cam] + shutdown[cam])
        if not accounting_ok:
            status = 'invalid'
        percam.append({'camera': cam, 'scheduled': scheduled, 'attempted': attempted,
                       'enqueued': enqueued, 'rejected': rejected, 'schedule_missed': missed,
                       'completed': completed[cam], 'stale': stale[cam],
                       'late_completion': late[cam], 'shutdown_backlog': shutdown[cam],
                       'fps': completed[cam] / args.duration, 'accounting_ok': accounting_ok})
    def percentile(values):
        return float(np.percentile(values, 95)) if values else None
    total_scheduled = args.cameras * scheduled
    done = sum(completed)
    summary = {'status': status, 'failure': failure,
               'cameras': args.cameras, 'width': args.width, 'height': args.height,
               'target_fps': args.fps, 'duration_s': args.duration,
               'delay_ms': args.delay_ms, 'policy': args.policy, 'slots': args.slots,
               'aggregate_fps': done / args.duration, 'min_camera_fps': min(completed) / args.duration,
               'completion_ratio': done / total_scheduled,
               'explicit_drop_pct': 100 * (sum(p['rejected'] for p in percam) + sum(stale)) / total_scheduled,
               'deadline_miss_pct': 100 * sum(p['schedule_missed'] for p in percam) / total_scheduled,
               'backlog_at_end': sum(shutdown) + sum(late),
               'latency_mean_ms': float(np.mean(latencies)) if latencies else None,
               'latency_p95_ms': percentile(latencies), 'queue_wait_p95_ms': percentile(waits),
               'copy_p95_ms': percentile(copy_ms),
               'target_payload_Mbps': args.cameras * args.width * args.height * args.fps * 40 / 1e6,
               'completed_payload_MBps': done * cfg['frame_bytes'] / args.duration / 1e6,
               'pool_MB': cfg['pool_bytes'] / 1e6,
               'cpu_normalized_mean_pct': float(np.mean([r[1] for r in resource_rows if r[1] is not None])) if any(r[1] is not None for r in resource_rows) else None,
               'rss_sum_peak_MB': max([r[3] for r in resource_rows if r[3] is not None], default=None),
               'backlog_sample_peak': max([r[5] for r in resource_rows], default=None),
               'gpu': 'NA', 'per_camera': percam}
    for name, header, rows in [
        ('frames.csv', ['camera','seq','status','capture_s','enqueue_s','finish_s','latency_ms'], frames),
        ('resources.csv', ['elapsed_s','cpu_normalized_pct','system_cpu_pct','rss_sum_MB','system_memory_pct','backlog_proxy'], resource_rows),
        ('per_camera.csv', list(percam[0]), [list(row.values()) for row in percam])]:
        with (out / name).open('w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(rows)
    (out / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k != 'per_camera'}, indent=2), flush=True)
    return 0 if status == 'ok' else 2


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cameras', type=int, default=1)
    parser.add_argument('--width', type=int, default=424)
    parser.add_argument('--height', type=int, default=240)
    parser.add_argument('--fps', type=int, default=5)
    parser.add_argument('--duration', type=float, default=30)
    parser.add_argument('--slots', type=int, default=32)
    parser.add_argument('--delay-ms', type=float, default=0)
    parser.add_argument('--policy', choices=['fifo','latest'], default='fifo')
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    if min(args.cameras, args.width, args.height, args.fps, args.slots) <= 0 or args.duration <= 0 or args.delay_ms < 0:
        parser.error('Dimensions/count/FPS/duration must be positive; delay must be nonnegative')
    if abs(args.fps * args.duration - round(args.fps * args.duration)) > 1e-6:
        parser.error('fps * duration must be an integer')
    raise SystemExit(run(args))


if __name__ == '__main__':
    mp.freeze_support()
    main()
