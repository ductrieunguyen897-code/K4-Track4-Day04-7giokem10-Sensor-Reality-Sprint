# Review tích hợp và kết quả — TV4

Ngày 05/10/2026. Phạm vi: đọc tĩnh ba khối Python ở Phụ lục A của [kế hoạch gốc](../Ke_hoach_T7_MultiCamera_Team5_Windows11.md). Chưa có file Python tích hợp, CSV, JSON kết quả hoặc biểu đồ để review thực nghiệm.

## Những phần khớp thiết kế trên giấy

- Nguồn tạo mẫu riêng từng camera, sao chép cả RGB và depth.
- Thông tin đi kèm gồm camera, seq, slot và hai thời điểm.
- Tiến trình chính sở hữu vùng nhớ; nguồn đóng handle của mình.
- FIFO/latest cùng dung lượng ô, cùng delay cho mỗi cặp RGB-D.
- Mẫu hoàn thành trong cửa sổ tách khỏi ảnh trễ và ảnh dọn lúc kết thúc.
- Đếm ảnh kiểm tra bằng ba đẳng thức từng camera.
- Suite chạy tuần tự, ba lần lặp, lưu thứ tự/lệnh/log và dừng khi tiến trình trả lỗi.

Đây là nhận xét về code trong Markdown, chưa chứng minh nó chạy đúng trên Windows.

## Các điểm cần xử lý trước khóa

| Mức | Vị trí code mẫu | Vấn đề và việc cần làm | Người nhận |
|---|---|---|---|
| Cần xác nhận trước đo | bench.run, summary | status có thể vẫn ok khi completed=0 nếu đếm khớp. Kiểm tra completed>0 và latency hữu hạn ngoài status; nên đưa điều kiện vào bộ kiểm tra hợp lệ | TV3/TV5 |
| Cần xác nhận trước đo | bench.run, lấy mẫu probes | len(probes) chỉ phản ánh số process mở ban đầu. NoSuchProcess khi lấy mẫu bị bỏ qua mà số probes không đổi; CPU/RSS có thể thành tổng thiếu nhưng vẫn được coi đủ. Theo dõi số process đọc thành công mỗi mẫu và lý do thiếu | TV3 |
| Cần xác nhận trước tổng hợp | plot.main, groups | Khóa nhóm chưa chứa slots, duration, seed, code commit hoặc môi trường; có thể gộp điều kiện khác nếu để chung root. Kiểm tra đồng nhất session hoặc thêm phân nhóm theo các thông số này | TV3 |
| Cần xác nhận trước tổng hợp | plot.main, n_runs | Script không bắt buộc đủ ba lượt mỗi nhóm và không kiểm tra toàn bộ accounting/config trước plot. TV5 kiểm tra bộ dữ liệu, TV3 chặn nhóm thiếu/thừa hoặc không đồng nhất | TV3/TV5 |
| Cần xác nhận trước tổng hợp | plot.main, values | n_runs đếm số lượt nhưng không ghi số mẫu hợp lệ của từng metric khi giá trị null. CPU mean có thể dựa trên ít hơn ba lượt. Ghi n_valid và lý do thiếu | TV3 |
| Phạm vi đầu ra | plot.main, metrics | Aggregate chưa tổng hợp FPS tổng, completion, backlog, RAM và deadline miss. Bổ sung nếu các trường được trình bày trong bảng chung | TV3 |
| Diễn giải | bench.release, frames.csv | late_completion cũng có latency trong CSV. Lọc completed khi so với summary, giữ ảnh trễ riêng | TV3/TV4 |
| Kiểm tra trên máy | bench finally | Cần thử thoát bình thường, lỗi nguồn và ngắt trên Windows; xác nhận không còn worker, đóng vùng nhớ và chạy lượt sau được | TV2/TV5 |

Không sửa code của TV2/TV3 vì hiện chỉ có code mẫu trong tài liệu. Bàn giao bảng này để kiểm tra trên bản tích hợp thực tế.

## Checklist kết quả khi TV5 bàn giao

- [ ] Có URL repo, code commit, phiên bản quy trình và hồ sơ đúng máy.
- [ ] Đủ 36 lượt matrix + 18 lượt failure, hoặc subset đã chốt trước đo.
- [ ] Mỗi nhóm đủ 3 lượt hợp lệ; không trộn số ô, thời gian, seed hoặc code.
- [ ] Mỗi lượt có config, summary, frames, resources, per_camera, command và console log.
- [ ] Tất cả đẳng thức đếm đúng từng camera; CSV khớp JSON.
- [ ] P95/mean được tính trên completed; đơn vị ms; phân biệt tổng và từng camera.
- [ ] Có camera chậm nhất, completion, drop, lỡ nhịp và ảnh còn chờ.
- [ ] CPU/RAM đủ mẫu; thiếu phải ghi rõ, GPU NA nếu chưa đo.
- [ ] Biểu đồ hiện đủ lần lặp và giải thích SD, không gọi SD là khoảng tin cậy.
- [ ] Kết luận có đường dẫn tới bộ số liệu cụ thể trong EVIDENCE_INDEX.

Trạng thái review kết quả: chưa thực hiện vì chưa có dữ liệu. Không xác nhận đợt C/D/E đã hoàn tất.

