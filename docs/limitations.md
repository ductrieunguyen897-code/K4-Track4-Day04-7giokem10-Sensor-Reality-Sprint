# Giới hạn phép đo

Trạng thái 05/10/2026: chưa có code tích hợp hoặc số đo trong thư mục dự án. Cấu hình thí nghiệm mới là đề xuất trong [kế hoạch](benchmark_plan.md).

- Dữ liệu tổng hợp không đại diện cảm biến thật: chưa đo USB, driver, thời gian camera thu ảnh, độ chính xác depth, ảnh hưởng quang học hoặc đồng bộ camera.
- Depth ngẫu nhiên không mang đơn vị khoảng cách thực. Mẫu tĩnh không phản ánh cảnh động; có thể làm dữ liệu trong bộ nhớ được tái sử dụng thuận lợi hơn.
- Hệ thống sao chép ảnh ở nguồn và phía xử lý. Dùng chung bộ nhớ không loại bỏ các lần sao chép.
- Lượng dữ liệu tính bằng kích thước ảnh chưa phải lưu lượng trên USB hoặc toàn bộ lưu lượng bộ nhớ.
- Pool cấp sẵn hữu hạn; ảnh còn chờ bị giới hạn bởi số ô. RAM không nhất thiết tăng khi ảnh chờ tăng.
- Warm-up riêng không loại mọi dao động lúc bắt đầu từng lượt. Không tự cắt mẫu đầu sau khi xem kết quả.
- Ba lượt chỉ phản ánh dao động trong phạm vi đã thử; chưa đủ để khái quát mọi máy và tác vụ.
- Độ trễ chỉ tính ảnh completed, dễ thấp hơn khi ảnh cũ bị bỏ nhiều. Phải đọc kèm tỷ lệ hoàn thành, bỏ ảnh, ảnh còn chờ và từng camera.
- CPU/RAM phụ thuộc việc thu đủ mẫu của tiến trình chính và nguồn. Tổng RSS có thể đếm bộ nhớ chung nhiều lần. Thiếu dữ liệu phải ghi NA và lý do.
- GPU chưa đo. Chưa chạy AI hoặc SLAM (xây bản đồ và xác định vị trí); chưa đo chất lượng hoặc an toàn tác vụ robot.
- latest giữ ảnh mới trong nhóm đã lấy, chưa bảo đảm đồng bộ thời điểm giữa camera hay tăng FPS.
- N=8 và các interface khác trong thiết kế tương lai chưa được thử. Không ngoại suy N=6 thành số đo N=8.

Các phát biểu từ tài liệu nguồn nằm trong [references.md](references.md). Chỉ bổ sung “quan sát được” khi có run ID và liên kết bằng chứng.

