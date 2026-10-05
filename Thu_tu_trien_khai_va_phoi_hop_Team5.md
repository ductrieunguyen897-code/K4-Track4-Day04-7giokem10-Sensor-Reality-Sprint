# Thứ tự triển khai và phối hợp song song — Team 5 người

**Đề tài:** T7 — Multi-camera bandwidth profiling bằng dữ liệu RGB-D tổng hợp  
**Môi trường đo:** Laptop HP Victus 16, Windows 11, chưa có camera RealSense  
**Ngày:** 05/10/2026

Nhóm có thể làm song song nhiều phần. Thứ tự chung là:

**Thống nhất cách làm → chia việc song song → tích hợp → chạy đo → phân tích và viết báo cáo.**

Các mốc trong kế hoạch là mốc tổ chức công việc, không có nghĩa TV1 phải làm xong toàn bộ thì TV2 mới bắt đầu.

## 1. Cả nhóm thống nhất đầu vào và đầu ra trước

Dành khoảng **20–30 phút** đầu tiên để thống nhất. TV1 điều phối, TV4 trình bày thiết kế thí nghiệm, TV2 và TV3 thống nhất cách nối producer với consumer.

Cần chốt:

- Cấu hình camera tổng hợp: resolution, FPS, số camera và seed.
- Metadata truyền giữa các phần: camera ID, số thứ tự frame, slot bộ nhớ và timestamp.
- Metric sẽ đo và các cột CSV.
- Lệnh chạy, tên thư mục kết quả và điều kiện một run bị coi là không hợp lệ.

Chốt những điểm này trước giúp từng người làm riêng mà sản phẩm vẫn ghép được với nhau. Nhóm đã có code mẫu trong file kế hoạch chi tiết, nên bước này chủ yếu là đọc hiểu và thống nhất phần mỗi người chịu trách nhiệm.

## 2. Các đợt làm việc và phần có thể làm song song

| Đợt | Những việc làm song song | Điều kiện chuyển sang đợt tiếp theo |
|---|---|---|
| **A — Chuẩn bị** | **TV1:** repo, môi trường Windows và bộ khung. **TV2:** đọc producer/shared memory. **TV3:** định nghĩa metric và CSV. **TV4:** đọc nguồn, chốt bảng thí nghiệm. **TV5:** chuẩn bị checklist và lệnh kiểm tra. | Có bộ khung chạy được và thống nhất cấu hình/định dạng dữ liệu |
| **B — Hoàn thiện từng phần** | **TV2:** producer, pacing và quản lý slot. **TV3:** logger, cách tính metric, script plot. **TV5:** runner và lưu log. **TV4:** methodology, references, limitations. **TV1:** hỗ trợ môi trường, review và tích hợp từng phần. | Chạy thử một camera, xuất được kết quả đúng định dạng |
| **C — Kiểm tra tích hợp** | **TV1 + TV2 + TV3:** sửa lỗi nối các phần. **TV5:** chạy thử từ bản clone sạch. **TV4:** đối chiếu code với protocol. | Baseline chạy được, đếm frame đúng, cleanup hoạt động |
| **D — Đo chính thức** | **TV5:** điều khiển laptop chạy benchmark. Những người còn lại chuẩn bị báo cáo/slide trên thiết bị khác hoặc xem tài liệu. | Có đủ run hợp lệ, config, log và CSV |
| **E — Phân tích và hoàn thiện** | **TV3:** tổng hợp và vẽ plot. **TV2:** giải thích queue/shared memory. **TV4:** đối chiếu nguồn và giới hạn kết luận. **TV5:** kiểm tra evidence. **TV1:** hoàn thiện README và đóng phiên bản. | Cả nhóm thống nhất failure và engineering decision, rồi hoàn thiện 5 báo cáo |

## 3. Thứ tự công việc riêng của từng thành viên

