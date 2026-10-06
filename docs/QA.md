# Quality Assurance & Experiment Execution Protocol (QA) — TV5

**Người phụ trách:** TV5 — Nguyễn Văn Diện (MSV: 2A202602615) — QA & Experiment Lead  
**Thiết bị thực thi:** Laptop HP Victus 16, Windows 11  

---

## 1. Tiêu Chuẩn Đánh Giá Run Hợp Lệ (Validity Criteria)

Một phiên chạy (run) chỉ được coi là hợp lệ (`status == "ok"`) khi thỏa mãn toàn bộ các điều kiện sau:
1. `summary.json` có trường `"status": "ok"` và `"failure": null`.
2. Mọi camera trong `per_camera` đều có `"accounting_ok": true`, tuân thủ đúng 3 phương trình bảo toàn khung hình:
   - $\text{scheduled} = \text{attempted} + \text{schedule\_missed}$
   - $\text{attempted} = \text{enqueued} + \text{rejected}$
   - $\text{enqueued} = \text{completed} + \text{stale} + \text{late\_completion} + \text{shutdown\_backlog}$
3. Không có tiến trình worker nào bị crash, thoát đột ngột (`exitcode != 0`), hoặc cần cưỡng chế dừng (`forced termination`).
4. Khối Shared Memory được giải phóng hoàn toàn sau khi kết thúc run.
5. Số lượng tiến trình được giám sát tài nguyên (`resource_monitor_processes`) khớp với kỳ vọng ($N + 1$).

Nếu bất kỳ điều kiện nào bị vi phạm: Đánh dấu run đó là `invalid`, ghi lại log lỗi, điều tra nguyên nhân và tạo Run ID mới để chạy lại. Tuyệt đối không xóa đè lên dữ liệu cũ.

---

## 2. Quy Trình Chạy Thử Nghiệm

### Bước 1: Smoke Test nhanh (Sanity Check)
Kiểm tra chức năng toàn vẹn của mã nguồn trên Windows:
```powershell
.\.venv\Scripts\python.exe -m benchmark.bench --cameras 1 --duration 10 --out results/smoke_test_01
```
Kiểm tra `results/smoke_test_01/summary.json` xem status có `ok` và `accounting_ok` có `true` hay không.

### Bước 2: Chạy Thử Failure Test Nhỏ
Kiểm tra cơ chế dọn dẹp hàng đợi và tính toán drop/backlog khi có delay:
```powershell
.\.venv\Scripts\python.exe -m benchmark.bench --cameras 2 --fps 30 --duration 10 --delay-ms 15 --policy latest --out results/smoke_failure_01
```

### Bước 3: Chạy Suite Toàn Diện (Full Matrix + Failure Suite)
- Tắt tất cả các ứng dụng nền nặng (trình duyệt, IDE nặng, game, v.v.).
- Đảm bảo máy cắm sạc nguồn AC và thiết lập chế độ tản nhiệt phù hợp.
- Thực hiện chạy toàn bộ 54 runs:
```powershell
.\.venv\Scripts\python.exe -m benchmark.suite --set all --root results/session_full --duration 30 --repeats 3
```

### Bước 4: Tạo Đồ Thị & Báo Cáo Thống Kê
Sau khi suite hoàn thành, chạy script tạo bảng và biểu đồ:
```powershell
.\.venv\Scripts\python.exe -m benchmark.plot --root results/session_full
```

---

## 3. Nhật Ký Giám Sát Tiến Trình (Run Log Checklist)

- [ ] Xác nhận sạc pin đã cắm, Power mode = Best Performance.
- [ ] Kiểm tra Task Manager đảm bảo không còn tiến trình Python mồ côi từ phiên trước.
- [ ] Ghi lại Git commit HEAD trước khi chạy suite.
- [ ] Giám sát file `order.json` và log từng run trong suốt quá trình chạy.
- [ ] Sau khi chạy xong, xác minh tất cả 54 thư mục con đều có `summary.json`.
- [ ] Kiểm tra thư mục `plots/` đã sinh đủ các đồ thị PNG:
  - `matrix_min_camera_fps.png`
  - `matrix_latency_p95_ms.png`
  - `matrix_explicit_drop_pct.png`
  - `failure_policy_tradeoff.png`
  - Các đồ thị `backlog_failure_*.png`
