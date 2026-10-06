# Quyết định xử lý nhiều luồng — bản chuẩn bị

Ngày 05/10/2026 · Lựa chọn cuối: chưa kết luận.

**Bối cảnh:** robot có thể ưu tiên ảnh mới để phản ứng nhanh, hoặc cần giữ đủ ảnh để lưu dữ liệu. Nhóm chưa xác nhận ưu tiên tác vụ cuối cùng.

**Điều kiện:** dự kiến P2, 6 camera, 30 FPS/camera, delay 0/15/30 ms, FIFO/latest; cùng seed, duration, slots và phiên bản code. Xem [kế hoạch](benchmark_plan.md).

**Bằng chứng:** chưa có số đo nhóm; [chỉ mục bằng chứng](../results/EVIDENCE_INDEX.md) chưa có kết luận thực nghiệm.

**Lựa chọn và lý do:** chờ đủ ba lượt từng điều kiện. Nếu ưu tiên ảnh mới, chỉ chọn latest khi giảm độ trễ có ý nghĩa với tác vụ và tỷ lệ bỏ ảnh/từng camera vẫn chấp nhận được. Nếu cần giữ đủ ảnh, cân nhắc FIFO cùng giảm tải hoặc tăng khả năng xử lý. Không tăng hàng chờ vô hạn để che nghẽn.

**Đánh đổi cần đánh giá:** P95 latency, FPS tổng, FPS camera chậm nhất, completion, explicit drop, backlog và CPU/RAM. latest không được mặc định là tăng FPS.

**Giới hạn:** dữ liệu tổng hợp; chưa có USB, đồng bộ cảm biến, AI hoặc chất lượng robot. Nguồn tham khảo được ghi trong [references](references.md); phạm vi chi tiết ở [limitations](limitations.md).

**Kết nối tương lai:** khi có camera thật, kiểm tra mode thực sự hỗ trợ, format, controller USB, nguồn và dây cáp rồi đo lại. Chưa đủ căn cứ chọn model/controller hoặc so sánh GigE/CSI/GMSL2.

**Phép thử tiếp:** TV1 tích hợp code; TV2/TV3 xác nhận bộ đếm và ô nhớ; TV5 đo tuần tự theo quy trình đã khóa. Sau đó so FIFO/latest cùng delay và ghi số đo/bằng chứng trước khi chốt. Giai đoạn phần cứng phải thêm phép đo thu ảnh, đồng bộ và tác vụ thực.

Các thiết kế 4–8 camera trong mục 16 của kế hoạch gốc là đề xuất chưa kiểm chứng, không phải kết quả của nhóm.