| Thành viên | Thứ tự thực hiện | Phần cần chờ người khác |
|---|---|---|
| **TV1 — Tích hợp** | Tạo repo/môi trường → đưa code mẫu vào → tích hợp từng phần → khóa code trước đo → hoàn thiện README và phiên bản nộp | Chờ phần producer, metrics và runner để kiểm tra tích hợp đầy đủ |
| **TV2 — Nguồn dữ liệu và bộ nhớ** | Hiểu metadata/slot → kiểm tra producer → kiểm tra FPS và lifetime → phối hợp thử overload/latest → giải thích failure | Cần định dạng chung; cần consumer của TV3 để kiểm tra toàn đường đi |
| **TV3 — Metric và plot** | Chốt công thức/CSV → làm logger và plot → kiểm tra đếm frame → đọc kết quả benchmark → tổng hợp số liệu | Có thể viết plot bằng dữ liệu mẫu trước; kết luận thật phải chờ TV5 chạy đo |
| **TV4 — Nghiên cứu và protocol** | Đọc đề/repo/tài liệu → chốt matrix và đối chứng → viết methodology/limitations → đối chiếu số đo → hoàn thiện decision và nội dung pitch | Chỉ phần kết luận dựa trên thực nghiệm phải chờ kết quả |
| **TV5 — QA và chạy thí nghiệm** | Viết checklist → chuẩn bị runner/log → chạy smoke và clone sạch → chạy matrix/failure → kiểm tra bằng chứng và checklist nộp | Runner có thể viết sớm; benchmark chính phải chờ bản tích hợp đã kiểm tra |

**TV4 và TV5 đều có việc từ đầu**, không phải đợi đến lúc code xong mới tham gia.

## 4. Những chỗ phải làm tuần tự

Có bốn điểm phụ thuộc quan trọng:

1. **Chốt metadata và CSV trước khi mỗi người hoàn thiện phần của mình.** Nếu TV2 gửi một kiểu dữ liệu còn TV3 đọc kiểu khác thì sẽ mất thời gian sửa lúc tích hợp.
2. **Baseline phải chạy đúng trước khi gây lỗi.** Nếu đếm frame hoặc timestamp còn sai, kết quả failure không đáng tin.
3. **Khóa code và protocol trước khi đo chính thức.** Nếu sửa logic giữa các run, cần ghi version và chạy lại phần bị ảnh hưởng.
4. **Có số đo rồi mới chốt kết luận và engineering decision.** Có thể chuẩn bị sẵn khung báo cáo, nhưng không điền trước kết quả mong muốn.

## 5. Phối hợp khi TV2 và TV3 cùng liên quan đến `bench.py`

Với bộ code mẫu hiện tại, nên phối hợp như sau:

- TV2 phụ trách hàm `producer()` và quản lý slot.
- Trong lúc đó, TV3 làm bảng metric, CSV schema và `plot.py`.
- TV2 bàn giao phần producer; TV3 tiếp tục chỉnh consumer/logger trong `run()`.
- Nếu cả hai sửa `bench.py` cùng lúc, phải thống nhất rõ vùng sửa và để TV1 merge lần lượt.

Như vậy vẫn làm song song được phần lớn công việc, đồng thời giảm xung đột cùng một file.

## 6. Phối hợp khi dùng laptop để benchmark

Trên laptop HP Victus dùng để đo, **các lần benchmark phải chạy lần lượt**. Không chạy hai cấu hình đồng thời, vì chúng sẽ tranh CPU/RAM và làm sai điều kiện so sánh. Trong lúc máy đang đo, cũng nên tránh chạy plot hoặc tác vụ nặng trên chính máy đó.

Nếu cả nhóm chỉ có **một laptop duy nhất**, việc thao tác máy phải luân phiên; các phần đọc tài liệu, review, chuẩn bị lời giải thích và phác thảo báo cáo vẫn có thể chia nhau thực hiện.

Nếu mỗi người có thiết bị riêng, phần chuẩn bị/code/tài liệu có thể song song rộng hơn, nhưng **dataset chính vẫn đo trên cùng một laptop đã chọn**.
