# Dàn Ý Slide Pitch Đề Tài T7 (4 Phút — 5 Slide)

**Đề tài:** Synthetic RGB-D Multi-camera Pipeline Profiling on Windows 11  
**Nhóm:** Nhóm 5 | **Thiết bị:** Laptop HP Victus 16-e0xxx (Windows 11)  
**Dữ liệu thực nghiệm:** 54 runs n=3 lặp độc lập tại `results/session_hp_victus_full/`  

---

## Slide 1: Problem & Scope (0:00 – 0:35) — TV1 (Bùi Văn Quang)
- **Bối cảnh bài toán:** Robot đa camera RGB-D cần tiếp nhận dữ liệu thời gian thực cho điều hướng và nhận thức. Khi tăng số camera hoặc độ phân giải, pipeline phần mềm có nguy cơ bị quá tải hàng đợi ngay cả trước khi chạy mô hình AI.
- **Ranh giới thực nghiệm (Scope Boundary):**
  - Thực nghiệm đo lường pipeline phần mềm đa luồng trên Windows 11 với dữ liệu RGB-D tổng hợp (synthetic).
  - Băng thông là raw application payload; chưa đo lường camera RealSense vật lý hay băng thông dây cáp USB.
- **Bằng chứng:** Sơ đồ phạm vi và manifest cấu hình máy HP Victus 16 trong `docs/environment.txt`.

---

## Slide 2: Method & Architecture (0:35 – 1:20) — TV2 (Nguyễn Đức Triệu)
- **Kiến trúc Pipeline:**
  - Mỗi virtual camera là một process độc lập (`spawn` mode trên Windows 11).
  - Dữ liệu thô RGB8 + depth uint16 (5 bytes/pixel) copy vào Shared Memory pool (32 slots/camera, khống chế cứng 884.7 MB) do process cha quản lý.
  - Metadata gọn truyền qua multiprocessing Queue.
  - Thu hồi slot tức thì sau khi consumer xử lý hoặc khi frame bị drop.
- **Đồng hồ & Accounting:** Đồng bộ đồng hồ host bằng `time.perf_counter()`. Cơ chế bảo toàn khung hình đảm bảo 100% 54/54 runs đạt `accounting_ok: true`.
- **Bằng chứng:** Sơ đồ kiến trúc pipeline và 5 unit tests pass tại `tests/test_producer_and_memory.py`.

---

## Slide 3: Benchmark & Matrix Results (1:20 – 2:20) — TV3 (Nguyễn Văn Thân)
- **Thiết kế ma trận:** 12 cấu hình (P0: 424x240@5fps, P1: 640x480@30fps, P2: 1280x720@30fps; $N \in \{1, 2, 4, 6\}$) $\times 3$ lần lặp ngẫu nhiên = 36 runs.
- **Kết quả đo lường chính trên HP Victus:**
  - Cả 12 cấu hình đều đạt **100% Target FPS** (Drop = 0%).
  - P2 N=6 (6 camera HD @ 30 FPS) đạt **180.0 FPS** tổng tải, thông lượng hoàn thành **827.4 MB/s** (~6.6 Gbps raw payload), độ trễ P95 chỉ **6.95 ms**.
  - Tải CPU chuẩn hóa toàn bộ pipeline chỉ chiếm **3.88%** CPU hệ thống.
- **Bằng chứng:** Đồ thị `plots/matrix_min_camera_fps.png` và `plots/matrix_latency_p95_ms.png`.

---

## Slide 4: Failure Case Analysis (2:20 – 3:15) — TV5 (QA Lead)
- **Kịch bản gây lỗi đối chứng:** P2, 6 cameras, 30 FPS (tổng tải 180 FPS); bơm delay $15\text{ ms}$ và $30\text{ ms}$ vào consumer.
- **Hiện tượng quan sát được:**
  - Với chính sách FIFO: Consumer quá tải, hàng đợi backlog tăng liên tục theo thời gian, độ trễ P95 tăng vọt từ **7.03 ms** (delay 0) lên **3,175.1 ms** (delay 15ms) và **6,165.4 ms** (delay 30ms).
  - Số lượng frame tồn đọng cuối phiên đo lên tới **191 frames**.
- **Bằng chứng:** Đồ thị diễn tiến hàng đợi `plots/backlog_failure_D15_fifo_r1.png` và bảng đối chứng F0/F1/F2 trong `EVIDENCE_INDEX.md`.

---

## Slide 5: Engineering Decision & Future Work (3:15 – 4:00) — TV4 (Bùi Việt Anh)
- **Quyết định kỹ thuật & Trade-off:**
  - Với tác vụ ưu tiên độ tươi mới (Real-time navigation): Bắt buộc dùng chính sách **Latest**, ghìm P95 Latency từ **3,175 ms xuống 53.0 ms** (giảm 60 lần) ở delay 15ms và từ **6,165 ms xuống 68.1 ms** (giảm 90 lần) ở delay 30ms. Đánh đổi chấp nhận drop ~66.7% - 82.6% khung hình cũ.
  - Với tác vụ ghi dữ liệu (Logging/Recording): Giữ **FIFO** nhưng phải hạ tải nguồn về P1 ($640 \times 480$) hoặc 15 FPS.
- **Phác thảo kiến trúc 4–8 camera:** Đề xuất 4 luồng $640\times480$@30fps (~1.47 Gbps, P95 latency 2.30 ms) cho cấu hình robot cân bằng.
- **Phép kiểm chứng tiếp theo:** Thử nghiệm với camera RealSense vật lý trên hub USB controller độc lập.
- **Bằng chứng:** Đồ thị `plots/failure_policy_tradeoff.png` và tài liệu `docs/decision.md`.
