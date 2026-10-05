# K4-Track4-Day04 — Đề tài T7: Multi-Camera Bandwidth Profiling

Dự án đo lường và đánh giá hiệu năng băng thông (Bandwidth Profiling) của hệ thống đa camera (Multi-Camera RGB-D) sử dụng dữ liệu tổng hợp (Synthetic Data), mô phỏng tải thực tế của các dòng cảm biến Intel RealSense (D435/D455) trên nền tảng Windows 11.

---

## 1. Thông tin chung
- **Đề tài:** T7 — Multi-camera bandwidth profiling bằng dữ liệu RGB-D tổng hợp
- **Môi trường đo lường chuẩn:** Laptop HP Victus 16, Windows 11, chưa có camera vật lý RealSense
- **Kiến trúc hệ thống:** Producer-Consumer đa tiến trình (Multiprocessing) kết hợp Bộ nhớ chia sẻ (Shared Memory zero-copy) và Hàng đợi IPC (IPC Queue baseline).

---

## 2. Phân công vai trò & Trách nhiệm nhóm (Team 5 người)

Dự án được tổ chức phân rã độc lập theo tài liệu [Thu_tu_trien_khai_va_phoi_hop_Team5.md](file:///d:/Phase2-AITC/K4-Track4-Day04-10-7-Sensor-Reality-Sprint/Thu_tu_trien_khai_va_phoi_hop_Team5.md):

| Thành viên | Vai trò | Nhiệm vụ chính | Phạm vi code / tài liệu |
|---|---|---|---|
| **TV1 — Bùi Văn Quang (MSV: 2A202602688)** *(Đã thực hiện)* | **Tích hợp & Kiến trúc** | Xây dựng repo, thiết lập môi trường Windows 11, xây dựng bộ khung `bench.py`, chuẩn hóa `specs/contract_spec.md`, scripts kiểm tra môi trường và hoàn thiện tài liệu hướng dẫn README. | `.gitignore`, `requirements.txt`, `scripts/check_env.py`, `specs/contract_spec.md`, `bench.py` (Khung chung), `README.md` |
| **TV2** *(Giữ nguyên)* | **Nguồn dữ liệu & Bộ nhớ** | Hoàn thiện hàm `camera_producer()`, mô hình hóa độ nhiễu RGB-D, điều khiển pacing (FPS), quản lý vòng đời slot bộ nhớ chia sẻ (ring buffer) và cơ chế xử lý overload/latest frame. | `bench.py` (Section 2: Producer & Memory Slots) |
| **TV3** *(Giữ nguyên)* | **Metric & Đo lường** | Hoàn thiện hàm `consumer_logger()`, công thức đo latency p95/mean, frame drop rate, tính toán throughput thực tế và viết script trực quan hóa `plot.py`. | `bench.py` (Section 3: Consumer & Telemetry), `plot.py` |
| **TV4** *(Giữ nguyên)* | **Nghiên cứu & Giao thức** | Phân tích cơ sở lý thuyết băng thông raw vs bottleneck bus, thiết kế ma trận kiểm thử (Test Matrix), viết báo cáo phương pháp luận (Methodology) và giới hạn thực nghiệm. | `docs/methodology.md`, Báo cáo phân tích chuyên sâu |
| **TV5** *(Giữ nguyên)* | **QA & Chạy thí nghiệm** | Lập checklist kiểm thử, phát triển kịch bản tự động hóa runner (`scripts/run_experiments.py`), kiểm tra clone sạch, vận hành đo đạc chính thức trên laptop HP Victus và lưu vết evidence. | `scripts/runner.py`, `docs/checklist.md`, Dữ liệu đo `results/` |

---

## 3. Cấu trúc thư mục Repo

```text
K4-Track4-Day04-10-7-Sensor-Reality-Sprint/
├── .gitignore                      # Cấu hình bỏ qua cache, file tạm, output nặng
├── requirements.txt                # Danh sách thư viện phụ thuộc (Windows 11)
├── README.md                       # Hướng dẫn tổng thể dự án (TV1 - Bùi Văn Quang)
├── Thu_tu_trien_khai_va_phoi_hop_Team5.md  # Kế hoạch phối hợp tác chiến của nhóm
├── bench.py                        # Bộ khung benchmark tích hợp (Core Profiler)
├── specs/
│   └── contract_spec.md            # Đặc tả kỹ thuật: RGB-D, Metadata, CSV Schema
├── scripts/
│   ├── check_env.py                # Script kiểm tra phần cứng & môi trường (TV1 - Bùi Văn Quang)
│   └── runner.py                   # (Vùng của TV5: Tự động chạy test matrix)
├── plots/                          # (Vùng của TV3: Chứa script plot.py & hình biểu đồ)
│   └── .gitkeep
├── results/                        # (Vùng của TV5: Chứa CSV log viễn trắc và summary)
│   └── .gitkeep
└── docs/                           # (Vùng của TV4: Tài liệu lý thuyết, methodology)
```

---

## 4. Hướng dẫn thiết lập môi trường (Windows 11)

### Bước 1: Mở PowerShell và kiểm tra phiên bản Python
Yêu cầu Python $\ge 3.8$ (khuyến nghị Python 3.10 - 3.12):
```powershell
python --version
```

### Bước 2: Cài đặt các gói thư viện phụ thuộc
```powershell
pip install -r requirements.txt
```

### Bước 3: Chạy script kiểm tra tương thích hệ thống
```powershell
python scripts/check_env.py
```
Script sẽ kiểm tra dung lượng RAM khả dụng, số CPU Cores và khả năng cấp phát của module `multiprocessing.shared_memory` trên Windows.

---

## 5. Hướng dẫn chạy Benchmark

### 5.1. Chạy kiểm thử nhanh (Smoke Test)
Mô phỏng 2 camera RGB-D, 30 FPS trong 3 giây dùng cơ chế Shared Memory:
```powershell
python bench.py --cameras 2 --fps 30 --duration 3 --mode shm
```

### 5.2. Chạy so sánh Baseline (Queue vs Shared Memory)
- **Chế độ Hàng đợi bản sao (Baseline IPC Queue):**
  ```powershell
  python bench.py --cameras 4 --fps 30 --duration 5 --mode queue
  ```
- **Chế độ Bộ nhớ chia sẻ không copy (Zero-copy Shared Memory):**
  ```powershell
  python bench.py --cameras 4 --fps 30 --duration 5 --mode shm
  ```

### 5.3. Các tham số dòng lệnh tùy biến (`bench.py`)
- `--cameras`: Số lượng camera giả lập (1, 2, 4, 8). Mặc định: `2`.
- `--fps`: Tốc độ khung hình mục tiêu mỗi camera (ví dụ: 30 hoặc 60). Mặc định: `30`.
- `--duration`: Thời lượng chạy benchmark (giây). Mặc định: `5`.
- `--mode`: Phương thức truyền dữ liệu: `shm` (Shared Memory) hoặc `queue` (multiprocessing.Queue).
- `--width`, `--height`: Độ phân giải khung hình (Mặc định: 640x480).
- `--outdir`: Thư mục lưu kết quả viễn trắc (Mặc định: `results`).
- `--seed`: Seed tạo dữ liệu giả lập ngẫu nhiên đảm bảo tính lặp lại.

---

## 6. Định dạng Dữ liệu & Kết quả đầu ra

Mỗi lần chạy sẽ tự động tạo thư mục con theo quy tắc:
`results/run_YYYYMMDD_HHMMSS_<num_cam>cam_<fps>fps_<mode>/`

Gồm 2 tệp dữ liệu chính:
1. `config.json`: Toàn bộ thông số thiết lập của run.
2. `frames_telemetry.csv`: Dữ liệu viễn trắc theo từng frame (`timestamp`, `camera_id`, `frame_id`, `latency_ms`, `payload_bytes`).
3. `summary.json`: Tóm tắt tổng frame đạt được, throughput trung bình (MB/s) và đánh giá trạng thái `VALID` / `DEGRADED`.

Chi tiết giao ước định dạng vui lòng tham khảo [specs/contract_spec.md](file:///d:/Phase2-AITC/K4-Track4-Day04-10-7-Sensor-Reality-Sprint/specs/contract_spec.md).

---

## 7. Quy tắc phối hợp song song cho 4 thành viên còn lại

- **TV2 (Producer):** Chỉ chỉnh sửa hàm `generate_synthetic_rgbd` và `camera_producer` trong **SECTION 2** của `bench.py`. Đảm bảo tôn trọng cấu trúc `FrameMetadata` đã chốt.
- **TV3 (Metrics & Plot):** Tinh chỉnh logic trích xuất thống kê trong **SECTION 3** của `bench.py` và viết script vẽ đồ thị `plot.py` đọc từ `frames_telemetry.csv`.
- **TV4 (Protocol & Research):** Tham khảo thông số cấu hình và dung lượng payload trong `specs/contract_spec.md` để đối chiếu với tính toán lý thuyết bus USB 3.0 / PCIe.
- **TV5 (QA & Runner):** Dùng lệnh gọi CLI của `bench.py` để xây dựng runner tự động và đánh giá run hợp lệ theo tiêu chí tại Section 5 của `specs/contract_spec.md`.

