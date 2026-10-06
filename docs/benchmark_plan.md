# Kế hoạch đo RGB-D tổng hợp — TV4

Phiên bản: TV4-draft-1.0 · Ngày: 05/10/2026 · Trạng thái: đã soạn, chưa được nhóm xác nhận và chưa khóa để đo.

Nhóm dùng RGB-D tổng hợp để đo khả năng xử lý nhiều luồng của phần mềm trên Windows 11; chưa đo USB hoặc camera RealSense thật. RGB-D là ảnh màu đi kèm dữ liệu độ sâu. Lượng dữ liệu trong bảng là số tính từ cấu hình, chưa phải số đo.

Nguồn thiết kế: [kế hoạch gốc](../Ke_hoach_T7_MultiCamera_Team5_Windows11.md), mục 9–13; [thứ tự phối hợp](../Thu_tu_trien_khai_va_phoi_hop_Team5.md). Công thức, điều kiện hợp lệ và cột CSV nằm trong [phương pháp](methodology.md).

## Câu hỏi cần trả lời

1. Tăng số camera từ 1 lên 2, 4, 6 ảnh hưởng FPS (số cặp ảnh hoàn thành mỗi giây), độ trễ và ảnh còn chờ thế nào?
2. Tăng độ phân giải ở cùng 30 FPS ảnh hưởng khả năng xử lý ra sao?
3. Thêm 15/30 ms xử lý cho mỗi cặp RGB-D gây nghẽn thế nào?
4. Ưu tiên ảnh mới có giảm độ trễ, và cần bỏ bao nhiêu ảnh?

## Cấu hình chung dự kiến

| Thành phần | Giá trị |
|---|---|
| Nguồn | RGB `uint8`, H×W×3; depth `uint16`, H×W; 5 byte/pixel |
| Dữ liệu | Mẫu tĩnh riêng từng camera, tái dùng nhưng sao chép đầy đủ mỗi lượt |
| Seed | 42; mỗi camera dùng seed + mã camera để tạo lại dữ liệu |
| Số camera | 1, 2, 4, 6 |
| Khoảng đo | 30 giây/lượt; 3 lần độc lập/cấu hình |
| Ô nhớ | 32/camera; chỉ đổi đồng loạt trước khóa nếu cần |
| Hiển thị/GPU/AI | Không hiển thị; không chạy AI; GPU chưa đo |
| FIFO | Xử lý theo thứ tự đến |
| latest | Giữ ảnh mới nhất từng camera trong nhóm ảnh đã đọc, bỏ ảnh cũ |
| Thiết bị chính | HP Victus 16, Windows 11 theo kế hoạch; chưa có hồ sơ cấu hình máy thực tế |

## Bảng cấu hình và lượng dữ liệu tính toán

MB = 1.000.000 byte; Mbps = 1.000.000 bit/giây. Dùng dấu chấm cho số thập phân để khớp CSV.

| Profile | Kích thước | FPS/camera | Byte/cặp RGB-D | Mbps/camera | MB/s/camera |
|---|---|---:|---:|---:|---:|
| P0 | 424×240 | 5 | 508800 | 20.352 | 2.544 |
| P1 | 640×480 | 30 | 1536000 | 368.640 | 46.080 |
| P2 | 1280×720 | 30 | 4608000 | 1105.920 | 138.240 |

Bộ cấu hình: FIFO, delay 0, các giá trị chung ở trên.

| ID | Profile | Camera | Tổng FPS mục tiêu | Mbps tính toán | Lần lặp |
|---|---|---:|---:|---:|---:|
| M01 | P0 | 1 | 5 | 20.352 | 3 |
| M02 | P0 | 2 | 10 | 40.704 | 3 |
| M03 | P0 | 4 | 20 | 81.408 | 3 |
| M04 | P0 | 6 | 30 | 122.112 | 3 |
| M05 | P1 | 1 | 30 | 368.640 | 3 |
| M06 | P1 | 2 | 60 | 737.280 | 3 |
| M07 | P1 | 4 | 120 | 1474.560 | 3 |
| M08 | P1 | 6 | 180 | 2211.840 | 3 |
| M09 | P2 | 1 | 30 | 1105.920 | 3 |
| M10 | P2 | 2 | 60 | 2211.840 | 3 |
| M11 | P2 | 4 | 120 | 4423.680 | 3 |
| M12 | P2 | 6 | 180 | 6635.520 | 3 |

Bộ gây nghẽn: P2, 6 camera, 30 FPS/camera; mỗi dòng chạy 3 lần.

