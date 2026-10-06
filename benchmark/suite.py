import argparse
import json
import random
import subprocess
import sys
import time
from pathlib import Path

PROFILES = [('P0', 424, 240, 5), ('P1', 640, 480, 30), ('P2', 1280, 720, 30)]


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--set', choices=['matrix', 'failure', 'all'], default='all')
    p.add_argument('--root', required=True)
    p.add_argument('--duration', type=float, default=30)
    p.add_argument('--repeats', type=int, default=3)
    p.add_argument('--seed', type=int, default=42)
    p.add_argument('--slots', type=int, default=32)
    a = p.parse_args()
    if a.repeats < 1:
        p.error('repeats must be positive')
    root = Path(a.root)
    root.mkdir(parents=True, exist_ok=False)
    jobs = []
    rng = random.Random(a.seed)
    for rep in range(1, a.repeats + 1):
        block = []
        if a.set in ('matrix', 'all'):
            for profile, w, h, fps in PROFILES:
                for n in [1, 2, 4, 6]:
                    block.append((f'matrix_{profile}_N{n}_r{rep}', n, w, h, fps, 0, 'fifo'))
        if a.set in ('failure', 'all'):
            for delay in [0, 15, 30]:
                for policy in ['fifo', 'latest']:
                    block.append((f'failure_D{delay}_{policy}_r{rep}', 6, 1280, 720, 30, delay, policy))
        rng.shuffle(block)  # block by repetition to reduce time/temperature confounding
        jobs.extend(block)
    (root / 'order.json').write_text(json.dumps(jobs, indent=2), encoding='utf-8')
    for index, (name, n, w, h, fps, delay, policy) in enumerate(jobs, 1):
        run_path = root / name
        command = [sys.executable, '-m', 'benchmark.bench', '--cameras', str(n),
                   '--width', str(w), '--height', str(h), '--fps', str(fps),
                   '--duration', str(a.duration), '--slots', str(a.slots), '--delay-ms', str(delay),
                   '--policy', policy, '--seed', str(a.seed), '--out', str(run_path)]
        print(f'[{index}/{len(jobs)}] {name}', flush=True)
        # Exact argument list, no shell interpolation.
        (root / f'{name}.command.json').write_text(json.dumps(command, indent=2), encoding='utf-8')
        with (root / f'{name}.console.log').open('w', encoding='utf-8') as log:
            result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT,
                                    timeout=a.duration + 90)
        if result.returncode:
            raise SystemExit(f'Run invalid: {name}. Inspect log; do not silently keep running.')
        time.sleep(2)


if __name__ == '__main__':
    main()
