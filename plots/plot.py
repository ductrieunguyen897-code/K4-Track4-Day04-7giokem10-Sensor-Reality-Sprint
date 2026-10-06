"""
Plot and aggregate TV3 metrics for the T7 synthetic multi-camera benchmark.

Owner: TV3 - Metrics & Telemetry.

Reads every `summary.json` produced by `bench.py` under a session root, writes
`summary.csv` (one row per run) and `aggregate.csv` (mean/SD per condition),
then renders the figures required by the plan (section 14.2):

  * matrix_min_camera_fps / matrix_aggregate_fps / matrix_latency_p95 /
    matrix_explicit_drop / matrix_completion_ratio   -> FPS/latency/drop vs N
  * failure_policy_tradeoff                          -> FIFO vs latest vs delay
  * backlog_<run>                                    -> backlog over time (r1)
  * resources_<run>                                  -> CPU/RAM over time

Design rules taken from docs/integration_review.md (TV4 review items):
  - a run is only aggregated when status=ok, accounting_all_ok and completed>0;
  - the group key includes slots, duration, seed and code commit so conditions
    are never silently merged;
  - per-metric n_valid is recorded and missing CPU/RAM is reported as NA, never
    plotted as zero.

Usage:
    python plots/plot.py --root results/session_matrix_01
"""

import csv
import json
import argparse
import statistics
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Metrics aggregated and their human-readable labels / units.
AGG_METRICS = [
    ("min_camera_fps", "FPS camera chậm nhất (frameset/s)"),
    ("aggregate_fps", "FPS tổng (frameset/s)"),
    ("completion_ratio", "Tỷ lệ hoàn thành (0-1)"),
    ("explicit_drop_pct", "Drop phần mềm rõ ràng (%)"),
    ("deadline_miss_pct", "Lỡ nhịp producer (%)"),
    ("backlog_at_end", "Backlog cuối window (frameset)"),
    ("latency_mean_ms", "Latency trung bình (ms)"),
    ("latency_p95_ms", "Latency P95 (ms)"),
    ("queue_wait_p95_ms", "Queue wait P95 (ms)"),
    ("copy_p95_ms", "Consumer copy P95 (ms)"),
    ("cpu_normalized_mean_pct", "CPU chuẩn hóa (%)"),
    ("rss_sum_peak_MB", "RSS tổng đỉnh (MB)"),
]

GROUP_KEYS = [
    "family", "width", "height", "target_fps", "cameras",
    "delay_ms", "policy", "slots", "duration_s", "seed", "code_commit",
]


def load_runs(root):
    """Load every summary.json under root; reject invalid runs loudly."""
    runs, invalid = [], []
    for path in sorted(root.rglob("summary.json")):
        row = json.loads(path.read_text(encoding="utf-8"))
        row["run_id"] = path.parent.name
        row["_dir"] = path.parent
        if row.get("status") != "ok" or not row.get("accounting_all_ok", False):
            invalid.append((row["run_id"], row.get("status"), row.get("failure")))
            continue
        if not row.get("frames_received"):
            invalid.append((row["run_id"], row.get("status"), "no completed frames"))
            continue
        runs.append(row)
    return runs, invalid


