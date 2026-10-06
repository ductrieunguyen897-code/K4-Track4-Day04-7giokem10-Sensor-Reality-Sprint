# Ghi Chú Đọc Nguồn Tài Liệu Chuyên Sâu — TV2 (Source & Memory Lead)

**Ngày đối chiếu:** 05/10/2026  
**Người thực hiện:** Thành viên 2 (TV2 — Source & Memory Lead)  
**Phạm vi:** Nghiên cứu kiến trúc nguồn dữ liệu, vòng đời bộ nhớ dùng chung và các giả định vật lý của cảm biến camera RGB-D.

---

## 1. Nguồn R1: Fahad Mirza — `realsense-multicam`
- **URL:** <https://github.com/mirzafahad/realsense-multicam>
- **Commit:** `4993d0f` (upstream snapshot) | **Ngày truy cập:** 05/10/2026
- **Phần trọng tâm:** `producer()` function, process-based streaming pipeline, shared memory block, queue metadata IPC.

### Bốn dòng chuẩn mực:
1. **Input/Output của phương pháp:**
   - *Input:* Khung hình vật lý từ các camera Intel RealSense (qua `pyrealsense2` pipeline) chạy trên từng tiến trình worker độc lập.
   - *Output:* Dữ liệu ảnh ghi trực tiếp vào vùng SharedMemory được định danh trước; chỉ số slot và thông tin đồng bộ đẩy qua `multiprocessing.Queue` tới tiến trình consumer hiển thị.
2. **Metric nguồn đo:**
   - FPS thu nhận thực tế trên từng camera khi chạy trên phần cứng nhúng (Jetson AGX/Xavier) và D405; FPS tổng hợp khi hiển thị OpenCV.
3. **Limitation:**
   - Mã nguồn được tối ưu cho môi trường Linux/POSIX, giả định cơ chế chia sẻ bộ nhớ fork/shared memory không bị hạn chế bởi cơ chế bảo vệ handle nghiêm ngặt của Windows; không có cơ chế pacing bù trễ hoặc accounting bảo toàn chặt chẽ khi consumer bị nghẽn (dễ gây crash hoặc tràn bộ đệm nếu không giới hạn).
4. **Điều nhóm sử dụng được:**
   - Kế thừa mô hình phân tách kiến trúc: **Mỗi camera là một tiến trình con (Producer)**, tách biệt payload (SharedMemory) và metadata (Queue); chuyển thể sang kiến trúc benchmark tổng hợp (synthetic) hỗ trợ Windows `spawn` với pool hữu hạn và quản lý handle nghiêm ngặt.

---

## 2. Nguồn R3: Python 3.11 Library Reference — `multiprocessing.shared_memory`
- **URL:** <https://docs.python.org/3.11/library/multiprocessing.shared_memory.html>
- **Section:** Class `SharedMemory`, các phương thức `close()` và `unlink()`, phần lưu ý nền tảng Windows. | **Ngày truy cập:** 05/10/2026

### Bốn dòng chuẩn mực:
1. **Input/Output của phương pháp:**
   - *Input:* Yêu cầu cấp phát vùng nhớ dùng chung theo tên (`name`) và kích thước (`size` tính bằng byte) giữa nhiều tiến trình Python độc lập.
   - *Output:* Đối tượng bộ đệm byte `memoryview` (`shm.buf`) cho phép đọc/ghi trực tiếp mảng NumPy không qua serialization.
2. **Metric nguồn đo:**
   - Tính tương thích đa tiến trình, tính hợp lệ của con trỏ bộ đệm, thời gian tồn tại của handle hệ điều hành và rò rỉ bộ nhớ (memory leaks).
3. **Limitation:**
   - Hành vi trên Windows khác biệt cơ bản với POSIX: Windows dùng named file-mapping; nếu một tiến trình gọi `unlink()` sớm trong khi các tiến trình khác còn giữ handle sẽ dẫn đến lỗi hoặc hành vi không xác định; nếu tiến trình chết đột ngột mà không đóng, tài nguyên hệ điều hành có thể không được giải phóng ngay.
4. **Điều nhóm sử dụng được:**
   - Thiết kế nguyên tắc sở hữu (Ownership Lifecycle): **Chỉ duy nhất tiến trình cha (Parent Process) có quyền gọi `create=True` và `unlink()`**, các tiến trình con Producer chỉ mở theo `name`, giải phóng `del view` và `shm.close()` khi kết thúc; không bao giờ gọi `unlink()` từ worker.

---

## 3. Nguồn P1: Keselman, Woodfill, Grunnet-Jepsen, Bhowmik (2017)
- **Tiêu đề:** *Intel RealSense Stereoscopic Depth Cameras*
- **URL:** <https://arxiv.org/abs/1705.05548> · **PDF:** <https://arxiv.org/pdf/1705.05548> | **Ngày truy cập:** 05/10/2026
- **Section:** Section 2 (System Architecture), Section 3 (Stereo Depth Engine), Table 1.

### Bốn dòng chuẩn mực:
1. **Input/Output của phương pháp:**
   - *Input:* Cặp ảnh hồng ngoại (IR stereo pair) được chiếu mẫu họa tiết laser hồng ngoại chủ động từ projector.
   - *Output:* Bản đồ độ sâu (Z16: 16-bit depth values tính theo mm) kết hợp với luồng ảnh màu RGB được căn chỉnh (aligned RGB-D).
2. **Metric nguồn đo:**
   - Khoảng cách đo độ sâu hiệu dụng (operating range: 0.1m - 10m), sai số chiều sâu theo khoảng cách (Z-error $\propto Z^2$), độ phân giải không gian và tần số quét (lên tới 90 FPS với depth stream).
3. **Limitation:**
   - Nghiên cứu tập trung vào nguyên lý cảm biến stereo chủ động, độ chính xác quang học và thuật toán tương quan điểm ảnh trên ASIC; không cung cấp đánh giá về thông lượng băng thông bộ nhớ hoặc giới hạn bus IPC trên laptop cá nhân chạy nhiều luồng dữ liệu đồng thời.
4. **Điều nhóm sử dụng được:**
   - Làm rõ cơ sở vật lý cho mô hình dữ liệu của nhóm: Camera RGB-D cung cấp luồng màu chuẩn 24-bit (RGB8: 3 bytes) và luồng độ sâu 16-bit nguyên không dấu (uint16 depth: 2 bytes), tạo thành tổng payload **5 bytes/pixel (40 bit/pixel)**; phân biệt rõ rằng benchmark phần mềm của nhóm chỉ đo đường truyền IPC/Memory, không đo độ trễ phơi sáng quang học hay sai số stereo của cảm biến thật.

