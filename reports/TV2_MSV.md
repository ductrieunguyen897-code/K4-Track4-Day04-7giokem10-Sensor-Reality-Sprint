# TV2 — Nguyễn Đức Triệu, 2A202602978

Nhóm: 10 > 7 | Vai trò: Source & Memory Lead (TV2) | Repo: `K4-Track4-Day04-TenNhom-Sensor-Reality-Sprint` | Code commit: `9d3c11b`  
Thiết bị: HP Victus 16, Windows 11; RGB-D tổng hợp, chưa có camera RealSense vật lý.

---

## Problem
Mô phỏng hệ thống đa camera RGB-D trên laptop mà không gây tràn RAM hay nghẽn IPC. Khi nhiều process camera cùng đẩy payload lớn (5 byte/pixel), việc cấp phát bộ nhớ động không kiểm soát hoặc gửi frame trực tiếp qua IPC Queue sẽ gây quá tải CPU, phình bộ đệm và tăng vọt độ trễ. Trách nhiệm của TV2 là chuẩn hóa dữ liệu, đảm bảo lập lịch cứng (pacing) và quản lý khối bộ nhớ dùng chung hữu hạn, không chồng lấn và không rò rỉ tài nguyên.

## Method
Kế thừa kiến trúc từ `realsense-multicam` [R1], thích ứng với Windows `spawn` [R3] và đặc tính cảm biến RGB-D [P1]:
- **Payload chuẩn:** RGB8 (`uint8`, 3 kênh) + Depth Z16 (`uint16`, 1 kênh) = **5 byte/pixel (40 bit/pixel)**. Mỗi camera khởi tạo ngẫu nhiên độc lập bằng `numpy.random.default_rng(seed + cam)`.
- **SharedMemory Pool hữu hạn:** Cấp phát một khối nhớ tĩnh duy nhất $\text{pool\_bytes} = \text{frame\_bytes} \times \text{cameras} \times \text{slots}$ với chốt chặn an toàn $< 1.5\text{ GB}$ RAM. Phân vùng slot độc lập tại địa chỉ: $(\text{cam} \times \text{slots} + \text{slot}) \times \text{frame\_bytes}$.
- **Hợp đồng Metadata & Slot (Handoff H2):** Producer lấy slot rảnh từ `frees[cam]`, copy template vào SharedMemory, rồi chỉ gửi tuple metadata 5 phần tử qua Queue: `(cam, seq, slot, t_capture, t_enqueue)`. Consumer xử lý xong bắt buộc phải trả lại slot. Producer không bao giờ ghi đè slot chưa trả.
- **Pacing chống phát dồn:** Lập lịch cứng theo mốc tuyệt đối $\text{deadline} = \text{start.value} + \text{seq} / \text{fps}$ qua `time.perf_counter()`. Nếu trễ lịch quá $1/\text{fps}$, tự động tăng `schedule_missed` và bỏ qua, không phát dồn (no catch-up burst).

## Benchmark
Kiểm thử chức năng và tính toàn vẹn trên môi trường thực thi:
- **Phương trình kế toán bảo toàn 100%:**
  - $\text{scheduled} = \text{attempted} + \text{schedule\_missed}$
  - $\text{attempted} = \text{enqueued} + \text{rejected}$
  - $\text{enqueued} = \text{completed} + \text{stale} + \text{late} + \text{shutdown\_backlog}$
- **Số liệu đo kiểm thử:**
  - *Smoke test (1 cam, 424×240 @ 5 FPS, 2.0s, 16 slots):* 10 scheduled, 10 completed, 0 drop, latency P95 = 1.32 ms, throughput = 2.54 MB/s, accounting OK.
  - *Unit test đa camera (2 cam, 160×120 @ 10 FPS, 1.0s, 4 slots):* 20 scheduled, 20 enqueued, 0 reject, accounting OK.
  - *Stress test cạn slot (1 cam, 0 slot rảnh, 1.0s):* 10 scheduled, 10 attempted, 0 enqueued, 10 rejected, accounting OK.

## Failure case
- **Hiện tượng cạn pool (Pool Exhaustion):** Khi consumer xử lý chậm (mô phỏng bằng tham số delay tăng), slot không kịp giải phóng về `frees[cam]`.
- **Cơ chế xử lý:** Producer timeout 2ms khi lấy slot, lập tức ghi nhận `rejected` và hủy frame ngay tại nguồn, loại trừ hoàn toàn nguy cơ deadlock và tràn RAM.
- **So sánh FIFO vs Latest:** Hàng đợi FIFO tích tụ frame cũ làm `queue_wait_p95` tăng vọt hàng trăm ms. Ngược lại, Latest rút cạn hàng đợi, giữ frame mới nhất và trả slot của frame cũ (`stale`), giữ độ trễ cực thấp (< 35 ms) với sự đánh đổi là tăng tỷ lệ frame bị drop.
- **Giới hạn đo lường:** Benchmark đo đường truyền bộ nhớ/IPC phần mềm; chưa đo băng thông USB 3.0 vật lý hay độ trễ phơi sáng quang học của cảm biến thật.

## Engineering decision
- **Cố định pool 32 slot/camera:** Khống chế cứng bộ nhớ RAM dưới 1.5 GB, bảo vệ hệ điều hành laptop không bị sập khi quá tải.
- **Bất biến thu hồi slot:** Mọi frame ở bất kỳ trạng thái nào (`completed`, `stale`, `late`, `shutdown`) đều phải trả lại slot về `frees[cam]`.
- **Khuyến nghị Latest Policy:** Đánh đổi tính toàn vẹn lịch sử frame để lấy độ tươi dữ liệu (freshness) và độ trễ thấp cho tác vụ robot thời gian thực.
- **Phép kiểm tra tiếp theo:** Đo topology USB Root Hub và kiểm tra format truyền dẫn YUYV khi có phần cứng RealSense thật.

---

**Đóng góp cá nhân:** Hiện thực hóa hàm `producer()` trong [`benchmark/bench.py`](file:///home/trieu/ai_in_action/track4_lab04/K4-Track4-Day04-10-7-Sensor-Reality-Sprint/benchmark/bench.py); soạn thảo bàn giao [`docs/H2_data_contract_and_memory_ownership.md`](file:///home/trieu/ai_in_action/track4_lab04/K4-Track4-Day04-10-7-Sensor-Reality-Sprint/docs/H2_data_contract_and_memory_ownership.md); xây dựng 5 bài unit test [`tests/test_producer_and_memory.py`](file:///home/trieu/ai_in_action/track4_lab04/K4-Track4-Day04-10-7-Sensor-Reality-Sprint/tests/test_producer_and_memory.py) đạt 100% PASS; tổng hợp ghi chú đọc tài liệu R1, R3, P1 tại [`docs/TV2_literature_notes.md`](file:///home/trieu/ai_in_action/track4_lab04/K4-Track4-Day04-10-7-Sensor-Reality-Sprint/docs/TV2_literature_notes.md).  
**Nguồn tài liệu:** [R1] `realsense-multicam` (commit `4993d0f`); [R3] Python 3.11 `multiprocessing.shared_memory`; [P1] Keselman et al. (2017), arXiv:1705.05548.
