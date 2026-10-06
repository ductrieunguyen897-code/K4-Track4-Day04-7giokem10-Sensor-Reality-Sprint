# Báo cáo Cá nhân T7 — [Họ và Tên TV5], MSV: [Điền MSV]

**Nhóm:** Nhóm 5 | **Vai trò:** TV5 — QA & Experiment Lead  
**Repository:** [K4-Track4-Day04-TenNhom-Sensor-Reality-Sprint](https://github.com/ductrieunguyen897-code/K4-Track4-Day04-10-7-Sensor-Reality-Sprint)  
**Code Commit:** [Điền commit hash git rev-parse HEAD]  
**Thiết bị thực nghiệm:** HP Victus 16-e0xxx, AMD Ryzen 7 5800H, 8GB RAM, Windows 11  
**Phạm vi:** Pipeline phần mềm RGB-D tổng hợp, không đo phần cứng camera RealSense hay bus USB.  

---

## 1. Problem
Trong các hệ thống robot sử dụng nhiều camera RGB-D, việc nhiều luồng dữ liệu đổ về đồng thời có thể gây quá tải cho bộ đệm hàng đợi và tiến trình xử lý trung tâm (consumer), dẫn đến độ trễ tăng vọt hoặc mất khung hình.  
Với tư cách là **QA & Experiment Lead**, vấn đề trọng tâm của tôi là:
- Thiết lập một quy trình thực nghiệm nghiêm ngặt, tự động hóa toàn bộ 54 lượt chạy (36 matrix + 18 failure) để đảm bảo tính tái lập (reproducibility).
- Phát hiện các bất thường trong quá trình chạy (deadlock, crash worker, memory leak, hoặc sai lệch frame accounting).
- Xác định chính xác ranh giới mà tại đó hệ thống chuyển từ trạng thái ổn định sang quá tải khi bị bơm delay nhân tạo ($15\text{ ms}$ và $30\text{ ms}$).

---

## 2. Method
- **Quy trình Runner & Tự động hóa:** Xây dựng script `benchmark/suite.py` thực hiện xáo trộn ngẫu nhiên thứ tự chạy (random block design) qua từng lần lặp (repetition) với seed cố định (`seed=42`) nhằm triệt tiêu các yếu tố nhiễu về nhiệt độ CPU (thermal throttling) và thời gian chạy.
- **Tiêu chuẩn kiểm thử hợp lệ (QA Guardrails):**
  - Giám sát tiến trình bằng cơ chế timeout (`timeout = duration + 90s`) để tránh treo máy.
  - Kiểm tra tính bảo toàn khung hình thông qua đẳng thức:  
    $\text{scheduled} = \text{attempted} + \text{schedule\_missed}$  
    $\text{attempted} = \text{enqueued} + \text{rejected}$  
    $\text{enqueued} = \text{completed} + \text{stale} + \text{late\_completion} + \text{shutdown\_backlog}$
- **Bảo toàn môi trường:** Mỗi lượt chạy xuất ra một thư mục độc lập gồm `config.json`, `summary.json`, `frames.csv`, `resources.csv`, `per_camera.csv` và file log console riêng biệt.

---

## 3. Benchmark
- **Kịch bản thực hiện:**
  - 12 cấu hình Matrix ($N \in \{1, 2, 4, 6\}$, độ phân giải P0, P1, P2) $\times 3$ lần lặp = 36 runs.
  - 6 cấu hình Failure (P2, $N=6$, delay $0, 15, 30\text{ ms}$, chính sách FIFO vs Latest) $\times 3$ lần lặp = 18 runs.
- **Bảng số liệu tổng hợp chính (Sau khi chạy thực nghiệm):**

| Cấu hình / Điều kiện | Achieved FPS/cam | Aggregate FPS | P95 Latency (ms) | Explicit Drop (%) | Deadline Miss (%) | Backlog cuối | CPU Norm (%) |
|---|---:|---:|---:|---:|---:|---:|---:|
| F0: P2, N=6, Delay 0ms, FIFO | [Điền số] | [Điền số] | [Điền số] | [Điền số] | [Điền số] | [Điền số] | [Điền số] |
| F1: P2, N=6, Delay 15ms, FIFO | [Điền số] | [Điền số] | [Điền số] | [Điền số] | [Điền số] | [Điền số] | [Điền số] |
| F2: P2, N=6, Delay 30ms, FIFO | [Điền số] | [Điền số] | [Điền số] | [Điền số] | [Điền số] | [Điền số] | [Điền số] |
| I1: P2, N=6, Delay 15ms, Latest | [Điền số] | [Điền số] | [Điền số] | [Điền số] | [Điền số] | [Điền số] | [Điền số] |
| I2: P2, N=6, Delay 30ms, Latest | [Điền số] | [Điền số] | [Điền số] | [Điền số] | [Điền số] | [Điền số] | [Điền số] |

*(Đính kèm link đến file `summary.csv`, `aggregate.csv` và các biểu đồ trong thư mục `results/`)*

---

## 4. Failure Case
- **Hiện tượng quan sát được:**
  - Khi đưa delay $15\text{ ms}$ vào consumer trên 6 luồng P2 (tổng tải lý thuyết 180 FPS), consumer chỉ có thể xử lý tối đa $\approx 66.6\text{ FPS}$.
  - Với chính sách FIFO (F1), hàng đợi nhanh chóng bị lấp đầy, thời gian chờ (`queue_wait_p95`) tăng đột biến, kéo theo P95 Latency tăng từ [x] ms lên [y] ms.
  - Đến cuối phiên đo, số lượng frame bị tồn đọng (`shutdown_backlog`) lên tới hàng trăm frameset.
- **Phân biệt ranh giới:**
  - *Quan sát thực tế:* Hiện tượng nghẽn xảy ra do năng lực xử lý của consumer bị giới hạn bởi delay nhân tạo, không phải do Shared Memory hay CPU của laptop bị quá tải.
  - *Giả thuyết/Hạn chế:* Trên camera thật, sự chậm trễ này sẽ khiến robot ra quyết định dựa trên các khung hình quá khứ, tiềm ẩn nguy cơ va chạm.

---

## 5. Engineering Decision
- **Quyết định đề xuất:**
  - Đối với các tác vụ điều khiển robot thời gian thực (Real-time Navigation/Obstacle Avoidance): Chuyển sang chính sách **Latest per-camera** khi phát hiện queue backlog vượt quá ngưỡng cho phép (ví dụ $> 2$ frames). Quyết định này giúp ghìm P95 Latency ở mức thấp (< [z] ms), chấp nhận trade-off đánh đổi tỷ lệ drop khung hình cũ.
  - Đối với tác vụ ghi dữ liệu phục vụ huấn luyện (Data Logging): Giữ chính sách FIFO nhưng bắt buộc phải giảm độ phân giải xuống P1 ($640 \times 480$) hoặc giảm FPS của nguồn về 15 FPS để khớp với throughput của consumer.
- **Phép kiểm chứng phần cứng tiếp theo:** Mượn hub USB chuẩn công nghiệp và camera Intel RealSense D435/D405 vật lý để đo lường băng thông thực tế trên bus USB và kiểm tra hiện tượng drop gói ở tầng driver.

---
**Đóng góp cá nhân:**
- Chủ trì thiết lập và kiểm thử mã nguồn `benchmark/suite.py`.
- Thực hiện toàn bộ quy trình QA, chạy Smoke test và điều khiển máy HP Victus 16 chạy hoàn chỉnh bộ 54 runs.
- Giám sát tính bảo toàn dữ liệu (frame accounting) và biên soạn tài liệu `docs/QA.md`.
