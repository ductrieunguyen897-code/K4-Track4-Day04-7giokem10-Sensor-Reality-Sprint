# Nguồn gốc và phạm vi thay đổi

Nguồn được kế hoạch gốc chỉ định: [mirzafahad/realsense-multicam](https://github.com/mirzafahad/realsense-multicam).

Commit tham chiếu: `ee144efd09bf534d8dc1b5f718fce7a4b89686a7`.
[Snapshot](https://github.com/mirzafahad/realsense-multicam/tree/ee144efd09bf534d8dc1b5f718fce7a4b89686a7).

Ngày 05/10/2026: thư mục hiện tại không có .git, mã multicam hoặc benchmark đã tách ra. Chưa có bằng chứng fork/copy source. Lượt truy cập snapshot qua công cụ duyệt web thất bại; không nhận đã xác minh trực tiếp source hoặc giấy phép.

## Phần dự kiến kế thừa và điều chỉnh

Dựa trên mục 2 và Phụ lục A của [kế hoạch gốc](Ke_hoach_T7_MultiCamera_Team5_Windows11.md):

| Thành phần | Ý tưởng dự kiến | Trạng thái thực tế |
|---|---|---|
| Kiến trúc | Một tiến trình mỗi camera, ảnh trong vùng nhớ chung, thông tin qua hàng chờ | Chưa có code tích hợp |
| Nguồn | Thay camera thật bằng RGB8 + depth uint16 tổng hợp | Có code mẫu trong tài liệu; chưa tách/chạy |
| Bộ nhớ | Tiến trình chính giữ vùng nhớ xuyên suốt, ô nhớ hữu hạn | Chưa kiểm tra Windows |
| Xử lý | Sao chép cả RGB và depth, FIFO/latest cùng số ô | Chưa có số đo |
| Bộ đo | perf_counter, đếm ảnh, CSV, tài nguyên | Đã review tĩnh code mẫu |
| Đóng góp TV4 | Kế hoạch đo, phương pháp, nguồn, giới hạn và khung kết luận | File tài liệu đã tạo tại đây |

Code mẫu hỗ trợ hiện nằm trong kế hoạch gốc, chưa được TV4 đưa thành các module executable. Không gọi bảng trên là thay đổi đã triển khai của nhóm.

Kế hoạch gốc ghi repo khai báo GPL-3.0. TV1 cần đọc LICENSE tại snapshot trước khi sao chép; giữ giấy phép và ghi công phù hợp. TV4 chưa tạo hoặc thay LICENSE từ suy đoán.

URL repo nhóm, commit tích hợp và commit đo: chưa được cung cấp.

