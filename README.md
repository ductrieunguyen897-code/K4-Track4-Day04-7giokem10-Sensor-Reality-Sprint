# K4-Track4-Day04 — Đề tài T7: Multi-Camera Bandwidth Profiling

Dự án đo lường và đánh giá hiệu năng băng thông (Bandwidth Profiling) của hệ thống đa camera (Multi-Camera RGB-D) sử dụng dữ liệu tổng hợp (Synthetic Data), mô phỏng tải thực tế của các dòng cảm biến Intel RealSense (D435/D455) trên nền tảng Windows 11.

---

## 1. Thông tin chung
- **Đề tài:** T7 — Multi-camera bandwidth profiling bằng dữ liệu RGB-D tổng hợp
- **Môi trường đo lường chuẩn:** Laptop HP Victus 16-e0xxx (AMD Ryzen 7 5800H, 8GB RAM, Windows 11 Home Single Language)
- **Kiến trúc hệ thống:** Producer-Consumer đa tiến trình (`multiprocessing` chế độ `spawn` Windows) kết hợp Bộ nhớ chia sẻ (`SharedMemory` zero-copy) và Hàng đợi IPC (`multiprocessing.Queue`).
- **Upstream Repository:** [mirzafahad/realsense-multicam](https://github.com/mirzafahad/realsense-multicam) (Commit `ee144efd09bf534d8dc1b5f718fce7a4b89686a7`).
- **Ranh giới nghiên cứu:** Benchmark pipeline phần mềm với dữ liệu RGB-D tổng hợp; chưa đo camera RealSense vật lý hoặc bus USB vật lý.

---

## 2. Phân công vai trò & Trách nhiệm nhóm (Team 5 người)

Dự án được tổ chức phân rã độc lập theo tài liệu [Thu_tu_trien_khai_va_phoi_hop_Team5.md](file:///C:/Users/DMX/Desktop/VIN/LAB/PHASE%202/K4-Track4-Day04-10-7-Sensor-Reality-Sprint/Thu_tu_trien_khai_va_phoi_hop_Team5.md) và [TEAMMATES.md](file:///C:/Users/DMX/Desktop/VIN/LAB/PHASE%202/K4-Track4-Day04-10-7-Sensor-Reality-Sprint/TEAMMATES.md):

| Thành viên | Vai trò | Nhiệm vụ chính | Sản phẩm sở hữu |
|---|---|---|---|
| **TV1 — Bùi Văn Quang (MSV: 2A202602688)** | **Tích hợp & Kiến trúc** | Xây dựng repo, thiết lập môi trường Windows 11, chuẩn hóa `specs/contract_spec.md`, kiểm tra tích hợp, hoàn thiện README. | `specs/contract_spec.md`, `scripts/check_env.py`, `scripts/smoke_test.py`, `reports/TV1_2A202602688.md` |
| **TV2 — Nguyễn Đức Triệu (MSV: 2A202602978)** | **Nguồn dữ liệu & Bộ nhớ** | Hàm `producer()`, mô hình hóa RGB-D (5 bytes/pixel), pacing chống phát dồn, quản lý slot bộ nhớ chia sẻ (32 slots) và unit tests. | `benchmark/bench.py` (producer), `docs/H2_data_contract_and_memory_ownership.md`, `tests/test_producer_and_memory.py`, `reports/TV2_2A202602978.md` |
| **TV3 — Nguyễn Văn Thân (MSV: 2A202602859)** | **Metric & Đo lường** | Consumer, bộ đếm frame accounting, công thức đo latency P95/queue wait/copy, telemetry logging và script đồ thị `plot.py`. | `plots/plot.py`, `benchmark/plot.py`, `docs/methodology.md`, `reports/TV3_2A202602859.md`, `results/session_tv3_pilot_02/` |
| **TV4 — Bùi Việt Anh (MSV: 2A202602611)** | **Nghiên cứu & Giao thức** | Phân tích cơ sở lý thuyết băng thông raw vs bottleneck bus, ma trận kiểm thử (Test Matrix), phân tích failure và giới hạn kết luận. | `docs/benchmark_plan.md`, `docs/limitations.md`, `docs/references.md`, `reports/TV4_2A202602611.md` |
| **TV5 — [QA & Experiment Lead]** | **QA & Vận hành Thí nghiệm** | Lập checklist QA, phát triển kịch bản runner tự động (`benchmark/suite.py`), vận hành đo đạc trên laptop HP Victus 16, thu thập evidence index. | `benchmark/suite.py`, `docs/QA.md`, `docs/environment.txt`, `reports/TV5_MSV.md`, `slides/pitch.md` |

---

## 3. Cấu trúc thư mục Repo

```text
K4-Track4-Day04-10-7-Sensor-Reality-Sprint/
├── .gitignore                      # Cấu hình bỏ qua cache, file tạm, lưu giữ evidence
├── requirements.txt                # Thư viện phụ thuộc cho scripts kiểm tra
├── requirements-benchmark.txt      # Thư viện phụ thuộc chuẩn cho benchmark suite
├── requirements-benchmark-lock.txt # Lock phiên bản pip freeze
├── README.md                       # Tài liệu tổng thể dự án
├── TEAMMATES.md                    # Danh sách chi tiết 5 thành viên nhóm
├── UPSTREAM.md                     # Tài liệu đối chiếu upstream repo
├── Ke_hoach_T7_MultiCamera_Team5_Windows11.md # Kế hoạch chi tiết của giảng viên
├── Thu_tu_trien_khai_va_phoi_hop_Team5.md     # Quy trình phối hợp tác chiến 5 người
├── bench.py                        # Profiler tích hợp dạng script đơn (TV1/TV2/TV3)
├── benchmark/                      # Gói benchmark dạng module chuẩn hóa (TV2/TV3/TV5)
│   ├── __init__.py
│   ├── bench.py                    # Core benchmark pipeline (Shared Memory + Queue)
│   ├── suite.py                    # Runner tự động 54 runs (Matrix + Failure)
│   └── plot.py                     # Script tổng hợp kết quả CSV và vẽ đồ thị
├── specs/
│   └── contract_spec.md            # Đặc tả kỹ thuật: RGB-D, Metadata, CSV Schema (TV1)
├── scripts/
│   ├── check_env.py                # Script kiểm tra phần cứng & môi trường (TV1)
│   └── smoke_test.py               # Script smoke test tích hợp nhanh (TV1)
├── tests/
│   └── test_producer_and_memory.py # Unit tests kiểm tra producer & shared memory (TV2)
├── plots/
│   └── plot.py                     # Script vẽ đồ thị của TV3
├── docs/                           # Bộ tài liệu kỹ thuật & phương pháp
│   ├── environment.txt             # Manifest phần cứng máy HP Victus 16 (TV5)
│   ├── QA.md                       # Quy trình QA và tiêu chuẩn run hợp lệ (TV5)
│   ├── benchmark_plan.md           # Kế hoạch thí nghiệm & ma trận 54 runs (TV4)
│   ├── methodology.md              # Phương pháp luận và công thức metric (TV3)
│   ├── limitations.md              # Ranh giới kết luận và giới hạn phần cứng (TV4)
│   ├── references.md               # Tài liệu tham khảo và ghi chú đọc (TV4)
│   ├── decision.md                 # Biên bản ra quyết định kỹ thuật (TV4)
│   ├── H2_data_contract_and_memory_ownership.md # Tài liệu bàn giao H2 (TV2)
│   └── TV2_literature_notes.md     # Ghi chú tài liệu của TV2
├── reports/                        # 5 Báo cáo cá nhân của 5 thành viên
│   ├── TV1_2A202602688.md          # Báo cáo cá nhân TV1 (Bùi Văn Quang)
│   ├── Bao_cao_TV1_Tich_hop.md     # Báo cáo tích hợp TV1
│   ├── TV2_2A202602978.md          # Báo cáo cá nhân TV2 (Nguyễn Đức Triệu)
│   ├── TV3_2A202602859.md          # Báo cáo cá nhân TV3 (Nguyễn Văn Thân)
│   ├── TV4_2A202602611.md          # Báo cáo cá nhân TV4 (Bùi Việt Anh)
│   └── TV5_MSV.md                  # Báo cáo cá nhân TV5 (QA Lead)
├── slides/
│   └── pitch.md                    # Dàn ý 5 slide thuyết trình 4 phút
└── results/                        # Dữ liệu đo đạc thực nghiệm và đồ thị
    ├── EVIDENCE_INDEX.md           # Chỉ mục liên kết phát biểu - số đo (TV5)
    ├── smoke_test_01/              # Kết quả Smoke test 1 camera
    ├── smoke_test_failure_01/      # Kết quả Smoke test có delay
    └── session_tv3_pilot_02/       # Kết quả đo pilot đợt 2 của TV3
```

---

## 4. Hướng dẫn thiết lập môi trường (Windows 11)

### Bước 1: Mở PowerShell và kiểm tra phiên bản Python
```powershell
py -3.11 --version
```

### Bước 2: Tạo môi trường ảo và cài đặt thư viện
```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -r requirements-benchmark.txt
```

### Bước 3: Chạy script kiểm tra tương thích hệ thống
```powershell
.\.venv\Scripts\python.exe scripts/check_env.py
```

### Bước 4: Chạy Unit Test kiểm thử bộ nhớ & Producer
```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

---

## 5. Hướng dẫn chạy Benchmark

### 5.1. Chạy Smoke Test kiểm tra đường ống (10 giây)
```powershell
.\.venv\Scripts\python.exe -m benchmark.bench --cameras 1 --duration 10 --out results/smoke_test_01
Get-Content results/smoke_test_01/summary.json
```

### 5.2. Chạy Full Suite tự động (36 Matrix + 18 Failure = 54 runs)
```powershell
.\.venv\Scripts\python.exe -m benchmark.suite --set all --root results/session_full --duration 30 --repeats 3
```

### 5.3. Xuất bảng tổng hợp và vẽ đồ thị
```powershell
.\.venv\Scripts\python.exe -m benchmark.plot --root results/session_full
```

---

## 6. Tiêu chí Đánh giá & Ranh giới Kết luận
- **Tính bảo toàn khung hình (Frame Accounting):** Mọi run phải đảm bảo 100% khớp các bộ đếm `scheduled = attempted + schedule_missed`, `attempted = enqueued + rejected`, `enqueued = completed + stale + late_completion + shutdown_backlog`.
- **Ranh giới:** Đây là benchmark phần mềm trên máy tính HP Victus 16; băng thông được tính toán ở tầng ứng dụng, không đại diện cho giới hạn phần cứng bus USB 3.0 khi chưa gắn camera vật lý.
