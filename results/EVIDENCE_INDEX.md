# Chỉ mục bằng chứng thực nghiệm (Evidence Index) — Laptop HP Victus 16

**Ngày thực nghiệm:** 06/10/2026  
**Thiết bị:** Laptop HP Victus 16-e0xxx (AMD Ryzen 7 5800H, 8GB RAM, Windows 11 Home Single Language Build 26200)  
**Session kết quả chính thức:** `results/session_hp_victus_full/` (Đầy đủ 54 runs: 36 Matrix + 18 Failure, n=3 độc lập)  
**Code commit:** `7fc3a33` (nhánh `feat/tv5-integration`)  

---

## 1. Bảng đối chiếu Phát biểu — Bằng chứng thực tế

| Phát biểu / Claim | Loại phát biểu | Điều kiện & Run IDs | Bằng chứng định lượng (Mean ± SD) | File log, CSV & Plot minh chứng |
|---|---|---|---|---|
| **1. Pipeline phần mềm đáp ứng 100% Target FPS cho 6 camera P2 (6.6 Gbps raw payload)** | Quan sát thực nghiệm | `matrix_P2_N6_r1..r3` | - Achieved FPS/cam: $30.0 \pm 0.0$<br>- Aggregate FPS: $180.0 \pm 0.0$<br>- P95 Latency: $6.95 \pm 1.18\text{ ms}$<br>- Explicit Drop: $0.0\%$ | - [`aggregate.csv`](session_hp_victus_full/aggregate.csv)<br>- Đồ thị [`matrix_min_camera_fps.png`](session_hp_victus_full/plots/matrix_min_camera_fps.png)<br>- Đồ thị [`matrix_latency_p95_ms.png`](session_hp_victus_full/plots/matrix_latency_p95_ms.png) |
| **2. Consumer delay 15ms gây bão hòa hàng đợi FIFO, P95 Latency tăng vọt lên ~3.18 giây** | Quan sát thực nghiệm | `failure_D15_fifo_r1..r3` (so với F0 delay 0ms) | - Aggregate FPS giảm từ 180 về $61.1 \pm 0.3$<br>- P95 Latency tăng từ $7.03\text{ ms}$ lên **$3,175.09 \pm 42.64\text{ ms}$**<br>- Backlog cuối window: **191 frames** | - [`summary.csv`](session_hp_victus_full/summary.csv)<br>- Đồ thị [`backlog_failure_D15_fifo_r1.png`](session_hp_victus_full/plots/backlog_failure_D15_fifo_r1.png) |
| **3. Consumer delay 30ms gây nghẽn nghiêm trọng, P95 Latency tăng lên ~6.17 giây** | Quan sát thực nghiệm | `failure_D30_fifo_r1..r3` (so với F0 delay 0ms) | - Aggregate FPS giảm về $31.6 \pm 0.1$<br>- P95 Latency tăng lên **$6,165.38 \pm 16.77\text{ ms}$**<br>- Explicit Drop (reject tại nguồn): $78.88 \pm 0.04\%$<br>- Backlog cuối: **191 frames** | - [`summary.csv`](session_hp_victus_full/summary.csv)<br>- Đồ thị [`backlog_failure_D30_fifo_r1.png`](session_hp_victus_full/plots/backlog_failure_D30_fifo_r1.png) |
| **4. Chính sách Latest ghìm P95 Latency xuống < 70ms, đổi lại tăng tỷ lệ drop khung hình cũ** | Quan sát thực nghiệm (Trade-off) | So sánh F1 vs I1 và F2 vs I2 (`failure_D15_latest` & `failure_D30_latest`) | - Ở delay 15ms: P95 Latency từ $3175\text{ ms}$ giảm xuống **$53.00 \pm 0.10\text{ ms}$** (giảm 60 lần), Drop tăng từ $62.5\%$ lên $66.7\%$<br>- Ở delay 30ms: P95 Latency từ $6165\text{ ms}$ giảm xuống **$68.13 \pm 0.08\text{ ms}$** (giảm 90 lần), Drop tăng từ $78.9\%$ lên $82.6\%$<br>- Backlog cuối giảm từ 191 xuống còn **6 - 8 frames** | - Đồ thị đối chứng [`failure_policy_tradeoff.png`](session_hp_victus_full/plots/failure_policy_tradeoff.png)<br>- Đồ thị [`backlog_failure_D15_latest_r1.png`](session_hp_victus_full/plots/backlog_failure_D15_latest_r1.png) |
| **5. Băng thông ứng dụng 6.6 Gbps không đồng nghĩa bus USB đã nghẽn** | Phân biệt ranh giới lý thuyết | Toàn bộ ma trận P2 | Băng thông tính toán ở RAM ứng dụng; benchmark chưa đo cáp USB hay UVC driver vật lý | [`docs/limitations.md`](../docs/limitations.md) |
| **6. Shared Memory trên Windows bảo toàn 100% khung hình không mất mát** | Kiểm chứng cơ chế QA | 54/54 runs | Tất cả 54 runs đều đạt `"status": "ok"` và `"accounting_ok": true` cho mọi camera | Từng file `per_camera.csv` trong 54 thư mục con |

---

## 2. Bảng Tóm Tắt Số Liệu 6 Cấu Hình Failure & Policy (P2, N=6, 30 FPS, n=3)

| Ký hiệu | Policy | Delay/frame | Achieved FPS/cam | Aggregate FPS | P95 Latency (ms) | Explicit Drop (%) | Tồn đọng (Backlog) | CPU Norm (%) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| **F0** | FIFO | 0 ms | $30.00 \pm 0.00$ | $180.00 \pm 0.00$ | $7.03 \pm 1.37$ | $0.00 \pm 0.00$ | 0 | $3.54 \pm 0.77$ |
| **I0** | Latest | 0 ms | $29.97 \pm 0.06$ | $179.87 \pm 0.23$ | $8.13 \pm 3.73$ | $0.08 \pm 0.14$ | 0 | $3.72 \pm 0.60$ |
| **F1** | FIFO | 15 ms | $10.18 \pm 0.04$ | $61.10 \pm 0.26$ | **$3,175.09 \pm 42.64$** | $62.52 \pm 0.15$ | **191** | $1.19 \pm 0.09$ |
| **I1** | Latest | 15 ms | $9.83 \pm 0.03$ | $59.67 \pm 0.25$ | **$53.00 \pm 0.10$** | $66.74 \pm 0.12$ | **6** | $3.41 \pm 0.96$ |
| **F2** | FIFO | 30 ms | $5.24 \pm 0.02$ | $31.60 \pm 0.10$ | **$6,165.38 \pm 16.77$** | $78.88 \pm 0.04$ | **191** | $0.92 \pm 0.37$ |
| **I2** | Latest | 30 ms | $5.14 \pm 0.02$ | $31.07 \pm 0.12$ | **$68.13 \pm 0.08$** | $82.60 \pm 0.11$ | **8** | $3.42 \pm 0.84$ |
