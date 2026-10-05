# Đặc tả Giao thức & Định dạng Kỹ thuật (Contract Specification) — Team 5

**Đề tài:** T7 — Multi-camera bandwidth profiling bằng dữ liệu RGB-D tổng hợp  
**Phụ trách điều phối & tổng hợp:** Thành viên 1 (TV1 — Tích hợp)  
**Phạm vi áp dụng:** Thống nhất giữa TV1, TV2 (Producer/Memory), TV3 (Metrics/Plot), TV4 (Protocol/Theory), TV5 (QA/Runner).

---

## 1. Cấu hình Camera RGB-D Tổng hợp (Synthetic Camera Configuration)

Để mô phỏng chính xác luồng dữ liệu camera Intel RealSense D435 / D455 trên máy laptop HP Victus 16 khi chưa gắn sensor vật lý:
- **RGB Stream:**
  - Định dạng: 3 kênh màu (RGB), kiểu dữ liệu `uint8` (8-bit per channel).
  - Độ phân giải mặc định: 640x480 (VGA) hoặc 1280x720 (HD).
  - Kích thước 1 frame RGB (640x480): $640 \times 480 \times 3 = 921,600 \text{ bytes} \approx 0.879 \text{ MB}$.
- **Depth Stream:**
  - Định dạng: 1 kênh độ sâu (Depth 16-bit raw Z-distance), kiểu dữ liệu `uint16` (2 bytes per pixel).
  - Độ phân giải: Tương đương RGB (640x480 hoặc 1280x720).
  - Kích thước 1 frame Depth (640x480): $640 \times 480 \times 2 = 614,400 \text{ bytes} \approx 0.586 \text{ MB}$.
- **Tổng 1 cặp RGB-D frame (640x480):**
  - $921,600 + 614,400 = 1,536,000 \text{ bytes} \approx 1.465 \text{ MB/frame}$.
  - Ở 30 FPS: Băng thông lý thuyết $\approx 1.465 \times 30 = 43.95 \text{ MB/s}$ cho **mỗi camera**.
  - 4 cameras @ 30 FPS: Băng thông raw $\approx 175.8 \text{ MB/s}$.
  - 8 cameras @ 30 FPS: Băng thông raw $\approx 351.6 \text{ MB/s}$.
- **Tham số cấu hình (CLI & config dict):**
  - `width`: mặc định `640`
  - `height`: mặc định `480`
  - `fps`: mặc định `30` (hoặc `60`)
  - `num_cameras`: `1`, `2`, `4`, `8`
  - `duration_sec`: thời gian chạy mỗi run (mặc định `10` giây)
  - `seed`: seed khởi tạo dữ liệu giả lập (đảm bảo tính lặp lại - reproducibility)

---

## 2. Đặc tả Metadata truyền giữa Producer và Consumer

Metadata được truyền qua IPC Queue (hoặc shared ring buffer slot header) độc lập với payload lớn (được lưu tại Shared Memory slot).

Cấu trúc metadata packet (`dict` hoặc `namedtuple`):

| Thuộc tính | Kiểu dữ liệu | Ý nghĩa |
|---|---|---|
| `camera_id` | `int` | ID của camera sinh frame (`0, 1, ..., num_cameras - 1`) |
| `frame_id` | `int` | Số thứ tự frame tăng tuần tự từ `0, 1, 2, ...` per camera |
| `slot_id` | `int` | Vị trí slot trong Shared Memory ring buffer (hoặc `-1` nếu dùng queue trực tiếp) |
| `t_produced` | `float` | Timestamp khi producer tạo xong frame (`time.perf_counter()`) |
| `t_pushed` | `float` | Timestamp khi đưa frame vào hàng đợi/slot |
| `payload_size_bytes` | `int` | Dung lượng dữ liệu frame (`len(rgb) + len(depth)`) |
| `is_overload_drop` | `bool` | Cờ đánh dấu nếu producer chủ động drop frame do consumer tắc nghẽn |