def write_summary_csv(root, runs):
    columns = [k for k in runs[0] if k not in ("per_camera", "_dir")]
    with (root / "summary.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(runs)


def build_aggregate(runs):
    groups = {}
    for row in runs:
        key = tuple(row.get(k) for k in GROUP_KEYS)
        groups.setdefault(key, []).append(row)

    agg = []
    for key, rows in sorted(groups.items(), key=lambda kv: [str(x) for x in kv[0]]):
        record = dict(zip(GROUP_KEYS, key))
        record["n_runs"] = len(rows)
        for metric, _ in AGG_METRICS:
            values = [r[metric] for r in rows if r.get(metric) is not None]
            record[metric + "_n"] = len(values)
            record[metric + "_mean"] = statistics.mean(values) if values else None
            record[metric + "_sd"] = (
                statistics.stdev(values) if len(values) > 1 else (0.0 if values else None)
            )
        agg.append(record)
    return agg


def write_aggregate_csv(root, agg):
    with (root / "aggregate.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(agg[0]))
        writer.writeheader()
        writer.writerows(agg)


def _matrix_rows(agg):
    """Matrix groups only: delay 0, FIFO, family=matrix, one profile per curve."""
    return [
        r for r in agg
        if r["family"] == "matrix" and r["delay_ms"] == 0 and r["policy"] == "fifo"
    ]


def plot_matrix(out, agg, metric, label, fname):
    rows = _matrix_rows(agg)
    if not rows:
        return False
    fig, ax = plt.subplots(figsize=(8, 4.8))
    profiles = sorted({(r["width"], r["height"], r["target_fps"]) for r in rows})
    for profile in profiles:
        data = [r for r in rows if (r["width"], r["height"], r["target_fps"]) == profile]
        data.sort(key=lambda r: r["cameras"])
        ax.errorbar(
            [r["cameras"] for r in data],
            [r[metric + "_mean"] for r in data],
            yerr=[r[metric + "_sd"] or 0 for r in data],
            marker="o", capsize=4, label=f"{profile[0]}x{profile[1]} @ {profile[2]} FPS",
        )
    ax.set(xlabel="Số virtual camera (N)", ylabel=label,
           title="Pipeline RGB-D tổng hợp trên CPU; chưa đo USB")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out / fname, dpi=180)
    plt.close(fig)
    return True


def plot_failure_tradeoff(out, agg):
    rows = [r for r in agg if r["family"] == "failure"]
    if not rows:
        return False
    ref = rows[0]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    for ax, metric, label in zip(
        axes,
        ["latency_p95_ms", "explicit_drop_pct"],
        ["P95 latency (ms)", "Drop phần mềm rõ ràng (%)"],
    ):
        for policy in ("fifo", "latest"):
            data = [
                r for r in rows
                if r["policy"] == policy
                and all(r[k] == ref[k] for k in ("cameras", "width", "height", "target_fps"))
            ]
            data.sort(key=lambda r: r["delay_ms"])
            if not data:
                continue
            ax.errorbar(
                [r["delay_ms"] for r in data],
                [r[metric + "_mean"] for r in data],
                yerr=[r[metric + "_sd"] or 0 for r in data],
                marker="o", capsize=4, label=policy,
            )
        ax.set(xlabel="Delay cài vào mỗi frameset (ms)", ylabel=label)
        ax.grid(alpha=0.25)
        ax.legend()
    fig.suptitle(
        f"FIFO vs latest — {ref['cameras']} luồng {ref['width']}x{ref['height']} "
        f"@{ref['target_fps']} FPS, cùng pool"
    )
    fig.tight_layout()
    fig.savefig(out / "failure_policy_tradeoff.png", dpi=180)
    plt.close(fig)
    return True


def plot_backlog(out, runs):
    made = False
    for row in runs:
        if row["family"] != "failure" or "r1" not in row["run_id"]:
            continue
        res = row["_dir"] / "resources.csv"
        if not res.exists():
            continue
        with res.open(encoding="utf-8") as f:
            samples = list(csv.DictReader(f))
        if not samples:
            continue
        fig, ax = plt.subplots(figsize=(7, 3.8))
        ax.plot([float(r["elapsed_s"]) for r in samples],
                [float(r["backlog_proxy"]) for r in samples])
        ax.set(xlabel="Thời gian (s)", ylabel="Frameset đã enqueue chưa xử lý",
               title=row["run_id"])
        ax.grid(alpha=0.25)
        fig.tight_layout()
        fig.savefig(out / f"backlog_{row['run_id']}.png", dpi=180)
        plt.close(fig)
        made = True
    return made


def plot_resources(out, runs):
    """CPU/RAM time series; skipped when the monitor produced no valid sample."""
    made = False
    for row in runs:
        if "r1" not in row["run_id"]:
            continue
        res = row["_dir"] / "resources.csv"
        if not res.exists():
            continue
        with res.open(encoding="utf-8") as f:
            samples = list(csv.DictReader(f))
        cpu = [float(r["cpu_normalized_pct"]) for r in samples if r["cpu_normalized_pct"]]
        rss = [float(r["rss_sum_MB"]) for r in samples if r["rss_sum_MB"]]
        if not cpu and not rss:
            continue  # never plot missing CPU/RAM as zero
        fig, ax1 = plt.subplots(figsize=(7, 3.8))
        if cpu:
            ax1.plot([float(r["elapsed_s"]) for r in samples if r["cpu_normalized_pct"]],
                     cpu, color="tab:blue", label="CPU chuẩn hóa (%)")
            ax1.set_ylabel("CPU chuẩn hóa (%)", color="tab:blue")
        if rss:
            ax2 = ax1.twinx()
            ax2.plot([float(r["elapsed_s"]) for r in samples if r["rss_sum_MB"]],
                     rss, color="tab:red", label="RSS tổng (MB)")
            ax2.set_ylabel("RSS tổng (MB)", color="tab:red")
        ax1.set_xlabel("Thời gian (s)")
        ax1.set_title(f"Tài nguyên — {row['run_id']}")
        ax1.grid(alpha=0.25)
        fig.tight_layout()
        fig.savefig(out / f"resources_{row['run_id']}.png", dpi=180)
        plt.close(fig)
        made = True
    return made


def main():
    parser = argparse.ArgumentParser(description="Aggregate and plot T7 metrics (TV3)")
    parser.add_argument("--root", required=True, help="Session directory with run subfolders")
    parser.add_argument("--out", default=None, help="Plot directory (default: <root>/plots)")
    parser.add_argument("--min-repeats", type=int, default=3,
                        help="Warn when a condition has fewer valid repeats")
    args = parser.parse_args()

    root = Path(args.root)
    runs, invalid = load_runs(root)
    if not runs:
        raise SystemExit("No valid summaries found")
    out = Path(args.out) if args.out else root / "plots"
    out.mkdir(parents=True, exist_ok=True)

    if invalid:
        print("Skipped invalid runs (kept on disk, not aggregated):")
        for run_id, status, reason in invalid:
            print(f"  - {run_id}: status={status} reason={reason}")

    write_summary_csv(root, runs)
    agg = build_aggregate(runs)
    write_aggregate_csv(root, agg)

    # Completeness check: every condition should have the required repeats.
    for record in agg:
        if record["n_runs"] < args.min_repeats:
            print(f"[WARN] {record['family']} N={record['cameras']} "
                  f"delay={record['delay_ms']} {record['policy']}: "
                  f"only {record['n_runs']}/{args.min_repeats} valid runs")

    made = []
    for metric, label, fname in [
        ("min_camera_fps", "FPS camera chậm nhất", "matrix_min_camera_fps.png"),
        ("aggregate_fps", "FPS tổng", "matrix_aggregate_fps.png"),
        ("latency_p95_ms", "P95 latency (ms)", "matrix_latency_p95.png"),
        ("explicit_drop_pct", "Drop phần mềm (%)", "matrix_explicit_drop.png"),
        ("completion_ratio", "Tỷ lệ hoàn thành", "matrix_completion_ratio.png"),
    ]:
        if plot_matrix(out, agg, metric, label, fname):
            made.append(fname)
    if plot_failure_tradeoff(out, agg):
        made.append("failure_policy_tradeoff.png")
    plot_backlog(out, runs)
    plot_resources(out, runs)

    print(f"Wrote {root / 'summary.csv'}, {root / 'aggregate.csv'}")
    print(f"Plots in {out}: {', '.join(sorted(p.name for p in out.glob('*.png')))}")


if __name__ == "__main__":
    main()
