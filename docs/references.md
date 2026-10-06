# Nguồn và ghi chú đọc của TV4

Ngày truy cập thực tế: 05/10/2026 (Asia/Bangkok). Ghi mức đã đọc qua công cụ duyệt web; không nhận đã đọc toàn bộ paper. Không đưa số hiệu năng từ nguồn thành số đo HP Victus.

## R2 — RealSense Multi-Camera configurations, D400

[Nguồn chính thức](https://dev.realsenseai.com/docs/multiple-depth-cameras-configuration/). Đã đọc mục 2 A–D, H và đoạn thu thập ảnh mục 3 B; trang không có phiên bản cố định trong nội dung đã đọc.

- Đầu vào/đầu ra: camera thật và kết nối USB; ảnh màu/depth.
- Chỉ số: tải truyền, điều kiện chạy nhiều camera, buffering gây trễ.
- Áp dụng: kiểm tra controller, nguồn điện, dây cáp, CPU và lượng ảnh chờ khi thử phần cứng.
- Giới hạn: cấu hình và SDK được mô tả không xác nhận laptop của nhóm. RGB8 phía ứng dụng có thể khác format trên dây.
- Lưu ý đơn vị: đoạn A viết 0.3×4 Gbps thành 1200 MBps. Phép đổi đúng là 1.2 Gbps = 150 MB/s; đây là sửa đơn vị, không phải cam kết năng lực USB.

## P1 — Intel RealSense Stereoscopic Depth Cameras

Keselman, Woodfill, Grunnet-Jepsen, Bhowmik, 2017. [Metadata](https://arxiv.org/abs/1705.05548), [PDF v2](https://arxiv.org/pdf/1705.05548v2). Bản PDF đã đọc ghi v2, 29/10/2017.

Đã đọc Abstract và §2.1–2.2 (trang 1–2), đoạn §4.1.1–4.1.2 (trang 4), §4.2–4.2.2 (trang 5), §4.2.6–4.2.8 (trang 6–7, chỉ đoạn hiển thị).

- Đầu vào/đầu ra: cặp ảnh stereo (hai ảnh từ hai góc nhìn); dữ liệu độ sâu.
- Chỉ số: sai số độ sâu, tỷ lệ điểm hợp lệ, khoảng cách đo; kiểm tra với ảnh chuẩn và bề mặt tường.
- Giới hạn: chất lượng cảm biến phụ thuộc cảnh, ánh sáng, chuyển động và thiết lập.
- Áp dụng: tách phép đo tốc độ phần mềm khỏi chất lượng depth. Không trích số đo chi tiết của paper vào bảng benchmark nhóm.

## P2 — DeepStream: Bandwidth Efficient Multi-Camera Video Streaming for Deep Learning Analytics

Guo và cộng sự, 2023. [Bản HTML v1](https://arxiv.org/html/2306.15129v1), [metadata](https://arxiv.org/abs/2306.15129). v1 ngày 27/06/2023. Đây là paper cùng tên, khác NVIDIA DeepStream SDK.

Đã đọc Abstract, §2.2, §3, đoạn §5.2–5.3 và §6–7.1 qua HTML; chưa đọc toàn văn mọi phần đánh giá.

- Đầu vào/đầu ra: video nhiều camera; video nén gửi tới máy xử lý và kết quả nhận diện.
- Phương pháp: cắt vùng không cần thiết, phân bổ tốc độ truyền theo nội dung, điều chỉnh thời gian truyền.
- Chỉ số: băng thông, độ trễ, chất lượng nhận diện (F1, điểm gộp độ đúng và độ bao phủ).
- Giới hạn: đánh giá mạng/video và nhận diện; không đo USB hay hàng chờ RGB-D trên HP Victus.
- Áp dụng: so lợi ích giảm tải với chi phí mất thông tin. Không dùng paper để khẳng định latest cải thiện chất lượng robot.

## R3 — Python shared_memory

[Python 3.11](https://docs.python.org/3.11/library/multiprocessing.shared_memory.html). Trang hiển thị tài liệu 3.11.17 khi truy cập; môi trường đo thực tế chưa chốt.

Đã đọc mô tả SharedMemory, close/unlink và ví dụ NumPy. Áp dụng việc xác định tiến trình sở hữu vùng nhớ, đóng các handle và dọn tài nguyên. Ví dụ có thao tác sao chép; dùng chung bộ nhớ không đồng nghĩa toàn hệ thống không sao chép. Chưa kiểm chứng hành vi dọn trên máy Windows của nhóm.

## R1 — Repo gốc

[Snapshot tham chiếu](https://github.com/mirzafahad/realsense-multicam/tree/ee144efd09bf534d8dc1b5f718fce7a4b89686a7).

Đã thử mở snapshot và README cố định ngày 05/10/2026 nhưng công cụ trả lỗi. Chưa trực tiếp xác minh nội dung/giấy phép của snapshot trong lượt thực hiện này. Thông tin kiến trúc và nguồn gốc hiện dựa trên mục 2 của kế hoạch gốc; xem [UPSTREAM.md](../UPSTREAM.md). TV1 cần xác minh khi có repo.

## Nguồn nội bộ đã đọc

- [Kế hoạch hành động TV4](../../dumb-scribings/agent-responses/Ke-hoach-hanh-dong-TV4.md).
- [Thứ tự phối hợp](../Thu_tu_trien_khai_va_phoi_hop_Team5.md).
- [Kế hoạch gốc](../Ke_hoach_T7_MultiCamera_Team5_Windows11.md): phạm vi, kiến trúc, mục 9–11, 15–17, yêu cầu báo cáo/nộp bài và Phụ lục A.

Các kiểm tra Linux được kế hoạch gốc kể lại là thông tin tài liệu; TV4 chưa chạy lại và không dùng làm số đo nhóm.