| ID | Policy | Delay/cặp RGB-D | Đối chiếu |
|---|---|---:|---|
| F0 | fifo | 0 ms | Mốc đối chứng gây nghẽn |
| F1 | fifo | 15 ms | So với F0 |
| F2 | fifo | 30 ms | So với F0 |
| I0 | latest | 0 ms | So với F0 |
| I1 | latest | 15 ms | So với F1 |
| I2 | latest | 30 ms | So với F2 |

Đầy đủ: 36 + 18 = 54 lượt, 27 phút đo thuần, chưa gồm khởi động và thời gian nghỉ. M12 và F0 cùng thông số nhưng suite mặc định vẫn chạy riêng; không tự loại một bộ sau khi xem kết quả.

P1/P2 giữ cùng FPS để so độ phân giải. P0/P1 đổi cả FPS lẫn độ phân giải, chỉ so được tải kết hợp. Khi so policy phải giữ cùng seed, số ô nhớ, thời gian, máy và phiên bản code.

## Trình tự và lệnh bàn giao cho TV5

Các lệnh dưới đây là hướng dẫn cho bản code sẽ tích hợp, chưa được chạy trong thư mục hiện tại. Chạy từ gốc repo nhóm sau khi TV1 chuẩn bị Python và các module `benchmark.*`.

1. Chạy thử một camera, kiểm tra đếm ảnh và dọn bộ nhớ.
2. Chạy thử đối chứng P2 N=6; kiểm tra bộ nhớ trước khi gây nghẽn.
3. Xử lý các điểm trong [review](integration_review.md), ghi commit code và môi trường.
4. Nhóm xác nhận rồi khóa quy trình; chạy làm nóng riêng P1 một camera 3 giây.
5. Chạy một suite duy nhất, tuần tự; kiểm tra đủ 54 lượt trước tổng hợp.

```powershell
.\.venv\Scripts\python.exe -m benchmark.bench --cameras 1 --width 424 --height 240 --fps 5 --duration 30 --slots 32 --policy fifo --delay-ms 0 --seed 42 --out results/smoke_B0_01
.\.venv\Scripts\python.exe -m benchmark.bench --cameras 6 --width 1280 --height 720 --fps 30 --duration 30 --slots 32 --policy fifo --delay-ms 0 --seed 42 --out results/smoke_BF_01
.\.venv\Scripts\python.exe -m benchmark.bench --cameras 1 --width 640 --height 480 --fps 30 --duration 3 --slots 32 --policy fifo --delay-ms 0 --seed 42 --out results/warmup_01
.\.venv\Scripts\python.exe -m benchmark.suite --set all --root results/session_01 --duration 30 --repeats 3 --slots 32 --seed 42
.\.venv\Scripts\python.exe -m benchmark.plot --root results/session_01
```

Không dùng lại thư mục kết quả cũ. TV5 lưu lệnh, nhật ký, thứ tự chạy, config, summary và các CSV. Không chạy plot hoặc tác vụ nặng trên máy trong lúc đo.

## Bộ nhớ và phương án rút gọn

Pool (vùng nhớ ảnh cấp sẵn) = camera × ô/camera × byte/cặp ảnh. N=6, 32 ô: P0 97.6896 MB; P1 294.912 MB; P2 884.736 MB. Đây chưa phải tổng RAM cần dùng. TV2/TV5 phải kiểm tra cả mẫu ảnh, bản sao, tiến trình và RAM còn trống.

Nếu cần 16 ô, cập nhật phiên bản kế hoạch trước đo và dùng 16 cho toàn bộ phép so sánh; P2 N=6 cần pool 442.368 MB. Không trộn session 16 và 32 ô.

Phương án rút gọn theo mục 10.5: P1/P2 × N=1/6 × 3 lần = 12 lượt; FIFO P2 N=6 delay 0/15/30 × 3 = 9; latest delay 15/30 × 3 = 6. Tổng 27 lượt nếu chạy riêng. Suite mặc định không sinh đúng subset này; TV5 cần lệnh riêng. Chọn subset trước đo, không chọn theo kết quả đẹp.

## Điều kiện khóa

- TV1: cung cấp URL repo, commit code, môi trường và tình trạng thay đổi chưa commit.
- TV2: xác nhận nguồn ảnh, nhịp phát, thông tin đi kèm và trả ô nhớ đúng.
- TV3: xác nhận công thức, CSV, đồng hồ, đủ ba lượt và nhóm tổng hợp không bị trộn cấu hình.
- TV5: cung cấp chạy thử bản tải sạch, đối chứng, dọn bộ nhớ và hồ sơ máy.
- TV4: cập nhật phiên bản và cấu hình đã xác nhận.

Hiện chưa có các xác nhận trên. Commit đo: chưa có. Phương án chốt: chưa có; bản này đề xuất bộ đầy đủ. Không dùng chữ “đã khóa” cho bản nháp.

