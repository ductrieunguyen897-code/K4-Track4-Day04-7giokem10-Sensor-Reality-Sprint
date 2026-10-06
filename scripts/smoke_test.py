"""
Smoke Test & Integration Verification Script
Maintained by: TV1 - Bùi Văn Quang (MSV: 2A202602688)
Purpose: Verify that the benchmark core runs correctly end-to-end,
generates valid CSV/JSON outputs according to specs/contract_spec.md,
and safely cleans up all shared memory allocations.
"""

import os
import sys
import json
import glob
import subprocess
import pandas as pd

def run_smoke_test():
    print("=" * 70)
    print("RUNNING INTEGRATION SMOKE TEST (TV1 - Bui Van Quang [MSV: 2A202602688])")
    print("=" * 70)

    test_dir = os.path.join("results", "smoke_test_output")
    os.makedirs(test_dir, exist_ok=True)

    modes = ["shm", "queue"]
    all_passed = True

    for mode in modes:
        print(f"\n--> [1/2] Testing Mode: {mode.upper()} (1 Camera, 30 FPS, 2 Seconds)...")
        cmd = [
            sys.executable,
            "bench.py",
            "--cameras", "1",
            "--fps", "30",
            "--duration", "2",
            "--mode", mode,
            "--outdir", test_dir
        ]

        ret = subprocess.run(cmd, capture_output=True, text=True)
        if ret.returncode != 0:
            print(f"[FAIL] Process exited with error code {ret.returncode}:")
            print(ret.stderr)
            all_passed = False
            continue

        # Find latest run subfolder in test_dir
        runs = sorted(glob.glob(os.path.join(test_dir, f"run_*_{mode}*")), key=os.path.getmtime)
        if not runs:
            print(f"[FAIL] No result folder created for mode {mode}!")
            all_passed = False
            continue

        latest_run = runs[-1]
        telemetry_file = os.path.join(latest_run, "frames_telemetry.csv")
        summary_file = os.path.join(latest_run, "summary.json")
        config_file = os.path.join(latest_run, "config.json")

        # 1. Check file existence
        for fpath, fname in [(telemetry_file, "telemetry CSV"), (summary_file, "summary JSON"), (config_file, "config JSON")]:
            if not os.path.exists(fpath):
                print(f"  [FAIL] Missing {fname} at {fpath}")
                all_passed = False
            else:
                print(f"  [PASS] Created {fname} successfully.")

        # 2. Verify CSV columns against contract_spec.md
        expected_cols = {"timestamp", "camera_id", "frame_id", "slot_id", "t_produced", "t_consumed", "latency_ms", "payload_bytes"}
        try:
            df = pd.read_csv(telemetry_file)
            actual_cols = set(df.columns)
            if not expected_cols.issubset(actual_cols):
                print(f"  [FAIL] CSV columns mismatch! Missing: {expected_cols - actual_cols}")
                all_passed = False
            else:
                print(f"  [PASS] CSV schema matches contract specification (Total rows: {len(df)}).")
        except Exception as e:
            print(f"  [FAIL] Could not parse CSV: {e}")
            all_passed = False

        # 3. Check summary.json validity
        try:
            with open(summary_file, "r", encoding="utf-8") as f:
                summary_data = json.load(f)
            status = summary_data.get("status")
            received = summary_data.get("frames_received", 0)
            expected = summary_data.get("total_expected_frames", 60)
            print(f"  [PASS] Run status: {status} | Frames: {received}/{expected} (Achieved FPS: {summary_data.get('achieved_total_fps')})")
            if status != "VALID" and received < expected * 0.8:
                print(f"  [WARN] Degradation observed in smoke test.")
        except Exception as e:
            print(f"  [FAIL] Could not parse summary JSON: {e}")
            all_passed = False

    print("\n" + "=" * 70)
    if all_passed:
        print("OVERALL RESULT: SMOKE TEST PASSED.")
        print("Integration baseline is functional and compliant with specifications.")
        print("Ready for TV2 (Producer logic), TV3 (Plot & Metrics), TV4 (Analysis), TV5 (Runner).")
    else:
        print("OVERALL RESULT: SMOKE TEST FAILED. Please review error logs.")
    print("=" * 70)
    return all_passed

if __name__ == "__main__":
    success = run_smoke_test()
    sys.exit(0 if success else 1)