---

## 3. Quy ước Schema CSV & Các Metric đo lường

TV3 và TV5 sẽ xuất và kiểm tra kết quả theo cấu trúc CSV chuẩn hóa sau:

### File 1: Per-frame Telemetry (`frames_telemetry.csv`)
Ghi nhận chi tiết từng frame nhận được tại Consumer:
- `timestamp`: Thời điểm nhận frame (`time.perf_counter()`)
- `camera_id`: ID camera
- `frame_id`: ID frame
- `slot_id`: Slot ID
- `t_produced`: Thời điểm sinh frame
- `t_consumed`: Thời điểm consumer đọc xong frame
- `latency_ms`: Độ trễ end-to-end: $(t\_consumed - t\_produced) \times 1000$ (ms)
- `payload_bytes`: Kích thước frame (bytes)

### File 2: Run Summary Metrics (`summary_metrics.csv`)
Bảng tổng kết của từng cấu hình kiểm thử (Benchmark Run):
- `run_id`: Tên định danh lần chạy (ví dụ `run_cam4_fps30_shm`)
- `num_cameras`: Số lượng camera
- `target_fps`: FPS đặt mục tiêu
- `achieved_fps`: FPS thực tế đạt được per camera và toàn hệ thống
- `total_frames_produced`: Tổng số frame được sinh ra
- `total_frames_consumed`: Tổng số frame consumer xử lý thành công
- `dropped_frames`: Số frame bị rớt (`produced - consumed`)
- `drop_rate_pct`: Tỷ lệ rớt frame (%)
- `mean_latency_ms`: Độ trễ trung bình (ms)
- `p95_latency_ms`: Độ trễ phân vị thứ 95 (ms)
- `max_latency_ms`: Độ trễ tối đa (ms)
- `throughput_mb_s`: Băng thông truyền dữ liệu thực tế đạt được (MB/s)
- `cpu_util_pct`: Tỷ lệ sử dụng CPU trung bình (%)
- `ram_util_mb`: Bộ nhớ RAM sử dụng (MB)
- `status`: Trạng thái run (`VALID` hoặc `INVALID`)

---

## 4. Tên thư mục kết quả và Quy ước lưu trữ

- Đường dẫn gốc: `results/`
- Định dạng thư mục cho mỗi lần chạy:
  `results/run_YYYYMMDD_HHMMSS_<num_cam>cam_<fps>fps_<mode>/`
  - `mode`: `queue` (Direct Queue baseline) hoặc `shm` (Shared Memory zero-copy).
- Bên trong thư mục của mỗi run bao gồm:
  - `config.json`: Toàn bộ cấu hình tham số đầu vào.
  - `frames_telemetry.csv`: Dữ liệu đo theo từng frame.
  - `summary.json` / `summary.csv`: Thống kê tổng hợp.
  - `run.log`: Nhật ký chạy, ghi log các sự kiện cảnh báo hoặc lỗi.

---

## 5. Điều kiện xác định một Run bị coi là "Không hợp lệ" (Invalid Run)

TV5 khi chạy benchmark tự động cần đánh dấu `INVALID` và chạy lại nếu phát hiện một trong các tiêu chí:
1. **Lệch thời gian chạy (Duration Skew):** Thời gian chạy thực tế lệch quá $\pm 10\%$ so với `duration_sec` chỉ định (thường do crash sớm hoặc deadlock).
2. **Khởi tạo tiến trình thất bại:** Số tiến trình producer thực tế chạy ít hơn `num_cameras`.
3. **Mất an toàn bộ nhớ (Resource Leak / Uncleaned SHM):** Vùng nhớ chia sẻ không được giải phóng sau khi kết thúc run.
4. **Không thu được dữ liệu:** File `frames_telemetry.csv` rỗng hoặc không có bản ghi nào.
5. **Frame Sequence Discontinuity bất thường:** Nếu không cấu hình mode overload mà frame ID nhảy vọt không báo trước.

