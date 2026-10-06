# Dàn Ý Slide Pitch Đề Tài T7 (4 Phút — 5 Slide)

**Đề tài:** Synthetic RGB-D Multi-camera Pipeline Profiling on Windows 11  
**Nhóm:** Nhóm 5 — [Tên Nhóm]  
**Thiết bị:** Laptop HP Victus 16-e0xxx (Windows 11)  

---

## Slide 1: Problem & Scope (0:00 – 0:35) — TV1 phụ trách
- **Bối cảnh bài toán:** Robot đa camera RGB-D cần tiếp nhận dữ liệu thời gian thực cho điều hướng và nhận thức. Khi tăng số camera hoặc độ phân giải, pipeline phần mềm có nguy cơ bị quá tải hàng đợi ngay cả trước khi chạy mô hình AI.
- **Ranh giới thực nghiệm (Scope Boundary):**
  - Thực nghiệm đo lường pipeline phần mềm đa luồng trên Windows 11 với dữ liệu RGB-D tổng hợp (synthetic).
  - Chưa đo lường camera RealSense vật lý hay băng thông vật lý trên đường truyền USB.
- **Bằng chứng:** Sơ đồ phạm vi và manifest cấu hình máy HP Victus 16 trong `docs/environment.txt`.

---

## Slide 2: Method & Architecture (0:35 – 1:20) — TV2 phụ trách
- **Kiến trúc Pipeline:**
  - Mỗi virtual camera là một process độc lập (`spawn` mode).
  - Dữ liệu thô RGB8 + depth uint16 (5 bytes/pixel) copy vào Shared Memory pool (32 slots/camera) do process cha quản lý.
  - Metadata gọn truyền qua multiprocessing Queue.
  - Thu hồi slot tức thì sau khi consumer xử lý hoặc khi frame bị drop.
- **Đồng hồ & Accounting:** Đồng bộ đồng hồ host bằng `time.perf_counter()`. Cơ chế bảo toàn khung hình đảm bảo không thất thoát frame.
- **Bằng chứng:** Sơ đồ kiến trúc pipeline và commit mã nguồn gốc `ee144efd`.

---

## Slide 3: Benchmark & Matrix Results (1:20 – 2:20) — TV3 phụ trách
- **Thiết kế ma trận:** 12 cấu hình (P0: 424x240@5fps, P1: 640x480@30fps, P2: 1280x720@30fps; $N \in \{1, 2, 4, 6\}$) $\times 3$ lần lặp ngẫu nhiên = 36 runs.
- **Kết quả đo lường chính:**
  - So sánh Target FPS và Achieved FPS (Aggregate vs Min-camera FPS).
  - Độ trễ P95 Latency qua từng mức tải.
  - Mức sử dụng tài nguyên CPU và bộ nhớ Working Set (RSS Peak).
- **Bằng chứng:** Đồ thị `plots/matrix_min_camera_fps.png` và `plots/matrix_latency_p95_ms.png`.

---

## Slide 4: Failure Case Analysis (2:20 – 3:15) — TV5 phụ trách
- **Kịch bản gây lỗi đối chứng:** P2, 6 cameras, 30 FPS (tổng tải 180 FPS); bơm delay $15\text{ ms}$ và $30\text{ ms}$ vào consumer.
- **Hiện tượng quan sát được:**
  - Với chính sách FIFO: Consumer quá tải, hàng đợi backlog tăng liên tục theo thời gian, độ trễ P95 tăng vọt từ [x] ms lên [y] ms.
  - Số lượng frame tồn đọng cuối phiên tăng cao.
- **Bằng chứng:** Đồ thị diễn tiến hàng đợi `plots/backlog_failure_D15_fifo_r1.png` và bảng đối chứng F0/F1/F2.

---

## Slide 5: Engineering Decision & Future Work (3:15 – 4:00) — TV4 phụ trách
- **Quyết định kỹ thuật & Trade-off:**
  - Với tác vụ ưu tiên độ mới (Real-time navigation): Khuyến nghị chính sách **Latest**, ghìm P95 Latency ở mức thấp để tránh robot phản ứng trên khung hình cũ, chấp nhận đánh đổi drop các frame cũ.
  - Với tác vụ ghi nhận dữ liệu (Logging/Recording): Giữ **FIFO** nhưng phải hạ độ phân giải hoặc FPS tại nguồn.
- **Phác thảo kiến trúc 4–8 camera:** Đề xuất cấu hình 4 luồng $640\times480$@30fps (~1.47 Gbps) hoặc 8 luồng $424\times240$@30fps (~976 Mbps).
- **Phép kiểm chứng tiếp theo:** Thử nghiệm với camera RealSense vật lý trên hub USB controller độc lập.
- **Bằng chứng:** Đồ thị `plots/failure_policy_tradeoff.png` và tài liệu `docs/limitations.md`.
