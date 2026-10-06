import argparse
import csv
import json
import statistics
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--root', required=True)
    a = p.parse_args()
    root = Path(a.root)
    summaries = []
    for path in sorted(root.rglob('summary.json')):
        row = json.loads(path.read_text(encoding='utf-8'))
        row['run_id'] = path.parent.name
        if row['status'] != 'ok':
            raise SystemExit(f'Invalid run: {path}')
        summaries.append(row)
    if not summaries:
        raise SystemExit('No summaries found')
    out = root / 'plots'
    out.mkdir(exist_ok=True)
    columns = [k for k in summaries[0] if k != 'per_camera']
    with (root / 'summary.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(summaries)
    groups = {}
    for row in summaries:
        family = 'matrix' if row['run_id'].startswith('matrix_') else 'failure' if row['run_id'].startswith('failure_') else 'manual'
        key = (family, row['width'], row['height'], row['target_fps'], row['cameras'], row['delay_ms'], row['policy'])
        groups.setdefault(key, []).append(row)
    metrics = ['min_camera_fps', 'latency_p95_ms', 'explicit_drop_pct', 'cpu_normalized_mean_pct']
    agg = []
    for key, rows in sorted(groups.items()):
        record = dict(zip(['family', 'width', 'height', 'target_fps', 'cameras', 'delay_ms', 'policy'], key))
        record['n_runs'] = len(rows)
        for metric in metrics:
            values = [r[metric] for r in rows if r[metric] is not None]
            record[metric + '_mean'] = statistics.mean(values) if values else None
            record[metric + '_sd'] = statistics.stdev(values) if len(values) > 1 else (0 if values else None)
        agg.append(record)
    with (root / 'aggregate.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(agg[0]))
        writer.writeheader()
        writer.writerows(agg)
    for metric, label in [('min_camera_fps', 'Slowest virtual camera FPS'),
                          ('latency_p95_ms', 'Per-run P95 latency, mean ± SD (ms)'),
                          ('explicit_drop_pct', 'Explicit software drop (%)')]:
        matrix = [r for r in summaries if r['run_id'].startswith('matrix_')]
        if not matrix:
            continue
        fig, ax = plt.subplots(figsize=(8, 4.8))
        for profile in sorted({(r['width'], r['height'], r['target_fps']) for r in matrix}):
            data = [r for r in agg if (r['width'], r['height'], r['target_fps']) == profile
                    and r['delay_ms'] == 0 and r['policy'] == 'fifo' and r['family'] == 'matrix']
            data.sort(key=lambda r: r['cameras'])
            ax.errorbar([r['cameras'] for r in data],
                        [r[metric + '_mean'] for r in data],
                        yerr=[r[metric + '_sd'] for r in data], marker='o', capsize=4,
                        label=f'{profile[0]}x{profile[1]} @ {profile[2]}')
        ax.set(xlabel='Virtual camera count', ylabel=label,
               title='Synthetic RGB-D software pipeline; USB not measured')
        ax.grid(alpha=.25)
        if matrix:
            ax.legend()
        fig.tight_layout()
        fig.savefig(out / f'matrix_{metric}.png', dpi=180)
        plt.close(fig)
    failure = [r for r in summaries if r['run_id'].startswith('failure_')]
    if failure:
        fig, axes = plt.subplots(1, 2, figsize=(10, 4))
        for policy in ['fifo', 'latest']:
            reference = failure[0]
            rows = [r for r in agg if all(r[k] == reference[k] for k in ['cameras', 'width', 'height', 'target_fps'])
                    and r['policy'] == policy and r['family'] == 'failure']
            rows.sort(key=lambda r: r['delay_ms'])
            for ax, metric, label in zip(axes, ['latency_p95_ms', 'explicit_drop_pct'],
                                         ['P95 latency (ms)', 'Explicit drop (%)']):
                ax.errorbar([r['delay_ms'] for r in rows], [r[metric + '_mean'] for r in rows],
                            yerr=[r[metric + '_sd'] for r in rows], marker='o', capsize=4, label=policy)
                ax.set(xlabel='Injected delay per frameset (ms)', ylabel=label)
                ax.grid(alpha=.25)
                ax.legend()
        fig.suptitle(f"Synthetic {reference['cameras']} streams {reference['width']}x{reference['height']} @{reference['target_fps']}; same pool")
        fig.tight_layout()
        fig.savefig(out / 'failure_policy_tradeoff.png', dpi=180)
        plt.close(fig)
    # Per-run time series gives evidence of backlog growth, not just one summary.
    for row in failure:
        if 'r1' not in row['run_id']:
            continue
        with (root / row['run_id'] / 'resources.csv').open(encoding='utf-8') as f:
            samples = list(csv.DictReader(f))
        fig, ax = plt.subplots(figsize=(7, 3.8))
        ax.plot([float(r['elapsed_s']) for r in samples],
                [float(r['backlog_proxy']) for r in samples])
        ax.set(xlabel='Elapsed (s)', ylabel='Enqueued but unprocessed frames', title=row['run_id'])
        ax.grid(alpha=.25)
        fig.tight_layout()
        fig.savefig(out / f"backlog_{row['run_id']}.png", dpi=180)
        plt.close(fig)
    print(f'Wrote {root / "summary.csv"}, {root / "aggregate.csv"}, {out}')


if __name__ == '__main__':
    main()
