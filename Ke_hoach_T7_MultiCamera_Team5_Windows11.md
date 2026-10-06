# Kế hoạch triển khai T7: Multi-camera bandwidth profiling — nhóm 5 người

**Phiên bản:** 1.0 · **Ngày:** 05/10/2026 · **Thiết bị đã xác nhận:** một laptop HP Victus 16, Windows 11, chưa có camera RealSense.  
**Tên đề tài đề xuất:** *Synthetic RGB-D Multi-camera Pipeline Profiling on Windows 11*.  
**Phạm vi:** kế hoạch thực thi, phân công, code mẫu, phương pháp đo và chuẩn bị nộp bài; chưa có kết quả thực nghiệm của nhóm trên HP Victus.

> Đọc tài liệu này theo thứ tự: chốt vai trò → tạo repo → cài môi trường → sao chép code ở Phụ lục A → chạy smoke test → khóa protocol → benchmark → phân tích failure → báo cáo và VLearn. Code đầy đủ nằm ngay trong file Markdown này, không cần tải thêm bộ code riêng.

## Mục lục

1. Phạm vi và yêu cầu đầu ra
2. Repo gốc, khác biệt và lựa chọn triển khai
3. Phân công 5 người và phối hợp
4. Timeline chuẩn bị theo giờ
5. Timeline buổi lab 120 phút
6. Cấu trúc GitHub repo
7. Branch, commit, PR và đóng phiên bản
8. Cài đặt trên Windows 11
9. Chuẩn bị dữ liệu và baseline
10. Bảng thí nghiệm
11. Metric, công thức và quy tắc đếm frame
12. Lệnh chạy benchmark
13. Gây lỗi/nghẽn và kiểm tra cải tiến
14. Lưu log, tạo plot và truy vết
15. Phân tích failure case
16. Engineering decision và phác thảo 4–8 camera
17. Paper, tài liệu và kế hoạch đọc
18. Bố cục 5 báo cáo cá nhân
19. Slide pitch 3–5 phút
20. Checklist VLearn và điều kiện hoàn thành
21. Xử lý vướng mắc thường gặp
22. Kiểm tra code mẫu và giới hạn xác minh
23. Phụ lục A: toàn bộ script

## 1. Phạm vi và yêu cầu đầu ra

### 1.1. Bài toán cụ thể

Một robot dùng nhiều camera RGB-D cần nhận dữ liệu mới đủ nhanh để hỗ trợ quan sát môi trường. Khi tăng số luồng, độ phân giải hoặc tốc độ khung hình, phần mềm có thể xử lý không kịp dù chưa chạy mô hình AI. Nhóm nghiên cứu đường đi:

**Nguồn RGB-D tổng hợp → producer riêng cho từng camera → copy vào shared memory → queue metadata → consumer copy/xử lý → log và metric.**

Nhóm trả lời bốn câu hỏi:

1. Số virtual camera tăng từ 1 lên 2, 4, 6 làm FPS, độ trễ và backlog thay đổi thế nào?
2. Hai độ phân giải ở cùng 30 FPS làm tải payload và khả năng xử lý thay đổi ra sao?
3. Consumer bị thêm 15 hoặc 30 ms xử lý cho mỗi frameset sẽ gây failure gì?
4. Ưu tiên frame mới thay cho FIFO có giảm độ trễ không, và phải bỏ qua bao nhiêu frame?

### 1.2. Yêu cầu đã đọc từ 11 ảnh đính kèm

| Yêu cầu | Nhóm thực hiện bằng cách nào | Bằng chứng |
|---|---|---|
| T7: resolution × FPS × bit depth × số camera | Tính payload RGB8 + depth uint16, ghi Mbps/MB/s rõ ràng | `docs/methodology.md`, bảng cấu hình |
| 2–3 mức độ phân giải | 424×240, 640×480, 1280×720 | `config.json` mỗi run |
| FPS/latency/drop và CPU/GPU load | Đo FPS, độ trễ phần mềm, drop, CPU và working set; GPU ghi NA nếu không đo | CSV, summary, plot |
| Baseline có đối chứng | Cùng cấu hình chạy delay 0/15/30 ms; cùng nguồn và metric | Các run `failure_*` |
| Dữ liệu tổng hợp được phép | Ghi seed, dtype, shape, cách tạo và tải copy | Code và config |
| Failure case cụ thể | Queue tồn đọng khi consumer không theo kịp | Log backlog, P95, đếm frame |
| Phân biệt quan sát/nguồn/giả thuyết | Gắn nhãn ba loại phát biểu trong báo cáo | Năm báo cáo cá nhân |
| Quyết định kỹ thuật gắn với metric | So sánh FIFO và latest trong cùng điều kiện | Plot trade-off |
| Báo cáo theo 5 mục | Problem, Method, Benchmark, Failure case, Engineering decision | Báo cáo từng người |
| Pitch 3–5 phút | 5 slide, mỗi người phụ trách một phần | Slide chung và bản riêng |
| Repo chung, đúng 5 người | Tên repo theo mẫu; `TEAMMATES.md` ở gốc, họ tên + MSV | Repo |
| Nộp riêng | 5 lượt nộp, mỗi lượt có bản đúng người và cùng URL repo | Xác nhận VLearn |

Rubric trong ảnh: **40% demo/benchmark chạy được; 25% hiểu failure; 20% giải thích thuật toán/phương pháp; 15% trade-off**. Ưu tiên dành thời gian cho phép đo có bằng chứng và giải thích số đo.

### 1.3. Ranh giới kết luận

**Được đo trực tiếp:** hiệu năng pipeline phần mềm tổng hợp trên laptop; số frame hoàn thành; độ trễ từ bắt đầu copy nguồn đến hoàn thành consumer; drop chủ động và frame không được tiếp nhận; CPU/working set nếu bộ đo hoạt động.

**Chỉ được tính/ước lượng:** raw application payload, cấu hình interface tương lai, năng lực hệ thống khi có camera thật.

**Chưa được đo:** USB wire bandwidth, driver/ASIC latency, lỗi cảm biến, độ chính xác depth, optical interference, đồng bộ phần cứng, chất lượng detector/SLAM và GPU nếu không có log GPU.

Không đổi tên virtual camera thành camera thật trong bảng kết quả. Không lấy FPS trên Jetson của tác giả làm baseline số đo của HP Victus. Nếu mô phỏng không quá tải, báo cáo đúng kết quả; controlled delay vẫn cung cấp một failure có thể tái hiện.

**Câu mô tả phạm vi dùng trong báo cáo:**

> Nhóm dùng RGB-D tổng hợp để đo khả năng xử lý nhiều luồng của pipeline phần mềm trên Windows 11. Bandwidth trong bảng cấu hình là payload tính toán ở phía ứng dụng; nhóm chưa đo đường truyền USB hoặc camera RealSense vật lý.

## 2. Repo gốc, khác biệt và lựa chọn triển khai

### 2.1. Nguồn cố định

- Repo: <https://github.com/mirzafahad/realsense-multicam>.
- Commit đã đọc khi soạn tài liệu: **`ee144efd09bf534d8dc1b5f718fce7a4b89686a7`**.
- Snapshot: <https://github.com/mirzafahad/realsense-multicam/tree/ee144efd09bf534d8dc1b5f718fce7a4b89686a7>.
- Giữ LICENSE và ghi công tác giả khi fork/copy; repo khai báo GPL-3.0. Tài liệu này không thay thế license của source gốc.

README mô tả Jetson Orin với sáu D405, một process cho mỗi camera, shared memory chứa ảnh và queue chuyển metadata. Tác giả ghi nhận khoảng 30 FPS với hai camera và khoảng 5 FPS với sáu; đây là kết quả nguồn, khác điều kiện nhóm.

### 2.2. Những điểm phải hiểu trong source

| File | Điểm cần kiểm tra | Ảnh hưởng đến kế hoạch |
|---|---|---|
| `multicam/app.py` | Tạo `CameraConfiguration` chỉ với alias/serial, queue không đặt `maxsize` | Không mặc định resolution/FPS theo một hằng số chưa được dùng |
| `multicam/data_contract.py` | Default `(424,240)`, 5 FPS; `get_np_array()` thực hiện `.copy()` | P0 có căn cứ từ default; shared memory vẫn có copy vào/ra |
| `multicam/config.py` | `FRAME_RESOLUTION=(1280,720)` nhưng không truyền vào cấu hình tại `app.py` | Luôn ghi cấu hình thực sự dùng trong log |
| `multicam/camera_frame_producer.py` | RGB8, Z16; cấp block cho từng ảnh, copy rồi đóng handle; timestamp dùng `time.time()` sau copy | Payload ứng dụng 5 byte/pixel khi hai ảnh cùng kích thước; timestamp này không bao gồm acquisition/copy trước nó |
| `multicam/camera_frame_consumer.py` | Lấy/copy màu để hiển thị; depth không được dùng để tính toán như màu | Benchmark đọc cả RGB và depth là workload bổ sung, không tái tạo nguyên vẹn viewer |
| `multicam/utils.py` | Monkey patch resource tracker | Không mang patch này sang benchmark mới; dùng ownership rõ ràng |
| `pyproject.toml` | Python `^3.11.8`, Poetry và dependency camera | Benchmark không có hardware dùng môi trường nhỏ riêng, không cần `pyrealsense2` |

Link source cố định: [app](https://github.com/mirzafahad/realsense-multicam/blob/ee144efd09bf534d8dc1b5f718fce7a4b89686a7/multicam/app.py), [data contract](https://github.com/mirzafahad/realsense-multicam/blob/ee144efd09bf534d8dc1b5f718fce7a4b89686a7/multicam/data_contract.py), [producer](https://github.com/mirzafahad/realsense-multicam/blob/ee144efd09bf534d8dc1b5f718fce7a4b89686a7/multicam/camera_frame_producer.py), [consumer](https://github.com/mirzafahad/realsense-multicam/blob/ee144efd09bf534d8dc1b5f718fce7a4b89686a7/multicam/camera_frame_consumer.py), [utils](https://github.com/mirzafahad/realsense-multicam/blob/ee144efd09bf534d8dc1b5f718fce7a4b89686a7/multicam/utils.py).

### 2.3. Điều chỉnh cần thiết so với kế hoạch sơ bộ

1. **Không gọi shared memory là zero-copy toàn bộ pipeline.** Source gốc đã copy vào buffer và copy ra consumer. Code mẫu cũng copy đầy đủ payload ở cả hai phía.
2. **Lifetime trên Windows:** shared memory bị xóa khi mọi handle đóng. Producer tạo rồi đóng block trước lúc consumer mở có thể làm block không còn tồn tại. Code mẫu để process chính giữ handle xuyên suốt run. Xem tài liệu Python [R3].
3. **Backlog không phải drop:** frame còn chờ cuối cửa sổ đo được đếm riêng. Không lấy `produced-consumed` rồi gọi tất cả là dropped frames.
4. **Timestamp phần mềm:** dùng `time.perf_counter()` cùng host cho producer/consumer. Không trừ timestamp camera với đồng hồ host nếu chưa xử lý clock domain.
5. **RAM của pool cấp sẵn không nhất thiết tăng theo backlog.** Phép thử này dự đoán backlog/latency tăng; working set có thể ổn định. Không dùng “RAM chắc chắn tăng” làm kết luận bắt buộc.
6. **Không hứa tăng throughput khi dùng latest.** Latest cải thiện độ mới của dữ liệu bằng cách bỏ frame cũ; tốc độ xử lý vẫn bị giới hạn bởi consumer.

### 2.4. Kiến trúc benchmark chọn để thực thi

- Giữ ý tưởng một process/virtual camera, shared memory cho payload, queue cho metadata.
- Cấp **32 slot/camera** trong một block lớn, process chính sở hữu block. Producer lấy slot rảnh, copy RGB-D vào slot, gửi `(camera, seq, slot, capture_time, enqueue_time)`.
- Consumer copy toàn bộ slot ra buffer riêng; sau xử lý trả slot. Producer không được ghi đè slot đang chờ/đang đọc.
- FIFO xử lý theo thứ tự queue. Latest giữ frame gần nhất cho từng camera trong batch, trả slot của frame cũ và đếm `stale`.
- Cả hai policy giữ **cùng pool, số slot và consumer delay** để phép so sánh chỉ đổi policy.
- Queue/pool hữu hạn bảo vệ laptop. Không chạy thử unbounded allocation để cố làm hết RAM.
- Viewer OFF ở phép đo chính. Code mẫu không cài viewer, decode, resize hoặc AI model. Nếu bổ sung, phải tạo nhánh thí nghiệm riêng và ghi rõ workload mới.

Đây là **benchmark dựa trên kiến trúc repo**, không phải bằng chứng repo gốc đã chạy trên Windows hoặc tái hiện chính xác số FPS của tác giả.

## 3. Phân công 5 người và phối hợp

Chưa có họ tên/MSV thật nên dùng TV1–TV5. Nhóm tự điền, không bịa thông tin. Cả năm người phải đọc protocol và giải thích được ít nhất một baseline, một failure, một quyết định.

| Người | Vai trò và trách nhiệm chính | Sản phẩm sở hữu | Người review | Điều kiện bàn giao |
|---|---|---|---|---|
| **TV1** | Integration Lead: fork, Windows/Python, entry point, merge, version, kiểm tra reproducibility môi trường | README, requirements, skeleton, environment manifest | TV5 | Từ clone sạch chạy được smoke; commit được ghi lại |
| **TV2** | Source & Memory Lead: dữ liệu RGB8/depth uint16, seed, pacing, slot ownership, process spawn | Hàm `producer`, mô tả nguồn và memory ownership | TV1 | Đúng dtype/shape, đủ scheduled accounting, không ghi đè frame chưa trả |
| **TV3** | Metrics Lead: đếm frame, timestamps, latency, throughput, CPU/RAM, CSV/plot | Phần consumer/logger trong `bench.py`, `plot.py` | TV4 | Bảng metric có đơn vị, accounting OK, tổng hợp theo run |
| **TV4** | Research & Protocol Lead: đọc nguồn, chốt matrix trước kết quả, phân biệt claim và proxy, decision/interface | methodology, references, limitations, bảng thí nghiệm | TV3 | Thí nghiệm đổi một biến có chủ đích; paper/repo khác số tự đo |
| **TV5** | QA & Experiment Lead: runner, timeout, failure, chạy lần lặp, log, cleanup, clone sạch | `suite.py`, QA log, evidence index, VLearn checklist | TV2 | 36 run matrix + 18 run failure hợp lệ hoặc subset ghi rõ; chạy lại được |

**Tất cả:** có commit hoặc PR phản ánh phần đóng góp; viết báo cáo cá nhân; tập pitch; tự nộp VLearn. Việc TV1 merge code không thay thế đóng góp và khả năng giải thích của người khác.

### 3.1. Chia ownership khi dùng code mẫu

Trong buổi đầu TV1 tạo bộ khung từ Phụ lục A rồi khóa điểm xuất phát. Sau đó:

- TV2 sửa/kiểm tra `producer()` và hợp đồng slot; ghi lý do mỗi thay đổi.
- TV3 sửa/kiểm tra `run()`, CSV và `plot.py`; không thay metric đã khóa mà không thông báo.
- TV5 sở hữu `suite.py`, lệnh reproduction và kiểm tra shutdown.
- TV4 sở hữu protocol, references, tiêu chí đánh giá, evidence-to-claim.
- TV1 sở hữu integration, môi trường và README.

Không tạo commit giả chỉ để chia đều. Nếu sử dụng code mẫu này, ghi rõ đã dùng code hỗ trợ và nhóm chịu trách nhiệm hiểu, kiểm tra, điều chỉnh và chạy nó.

### 3.2. Handoff và quản lý một laptop

| Handoff | Bên giao | Bên nhận | Nội dung phải có |
|---|---|---|---|
| H1 | TV4 | TV2, TV3 | Profile, seed, clock, counters, policy, định nghĩa window |
| H2 | TV2 | TV1, TV3 | Metadata contract và quy tắc trả slot |
| H3 | TV3 | TV5 | CSV schema, summary schema, điều kiện run invalid |
| H4 | TV1 | TV5 | Commit đã khóa và một lệnh smoke |
| H5 | TV5 | Cả nhóm | URL/path run, summary, plot, console, config |

Trong lúc đo chỉ một người thao tác laptop. Các thành viên khác đọc/viết trên thiết bị riêng nếu có; nếu nhóm chỉ có duy nhất laptop này thì viết/đọc nguồn trước hoặc sau thời gian đo. Không mở editor nặng, slideshow, trình duyệt nhiều tab và benchmark cùng lúc. Mỗi lượt dùng máy có thời gian và người điều khiển ghi trong nhật ký.

## 4. Timeline chuẩn bị theo giờ

**Đề xuất 3 buổi × 3 giờ trước lab.** Đây là lịch tổ chức, không phải yêu cầu thời lượng của giảng viên. Không cố cài môi trường, viết code, đọc paper, đo và viết đủ năm báo cáo từ đầu trong 120 phút.

### Buổi 1 — Hiểu bài toán, repo và khóa protocol (180 phút)

| Phút | Mốc tương đương | Hoạt động | Chủ trì | Đầu ra |
|---:|---|---|---|---|
| 0–15 | 00:00–00:15 | Điền 5 tên/MSV, xác nhận T7 và thiết bị | TV1 | TEAMMATES |
| 15–45 | 00:15–00:45 | Fork, cài Python, venv, Git, kiểm tra cấu hình máy | TV1 + TV5 | Environment log |
| 45–75 | 00:45–01:15 | Đọc producer/data contract và lifetime shared memory | TV2 | Sơ đồ + ownership |
| 75–105 | 01:15–01:45 | Đọc consumer, định nghĩa metric/counters | TV3 | Metric sheet |
| 105–135 | 01:45–02:15 | Đọc tài liệu RealSense và abstract paper | TV4 | Reference notes |
| 135–165 | 02:15–02:45 | Chốt matrix, delay, repeat, seed, memory budget | Cả nhóm | Protocol v1 |
| 165–180 | 02:45–03:00 | Review giới hạn claim và tạo issue từng người | TV5 | Backlog có owner |

### Buổi 2 — Tích hợp code và thử nhanh (180 phút)

| Phút | Hoạt động | Người thực hiện | Mốc kiểm tra |
|---:|---|---|---|
| 0–30 | TV1 tạo skeleton/code mẫu; cả nhóm đọc luồng chạy | TV1 | Import được module |
| 30–60 | Kiểm tra source template và spawn | TV2 | Một camera, đúng payload |
| 60–90 | Kiểm tra đếm frame và CSV | TV3 | Accounting OK |
| 90–115 | Kiểm tra runner và log command | TV5 | Run thất bại không bị bỏ qua |
| 115–140 | Chạy smoke Windows P0 10 s, rồi P1 10 s | TV1 + TV5 | Có CPU/RAM hoặc NA được giải thích |
| 140–165 | Failure nhỏ, FIFO/latest, cleanup Ctrl+C | TV2 + TV3 + TV5 | Latency/drop được hiểu đúng |
| 165–180 | Review thông số, đóng PR, sửa README | TV4 + TV1 | Một commit tích hợp |

### Buổi 3 — Dry run, khóa phiên bản và chuẩn bị trình bày (180 phút)

| Phút | Hoạt động | Người thực hiện | Đầu ra |
|---:|---|---|---|
| 0–25 | Clone sang thư mục sạch, cài bằng lock | TV5 | Reproduction checklist |
| 25–65 | Pilot 1–2 cấu hình tải cao, kiểm tra memory budget | TV5 + TV3 | Chốt 32/16 slots toàn protocol |
| 65–95 | Kiểm tra plot và đơn vị; không chọn chỉ số theo kết quả đẹp | TV3 + TV4 | Plot template |
| 95–120 | Khóa commit/protocol; điền shell báo cáo của năm người | TV1 + cả nhóm | Draft 5 mục/người |
| 120–150 | Chuẩn bị slide, evidence index, đối chiếu rubric | TV4 + TV5 | Slide khung |
| 150–170 | Tập pitch, mỗi người trả lời một câu về metric | Cả nhóm | Pitch 4 phút |
| 170–180 | Chốt người chạy máy và backup lệnh/log | TV1 | Go/no-go lab |

Nếu thiếu thời gian: hoàn thành smoke + matched baseline/failure trước; giảm số cấu hình theo mục 10.5. Không đổi 3 lần lặp thành 1 lần mà vẫn báo cáo có độ ổn định từ nhiều lần chạy.

## 5. Timeline buổi lab 120 phút

Bám giai đoạn trong ảnh: thiết kế/chạy 45–95 phút; failure/decision 95–115 phút; hoàn thiện 115–120 phút, pitch sau đó. Phần cài đặt và viết script đã hoàn thành trước buổi lab.

| Phút | Công việc cụ thể | Người chủ trì | Người phối hợp | Đầu ra tại mốc |
|---:|---|---|---|---|
| 0–10 | Nhắc lại problem, phạm vi software/proxy | TV4 | Cả nhóm | Claim chung |
| 10–20 | Mở repo và giải thích kiến trúc/input/output | TV2 | TV1 | Method có căn cứ |
| 20–30 | Ghi máy, sạc, power mode, version, commit | TV1 | TV5 | Manifest |
| 30–40 | Chốt baseline/error A/error B và metric, seed | TV3 | TV4 | Protocol không đổi |
| 40–45 | Kiểm tra thư mục output mới, tiến trình cũ đã dừng | TV5 | TV1 | Máy sẵn sàng |
| 45–50 | Warm-up 3 s P1, pilot và kiểm tra accounting | TV5 | TV3 | Go/no-go |
| 50–74 | Matrix 12 cấu hình × 3 lần × 30 s | TV5 | TV1 | 36 summary/log |
| 74–87 | Failure: 3 delay × 2 policy × 3 lần × 30 s | TV5 | TV2 | 18 summary/log |
| 87–95 | Tổng hợp CSV/plot, xem per-camera fairness và missing metric | TV3 | TV4 | Bảng kết quả có đơn vị |
| 95–100 | Chọn run failure rõ nhất và baseline cùng cấu hình | TV5 | TV3 | Evidence row |
| 100–105 | Viết quan sát/nguồn/giả thuyết riêng | TV4 | Cả nhóm | Claims đúng phạm vi |
| 105–110 | Quyết định FIFO/latest, đối chiếu drop và latency | TV2 | TV3 | Decision + trade-off |
| 110–115 | Nêu limitation và phép thử tiếp theo | TV1 | TV4 | Limitation cụ thể |
| 115–120 | Điền số vào draft từng người; khóa evidence/commit | Cả nhóm | 5 bản riêng + slide |

**Ngân sách chạy:** matrix 18 phút đo; failure 9 phút đo; tổng 27 phút đo. Cộng 54 lần khởi động process, khoảng nghỉ 2 s/lần, logging và plotting, dự trù 35–40 phút. Đây là ước lượng lịch, không cam kết runtime. Không chia 36 lần lặp thành “12 run trước rồi nếu kịp mới lặp”.

Có thể dùng `suite --set all` chạy tự động theo block ngẫu nhiên; khi đó tên các giai đoạn 50–87 là phân bổ thời gian dự kiến, matrix/failure có thể đan xen. Nếu muốn đúng thứ tự trong bảng, chạy hai suite `matrix` và `failure` riêng.

**Sau lab:** dành khoảng 45–60 phút kiểm tra file cá nhân, tập pitch, xuất PDF/slide nếu cần, kiểm tra link rồi thực hiện 5 lượt nộp. Không xem 115–120 phút là đủ thời gian viết năm báo cáo từ trang trắng.

## 6. Cấu trúc GitHub repo

Tên thư mục/repository: **`K4-Track4-Day04-TenNhom-Sensor-Reality-Sprint`**, thay `TenNhom` bằng tên nhóm không dấu.

Danh sách dưới đây là cấu trúc cần tạo; các file gốc `multicam/` giữ attribution. `bench.py` là bản tích hợp compact cho lớp; có thể tách producer/metrics thành module sau khi đã chạy được, nhưng không cần refactor trong giờ benchmark.

| Đường dẫn | Nội dung | Owner |
|---|---|---|
| `TEAMMATES.md` | Đúng 5 họ tên đầy đủ, MSV, GitHub, vai trò | TV1 |
| `README.md` | Bài toán, scope, install, smoke, suite, evidence, link cá nhân | TV1 |
| `LICENSE` | Giữ license upstream | TV1 |
| `UPSTREAM.md` | URL, commit nguồn, thay đổi so với nguồn | TV4 |
| `pyproject.toml`, `multicam/` | Source/dependency gốc | TV1 |
| `requirements-benchmark.txt` | Dependency benchmark | TV1 |
| `requirements-benchmark-lock.txt` | `pip freeze` sau setup đã chạy được | TV5 |
| `benchmark/__init__.py` | File rỗng để chạy module | TV1 |
| `benchmark/bench.py` | Source/process/shared memory/consumer/metrics | TV2 + TV3 |
| `benchmark/suite.py` | Matrix, repeats, order, log | TV5 |
| `benchmark/plot.py` | Summary, aggregate, plot | TV3 |
| `docs/benchmark_plan.md` | Protocol khóa trước đo | TV4 |
| `docs/methodology.md` | Metric/counters/window/clock | TV3 |
| `docs/references.md` | Nguồn và ghi chú đọc | TV4 |
| `docs/limitations.md` | Giới hạn hardware, workload và measurement | TV4 |
| `docs/environment.txt` | Máy, Windows, CPU/RAM, power mode | TV1 |
| `docs/QA.md` | Smoke, accounting, interrupt, clean clone | TV5 |
| `results/<session>/<run>/` | config, summary, CSV từng run | TV5 |
| `results/<session>/plots/` | PNG từ CSV | TV3 |
| `results/EVIDENCE_INDEX.md` | Claim → run → bảng/plot/lệnh | TV5 |
| `reports/TV1_MSV.md` … `reports/TV5_MSV.md` | 5 bản cá nhân, tên thật trong nội dung | Từng người |
| `slides/pitch.pdf` hoặc `slides/pitch.pptx` | Pitch chung | Cả nhóm |
| `slides/TV1_MSV.pdf` … nếu nộp slide riêng | Bản của đúng người | Từng người |

Mẫu `TEAMMATES.md`:

```markdown
# Thành viên nhóm

| STT | Họ tên đầy đủ | MSV | GitHub | Vai trò |
|---:|---|---|---|---|
| 1 | Điền tên thật | Điền MSV | Điền account | Integration |
| 2 | Điền tên thật | Điền MSV | Điền account | Source & Memory |
| 3 | Điền tên thật | Điền MSV | Điền account | Metrics |
| 4 | Điền tên thật | Điền MSV | Điền account | Research & Protocol |
| 5 | Điền tên thật | Điền MSV | Điền account | QA & Experiment |
```

Thêm vào `.gitignore`:

```gitignore
.venv/
__pycache__/
*.pyc
.pytest_cache/
```

Không ignore toàn bộ `results/`: CSV/config/log/plot là bằng chứng cần nộp. Không lưu toàn bộ raw RGB-D mỗi frame; code chỉ lưu metadata và metric nên tránh repo nặng. Nếu thêm video lớn, sử dụng cách lưu phù hợp và bảo đảm người chấm mở được; không để báo cáo trỏ đến ổ `C:` riêng.

## 7. Branch, commit, PR và đóng phiên bản

### 7.1. Quy tắc branch

`main` giữ phiên bản chạy được. Mỗi nhiệm vụ có branch ngắn, tạo từ `main`; chỉ TV1/owner integration merge sau review.

| Người | Branch đề xuất | Phạm vi |
|---|---|---|
| TV1 | `chore/windows-setup` | Môi trường, skeleton, README |
| TV2 | `feat/synthetic-producer` | Source và lifetime |
| TV3 | `feat/metrics-and-plots` | Counters, logger, plots |
| TV4 | `docs/protocol-and-references` | Thiết kế đo và nguồn |
| TV5 | `test/failure-and-reproduction` | Runner, QA, failure |

Code mẫu gộp producer/logger trong một file. TV2 và TV3 phối hợp merge nối tiếp; không cùng sửa các đoạn giao nhau khi chưa thống nhất. Ưu tiên PR nhỏ, một mục tiêu.

### 7.2. Commit convention

Dạng: **`type(scope): mô tả hành động cụ thể`**. Dùng `feat`, `fix`, `docs`, `test`, `chore`.

Ví dụ:

```text
chore(env): pin benchmark dependencies for Windows setup
feat(source): generate seeded RGB8 and uint16 depth payloads
fix(memory): retain parent handle for shared memory lifetime
feat(metrics): separate drops from unfinished frames
test(qa): verify accounting under slow consumer
docs(protocol): freeze delay levels and run repetitions
```

Không dùng message `update`, `fix all` hoặc mô tả kết quả đo chưa chạy.

### 7.3. Lệnh workflow trên PowerShell

```powershell
git switch main
git pull --ff-only
git switch -c feat/synthetic-producer
# Sửa file thuộc nhiệm vụ.
git add benchmark/bench.py docs/methodology.md
git commit -m "feat(source): add paced synthetic RGB-D producer"
git push -u origin feat/synthetic-producer
```

Tạo PR trên GitHub. PR ghi vấn đề, thay đổi, lệnh kiểm tra, evidence và limitation. Reviewer xem có thay đổi đơn vị/clock/counting hay không, không chỉ xem code có chạy.

Mẫu nội dung PR:

```markdown
Thay đổi: producer tạo RGB8 + uint16 depth theo cấu hình đã khóa.
Kiểm tra: smoke 1 camera và accounting; liên kết config/summary.
Phạm vi: không có camera/USB; không đo acquisition latency.
Ảnh hưởng protocol: không đổi / mô tả cụ thể nếu có đổi.
```

### 7.4. Khóa phiên bản

- Trước chạy: commit hết code và protocol; `git status --short` phải sạch hoặc có giải thích rõ.
- Ghi `git rev-parse HEAD`, dependency lock và environment.
- Sau chạy: commit evidence và report, tạo tag `v1.0-submission`.
- Commit ghi trong `config.json` là **code lúc chạy**, có thể khác commit cuối chứa kết quả. Giữ cả hai để truy vết.
- Nếu sửa bug metric, không ghi đè CSV cũ; tạo session mới, ghi lý do invalidation và đo lại phần bị ảnh hưởng.

```powershell
git rev-parse HEAD
git status --short
# Sau khi chạy, review và commit toàn bộ bằng chứng cần nộp.
git add results docs reports slides
git commit -m "docs(evidence): add verified benchmark results and reports"
git tag v1.0-submission
git push origin main --tags
```

## 8. Cài đặt trên Windows 11

### 8.1. Chuẩn bị

1. Cài Git for Windows và Python **3.11, bản vá từ 3.11.8 trở lên**; kiểm tra có Python launcher `py`. Có thể dùng Python 3.12 nếu nhóm kiểm tra lại, nhưng khóa một phiên bản cho mọi run.
2. Dùng Windows native, PowerShell và `multiprocessing` kiểu `spawn`. Không dùng WSL/Docker cho dataset chính vì thêm lớp môi trường; nếu dùng phải ghi là thí nghiệm khác.
3. Ghi CPU, RAM, GPU, Windows build và chế độ nguồn thật của HP Victus. Chưa biết thông số thì không đoán model CPU/GPU chỉ từ tên laptop.
4. Cắm sạc, giữ một power/thermal mode, đóng tác vụ nặng. Không tắt dịch vụ bảo mật hệ thống để đạt số đẹp.

### 8.2. Fork và clone

Trên GitHub, fork repo gốc và đặt tên fork theo mẫu của lớp. Thêm bốn thành viên còn lại theo chính sách nhóm. Dùng URL repo thật thay `<GITHUB_NHOM>`; không chạy nguyên placeholder.

```powershell
cd C:\Projects
git clone https://github.com/<GITHUB_NHOM>/K4-Track4-Day04-TenNhom-Sensor-Reality-Sprint.git
cd K4-Track4-Day04-TenNhom-Sensor-Reality-Sprint
git remote add upstream https://github.com/mirzafahad/realsense-multicam.git
git remote -v
git rev-parse HEAD
```

Nếu thư mục `C:\Projects` chưa có, tạo trước. Không chạy `reset --hard` lên công việc của nhóm để ép về commit nguồn. Khi cần xem snapshot nguồn, dùng clone riêng hoặc xem link cố định ở mục 2.

### 8.3. Cài môi trường benchmark tối thiểu

Tạo file `requirements-benchmark.txt` bằng nội dung:

```text
numpy==2.3.5
psutil==7.2.2
matplotlib==3.10.8
```

Đây là các phiên bản dùng cho kiểm tra code khi soạn tài liệu. Việc cài wheel trên máy Windows của nhóm vẫn cần smoke test, rồi đóng lock thực tế. Nếu một version không cài được, TV1 chọn version tương thích, ghi thay đổi trong README và khóa lại trước khi đo.

```powershell
py -0p
py -3.11 --version
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements-benchmark.txt
.\.venv\Scripts\python.exe -c "import numpy, psutil, matplotlib; print(numpy.__version__, psutil.__version__, matplotlib.__version__)"
.\.venv\Scripts\python.exe -m pip freeze | Out-File -Encoding utf8 requirements-benchmark-lock.txt
```

Các lệnh sau gọi thẳng Python trong venv, nên không cần đổi PowerShell execution policy chỉ để activate. Python module chạy từ **gốc repo**, không từ bên trong `benchmark/`.

### 8.4. Cài repo gốc để nghiên cứu — tùy chọn

Nếu cần môi trường dependency gốc để kiểm tra import, repo dùng Poetry. Tạo môi trường riêng, tránh trộn lock của benchmark và Poetry:

```powershell
py -3.11 -m venv .venv-upstream
.\.venv-upstream\Scripts\python.exe -m pip install poetry==1.8.5
.\.venv-upstream\Scripts\poetry.exe env use .\.venv-upstream\Scripts\python.exe
.\.venv-upstream\Scripts\poetry.exe install
```

Khi có camera thật và đã thay serial/config đúng, entry point là `python -m multicam` trong môi trường dependency tương ứng. README gốc có dòng `python run -m multicam`; không sao chép dòng đó làm lệnh chuẩn.

**Nhóm hiện chưa có camera nên không lấy việc chạy `multicam` làm điều kiện hoàn thành.** `benchmark.*` chạy độc lập, không import `multicam`, `pyrealsense2`, `numpydantic` hoặc monkey patch.

### 8.5. Tạo script từ tài liệu này

```powershell
New-Item -ItemType Directory -Force benchmark, docs, results, reports, slides
New-Item -ItemType File -Force benchmark\__init__.py
```

Sao chép lần lượt ba khối Python ở Phụ lục A vào đúng `benchmark/bench.py`, `benchmark/suite.py`, `benchmark/plot.py`. Lưu UTF-8, giữ indentation bằng spaces, không lấy dấu mở/đóng khối mã vào file Python.

Kiểm tra syntax:

```powershell
.\.venv\Scripts\python.exe -m py_compile benchmark\bench.py benchmark\suite.py benchmark\plot.py
```

## 9. Chuẩn bị dữ liệu và baseline

### 9.1. Dataset tổng hợp

Mỗi producer tạo một template riêng bằng `np.random.default_rng(seed + camera_id)`:

- Color: `uint8`, shape `(H,W,3)`, ba kênh, 24 bit/pixel.
- Depth: `uint16`, shape `(H,W)`, giá trị mẫu 500–4999; chỉ là dữ liệu payload, **không gắn đơn vị mét/millimét từ cảm biến**.
- Seed mặc định 42. Template tĩnh được tái sử dụng mỗi frame để tách chi phí sinh số ngẫu nhiên khỏi đường truyền phần mềm.
- Mỗi frame vẫn thực hiện copy đầy đủ vào pool và ra consumer. Sequence/timestamp thay đổi qua metadata.
- Không đo nén/decode hoặc tính depth từ ảnh stereo. Không đại diện được tính chất cảnh động hay thuật toán thị giác.

Nguồn này không đòi hỏi dữ liệu riêng tư hay download dataset. `source` trong config và code là mô tả dataset; không ghi UNSW-NB15 hoặc dataset khác của dự án trước vào bài này.

### 9.2. Hai baseline khác nhau, dùng đúng mục đích

**B0 — baseline sanity:** P0, một camera, 5 FPS, FIFO, delay 0, 32 slots, viewer OFF, 30 s. Kiểm tra code và metric. Một run B0 đơn lẻ không thay thế ba repetitions của matrix.

**BF — baseline đối chứng failure:** P2, sáu camera, 30 FPS/camera, FIFO, delay 0, 32 slots, cùng duration/seed. So sánh với BF + 15 ms và BF + 30 ms. Không so lỗi sáu camera HD với baseline một camera 424×240 rồi quy chênh lệch hoàn toàn cho delay.

Ngoài ra có delay 0 cho latest để thấy riêng ảnh hưởng policy khi chưa chủ động làm chậm consumer.

### 9.3. Warm-up và startup

- Trước suite, chạy một warm-up độc lập P1 trong 3 s; thư mục `warmup_*`, không đưa vào thống kê chính.
- Mỗi run thật đợi tất cả producer ready rồi bắt đầu tại một host timestamp chung sau 1s. Thời gian tạo process/template không nằm trong `duration` đo.
- Code mẫu **không có warm-up có tải ngay trong từng cửa sổ run**. Warm-up độc lập không đảm bảo loại bỏ mọi transient; ghi điều này trong limitations.
- Nếu nghiên cứu sâu hơn, thêm warm-up có tải và reset counters vào protocol mới, rồi chạy lại toàn bộ. Không tự bỏ những giây đầu khỏi một vài run sau khi đã nhìn kết quả.

### 9.4. Checklist baseline

- [ ] File config đúng resolution/FPS/N/duration/policy/seed/slots.
- [ ] `summary.status == "ok"`.
- [ ] Tất cả `per_camera.accounting_ok == true`.
- [ ] Có completed frames và latency hữu hạn.
- [ ] FPS dùng đơn vị theo camera hay aggregate đúng nhãn.
- [ ] CPU/RAM monitor thu đủ process; nếu không, NA + lý do.
- [ ] Không còn worker sau khi script thoát; chạy lần kế tiếp được.
- [ ] Không đổi code/power mode giữa các điều kiện.

## 10. Bảng thí nghiệm

### 10.1. Profiles và payload lý thuyết

| Profile | W×H | FPS/camera | Bytes/RGB-D frameset | Payload một camera (Mbps) | Vai trò |
|---|---:|---:|---:|---:|---|
| P0 | 424×240 | 5 | 508.800 | 20,352 | Default sanity theo cấu hình source |
| P1 | 640×480 | 30 | 1.536.000 | 368,640 | Workload trung bình |
| P2 | 1280×720 | 30 | 4.608.000 | 1.105,920 | Workload stress tổng hợp |

Dấu chấm trong cột byte là phân cách hàng nghìn; dấu phẩy trong Mbps là thập phân theo cách viết Việt Nam. CSV/code dùng dấu `.` cho số thập phân. Đây là **preset tổng hợp**, không xác nhận mode màu/depth đồng thời này được mọi model D405/D435 hỗ trợ.

P0→P1 đổi cả resolution và FPS, nên chỉ kết luận về **cấu hình tải kết hợp**. P1→P2 giữ 30 FPS nên phù hợp hơn để khảo sát ảnh hưởng độ phân giải.

### 10.2. Matrix chính — 12 cấu hình × 3 lần = 36 run

Mọi dòng: FIFO, delay 0, 32 slots/camera, 30 s, seed 42, viewer OFF.

| ID | Profile | N | Tổng target FPS | Payload tính toán (Mbps) | Số lần |
|---|---|---:|---:|---:|---:|
| M01 | P0 | 1 | 5 | 20,352 | 3 |
| M02 | P0 | 2 | 10 | 40,704 | 3 |
| M03 | P0 | 4 | 20 | 81,408 | 3 |
| M04 | P0 | 6 | 30 | 122,112 | 3 |
| M05 | P1 | 1 | 30 | 368,640 | 3 |
| M06 | P1 | 2 | 60 | 737,280 | 3 |
| M07 | P1 | 4 | 120 | 1.474,560 | 3 |
| M08 | P1 | 6 | 180 | 2.211,840 | 3 |
| M09 | P2 | 1 | 30 | 1.105,920 | 3 |
| M10 | P2 | 2 | 60 | 2.211,840 | 3 |
| M11 | P2 | 4 | 120 | 4.423,680 | 3 |
| M12 | P2 | 6 | 180 | 6.635,520 | 3 |

Không lấy việc M12 tính hơn 5 Gbps để kết luận USB laptop đã nghẽn: phép thử không đi qua USB và payload ứng dụng có thể khác format trên dây.

### 10.3. Failure và engineering decision — 6 điều kiện × 3 lần = 18 run

Giữ P2, N=6, 30 FPS/camera, duration=30 s, seed=42 và slots=32.

| ID | Policy | Delay/frameset | Mục đích | Dự đoán cần kiểm chứng |
|---|---|---:|---|---|
| F0 | FIFO | 0 ms | Baseline failure | Không chủ động làm chậm |
| F1 | FIFO | 15 ms | Lỗi A | Consumer có thể không theo kịp tổng 180 FPS |
| F2 | FIFO | 30 ms | Lỗi B | Backlog và latency lớn hơn |
| I0 | Latest | 0 ms | Đối chứng policy | Xem policy có làm bỏ frame khi không delay |
| I1 | Latest | 15 ms | Kiểm tra cải tiến ở lỗi A | Giảm tuổi frame nhưng tăng bỏ qua frame cũ |
| I2 | Latest | 30 ms | Kiểm tra cải tiến ở lỗi B | Giữ độ mới dù throughput còn thấp |

Những dự đoán này không phải số đo có sẵn. Nếu baseline đã quá tải, vẫn ghi đúng và so sánh định lượng thay vì gọi baseline là cấu hình “ổn định” theo ý muốn.

### 10.4. Mẫu bảng kết quả — điền sau đo

| Run/condition | FPS camera chậm nhất | Aggregate FPS | P95 latency (ms) | Explicit drop (%) | Deadline miss (%) | Backlog cuối | CPU (%) | RSS sum (MB) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| F0, mean ± SD của 3 run | Chưa đo | Chưa đo | Chưa đo | Chưa đo | Chưa đo | Chưa đo | Chưa đo | Chưa đo |
| F1 | Chưa đo | Chưa đo | Chưa đo | Chưa đo | Chưa đo | Chưa đo | Chưa đo | Chưa đo |
| F2 | Chưa đo | Chưa đo | Chưa đo | Chưa đo | Chưa đo | Chưa đo | Chưa đo | Chưa đo |
| I1 | Chưa đo | Chưa đo | Chưa đo | Chưa đo | Chưa đo | Chưa đo | Chưa đo | Chưa đo |
| I2 | Chưa đo | Chưa đo | Chưa đo | Chưa đo | Chưa đo | Chưa đo | Chưa đo | Chưa đo |

P95 trong bảng tổng hợp là **mean ± SD của P95 tính riêng từng run**, không phải percentile của mọi frame ghép chung.

### 10.5. Phương án tối thiểu nếu lịch/máy không đủ

Ưu tiên một protocol nhỏ hoàn chỉnh:

- P1 và P2, N=1 và 6, mỗi cấu hình 3 lần: 12 run.
- P2 N=6 FIFO delay 0/15/30 ms, 3 lần: 9 run.
- Latest delay 15/30 ms cùng điều kiện, 3 lần: 6 run.
- Tổng 27 run, 13,5 phút đo thuần, có thể tận dụng baseline đúng cấu hình đã đo nếu version/protocol giống nhau và giải thích việc tái dùng.

Ghi rõ chỉ làm subset; không nói đã hoàn thành đủ matrix 12 cấu hình. Chạy từng lệnh `bench` có tên run/rep rõ ràng, vì runner mặc định sinh full set.

Mở rộng nếu có thời gian: thêm 424×240 @30 FPS để tách yếu tố FPS khỏi resolution; hoặc thử N=8 synthetic. Đây không phải phần bắt buộc để hoàn thành tối thiểu.

## 11. Metric, công thức và quy tắc đếm frame

### 11.1. Bandwidth/payload

Với hai ảnh cùng resolution và FPS:

\[
S = W H (3+2) = 5WH \quad \text{byte/frameset}
\]

\[
B_{target} = N W H F (24+16) = 40NWHF \quad \text{bit/s}
\]

\[
B_{target,Mbps}=B_{target}/10^6
\]

Tổng quát khi màu/depth khác resolution/FPS:

\[
B_{target}=\sum_{camera}\left(W_cH_cF_c b_c+W_dH_dF_d b_d\right)
\]

Ví dụ P1 một camera: `640×480×30×40 = 368.640.000 bit/s = 368,64 Mbps = 46,08 MB/s`.

**MB** ở đây là 10^6 byte; **MiB** là 2^20 byte. Không chia Mbps cho 1024 để ra MB/s. Số throughput consumer hoàn thành:

\[
Throughput_{completed,MB/s}=C_{window}\times S/(T\times10^6)
\]

Đây là payload của frameset hoàn thành, không phải DRAM bus bandwidth. Có cả copy producer/consumer và hoạt động khác nên lưu lượng vật lý trong bộ nhớ không bằng con số này. Cũng không phải USB bandwidth: format màu trên dây có thể khác RGB8 ở API [R2].

### 11.2. Các bộ đếm

Một frameset = một ảnh RGB + một depth của một virtual camera. Sáu camera @30 FPS tương đương **180 frameset/s**, không phải 30 frame/s tổng.

| Ký hiệu / field | Định nghĩa |
|---|---|
| `scheduled` | Số slot thời gian dự kiến mỗi camera: `round(F×T)` |
| `schedule_missed` | Slot bị bỏ vì producer trễ ≥ một chu kỳ hoặc đã hết window |
| `attempted` | Slot producer thực sự thử tạo/đưa vào pipeline |
| `enqueued` | Payload copy xong trong window và metadata đã enqueue |
| `rejected` | Attempt không được tiếp nhận vì không có slot hoặc copy xong quá hạn |
| `completed` | Consumer hoàn thành trước thời điểm kết thúc window |
| `stale` | Frame đã enqueue nhưng bị latest bỏ để giữ frame mới hơn |
| `late_completion` | Consumer đã bắt đầu xử lý nhưng kết thúc sau window |
| `shutdown_backlog` | Frame đã enqueue còn tồn khi kết thúc, được dọn lúc shutdown |

Ba đẳng thức phải đúng sau shutdown bình thường, cho từng camera:

```text
scheduled = attempted + schedule_missed
attempted = enqueued + rejected
enqueued = completed + stale + late_completion + shutdown_backlog
```

Nếu không đúng: run `invalid`, điều tra nguồn/cleanup/counting trước khi dùng số. Partial run bị Ctrl+C được đánh dấu invalid, không dùng để thống kê cùng run đủ 30 s.

### 11.3. Metric bắt buộc

| Metric | Công thức / cách tính | Đơn vị | Cách đọc |
|---|---|---|---|
| Achieved FPS mỗi camera | `completed_camera / T` | FPS | So với target FPS/camera |
| Aggregate FPS | `sum(completed) / T` | frameset/s | Không nhầm với FPS một camera |
| Min-camera FPS | `min(completed_camera) / T` | FPS | Phát hiện camera bị đói tài nguyên |
| Completion ratio | `sum(completed) / sum(scheduled)` | 0–1 | Mức đáp ứng tải trong window |
| Explicit software drop | `(rejected + stale) / scheduled ×100` | % | Drop/reject có định nghĩa cụ thể |
| Deadline miss | `schedule_missed / scheduled ×100` | % | Producer không giữ nhịp |
| Backlog cuối | `shutdown_backlog + late_completion` | frameset | Frame chưa hoàn thành đúng window |
| Backlog sample proxy | `enqueued_so_far-completed-stale-late` | frameset | Xấp xỉ frame chưa xử lý, gồm inflight; lấy mẫu 0,5 s |
| Latency | `t_finish - t_capture` | ms | Từ bắt đầu copy nguồn đến xong consumer |
| Latency mean/P95 | Mean / percentile95 của latency completed trong window | ms | Thấp hơn tốt cho độ mới dữ liệu |
| Queue wait P95 | `t_receive - t_enqueue` | ms | Chờ/IPC sau producer copy |
| Consumer copy P95 | `t_copy_done-t_receive` | ms | Chi phí copy tại consumer |
| Target payload | Công thức trên | Mbps | Ước lượng từ cấu hình |
| Completed payload | `completed×S/T/10^6` | MB/s | Lượng payload hoàn thành |
| CPU normalized | Tổng process CPU% / logical CPU count | % tổng CPU logic | Khác process CPU có thể vượt100% |
| System CPU | `psutil.cpu_percent` | % toàn hệ thống | Có cả tác vụ ngoài benchmark |
| RSS sum / working set sum | Tổng `memory_info().rss` parent + producer | MB | Có thể đếm shared pages nhiều lần |
| Pool size | `N×slots×S` | MB | Dung lượng logic cấp sẵn |
| GPU | NA hoặc dữ liệu log riêng | %/MB | Không gán 0 khi chưa đo |

Không đưa `1-completion_ratio` dưới tên “USB drop rate”. Tỷ lệ chưa hoàn thành gồm schedule miss, explicit drop và tồn đọng; code giữ chúng tách biệt.

### 11.4. Đồng hồ và giới hạn latency

`t_capture` là host timestamp ngay trước producer copy template. `t_enqueue` ngay sau copy và trước `Queue.put`. `t_receive` sau consumer lấy metadata; `t_finish` sau copy consumer + delay.

Metric này có serialization/scheduling/copy trong pipeline, **không bao gồm** sensor exposure, ASIC, USB, SDK acquisition hoặc màn hình. Trường `time.perf_counter` không phải thời gian lịch để so giữa hai máy; dùng cùng host trong một run. UTC trong config chỉ để ghi nhật ký.

Latency chỉ tính frame hoàn thành, nên có **survivorship bias** khi nhiều frame bị drop/tồn đọng. Luôn trình bày latency cạnh completion/drop/backlog, không dùng latency thấp riêng lẻ để nói pipeline tốt hơn toàn diện.

### 11.5. Quy tắc thống kê và tiêu chí chọn cấu hình

- 3 repetitions độc lập; block theo repetition, thứ tự trong block random theo seed.
- Mean ± sample SD giữa các run; không gọi SD là confidence interval.
- Per-camera log để kiểm tra phân bổ công bằng; giữ min-camera FPS bên cạnh aggregate.
- Không ghép các frames thành hàng nghìn “lần lặp độc lập” để phóng đại độ chắc chắn.
- Quy ước thử nghiệm nội bộ trước khi đo: mọi camera ≥95% target; completion ratio ≥95%; P95 latency ≤ `max(100 ms, 2 chu kỳ frame)`; không invalid; CPU còn khoảng dự phòng do nhóm đặt.
- Ngưỡng trên là **SLO nhóm đề xuất cho bài thực hành**, không phải chuẩn an toàn robot hoặc thông số RealSense. Nếu task thật cần deadline khác, giải thích và khóa tiêu chí trước khi chạy.
- Có thể không có cấu hình thỏa mọi ngưỡng. Báo cáo đúng và đề xuất giảm FPS/resolution hoặc tăng năng lực consumer.

## 12. Lệnh chạy benchmark

Mọi lệnh ở gốc repo, dùng venv. Mỗi `--out`/`--root` phải mới; code cố tình từ chối ghi đè thư mục cũ. Đặt suffix ngày/giờ nếu chạy lại.

### 12.1. Smoke test Windows trước benchmark

```powershell
.\.venv\Scripts\python.exe -m benchmark.bench --cameras 1 --width 424 --height 240 --fps 5 --duration 10 --out results/smoke_p0_01
Get-Content results/smoke_p0_01/summary.json
Get-Content results/smoke_p0_01/per_camera.csv
```

Kiểm tra FPS gần target và accounting đúng. Nếu thấp, xem scheduler, CPU/background, process exception trước khi nâng tải.

```powershell
.\.venv\Scripts\python.exe -m benchmark.bench --cameras 2 --width 640 --height 480 --fps 30 --duration 10 --out results/smoke_p1_01
```

### 12.2. Warm-up độc lập, không đưa vào main result

```powershell
.\.venv\Scripts\python.exe -m benchmark.bench --cameras 2 --width 640 --height 480 --fps 30 --duration 3 --out results/warmup_01
```

### 12.3. Baseline sanity 30 s có log

```powershell
.\.venv\Scripts\python.exe -m benchmark.bench --cameras 1 --width 424 --height 240 --fps 5 --duration 30 --slots 32 --seed 42 --out results/baseline_b0_01 2>&1 | Tee-Object -FilePath results/baseline_b0_01.console.log
```

Sau pipeline `Tee-Object`, kiểm tra `$LASTEXITCODE` hoặc `summary.status`; không xem việc xuất hiện console log là bằng chứng run thành công.

### 12.4. Chạy đầy đủ theo một suite

```powershell
.\.venv\Scripts\python.exe -m benchmark.suite --set all --duration 30 --repeats 3 --seed 42 --slots 32 --root results/session_full_01
.\.venv\Scripts\python.exe -m benchmark.plot --root results/session_full_01
```

Suite `all` có 54 run; order trong file JSON. Lưu console/error của từng run. Nếu gặp run invalid/timeout, dừng để điều tra; không im lặng bỏ run lỗi rồi tính trung bình những run còn tốt.

### 12.5. Chạy đúng hai giai đoạn của timeline

```powershell
.\.venv\Scripts\python.exe -m benchmark.suite --set matrix --root results/session_matrix_01
.\.venv\Scripts\python.exe -m benchmark.plot --root results/session_matrix_01
.\.venv\Scripts\python.exe -m benchmark.suite --set failure --root results/session_failure_01
.\.venv\Scripts\python.exe -m benchmark.plot --root results/session_failure_01
```

Mặc định duration30/repeats3/seed 42/slots 32. Không chạy `all` rồi chạy thêm matrix/failure nếu không có lý do; hai lựa chọn trên thay thế nhau.

### 12.6. Memory budget và fallback

Ở N=6, pool 32 slot/camera:

| Profile | Pool logic |
|---|---:|
| P0 | 97,6896 MB |
| P1 | 294,912 MB |
| P2 | 884,736 MB |

Ngoài pool còn template, bản copy consumer, metadata, Python và Windows. Script từ chối pool vượt min(1,5 GB, 35% available RAM). Đây là guard thực thi, không chứng minh tổng RAM chắc chắn đủ.

Nếu guard chặn P2: trước dataset chính, khóa **slots 16 cho toàn bộ matrix và failure**, sửa protocol và ghi lý do; dùng `--slots 16` với suite. Không giảm slot chỉ cho latest rồi coi chênh lệch hoàn toàn do policy. Nếu đã có dataset chính slots 32, bộ slots 16 là session khác, không trộn trực tiếp.

## 13. Gây lỗi/nghẽn và kiểm tra cải tiến

### 13.1. Controlled failure

Delay đặt tại consumer **cho mỗi frameset của một camera**. 6 camera @ 30 tạo target tổng 180 frameset/s. Nếu delay là15 ms thì riêng delay đã giới hạn khoảng66,7 frameset/s; nếu30 ms thì khoảng33,3 frameset/s, trước các overhead khác.

\[
\mu_{delay}\leq\frac{1000}{delay_{ms}}\quad \text{frameset/s, khi delay >0}
\]

\[
\lambda=N F=180\quad \text{frameset/s}
\]

Khi `λ > μ`, lượng chưa xử lý tăng cho tới khi pool hết slot, producer bị reject. Với32 slots/camera, giới hạn tổng192 slot; không thể backlog tăng vô hạn. Đây là nghẽn **software consumer**, không phải bằng chứng USB bão hòa.

### 13.2. Ba lệnh đối chứng trực tiếp

```powershell
.\.venv\Scripts\python.exe -m benchmark.bench --cameras 6 --width 1280 --height 720 --fps 30 --duration 30 --slots 32 --delay-ms 0 --policy fifo --out results/manual_F0_r1
.\.venv\Scripts\python.exe -m benchmark.bench --cameras 6 --width 1280 --height 720 --fps 30 --duration 30 --slots 32 --delay-ms 15 --policy fifo --out results/manual_F1_r1
.\.venv\Scripts\python.exe -m benchmark.bench --cameras 6 --width 1280 --height 720 --fps 30 --duration 30 --slots 32 --delay-ms 30 --policy fifo --out results/manual_F2_r1
```

Các lệnh này là demo/rerun riêng; suite đã tự chạy đủ repetition. Nếu dùng thay suite, đổi suffix r1/r2/r3, randomize thứ tự và lưu console/command.

### 13.3. Cải tiến latest

```powershell
.\.venv\Scripts\python.exe -m benchmark.bench --cameras 6 --width 1280 --height 720 --fps 30 --duration 30 --slots 32 --delay-ms 15 --policy latest --out results/manual_I1_r1
.\.venv\Scripts\python.exe -m benchmark.bench --cameras 6 --width 1280 --height 720 --fps 30 --duration 30 --slots 32 --delay-ms 30 --policy latest --out results/manual_I2_r1
```

Latest trong script là **giữ newest per-camera trong batch queue**, không đảm bảo luôn lấy frame mới nhất tuyệt đối ngay khi processing bắt đầu. Có thể có frame tới sau batch drain. Ghi đúng mức bảo đảm này.

Chấp nhận cải tiến khi latency giảm có bằng chứng, không có camera bị starvation bất thường và trade-off drop được mô tả. Không yêu cầu FPS trở lại180 vì consumer delay vẫn như cũ.

### 13.4. Secondary failure: shutdown/exception

TV5 chạy một run dài, nhấn Ctrl+C giữa chừng, rồi:

1. Xem summary/console đánh dấu invalid.
2. Task Manager kiểm tra producer đã thoát; không kết thúc tất cả Python trên máy nếu có chương trình khác.
3. Chạy một smoke mới với output mới để kiểm tra tài nguyên còn dùng được.
4. Ghi version, thời điểm interrupt, traceback và hành vi cleanup trong QA.

Script dùng `finally`, stop event, join và close/unlink. Kill cưỡng bức toàn process tree có thể bỏ qua cleanup; đây là limitation phải báo, không hứa mọi cách kill đều sạch. Với Windows, kernel giải phóng named mapping khi mọi handle đóng [R3].

## 14. Lưu log, tạo plot và truy vết

### 14.1. File tạo ra

| File | Chứa gì | Dùng ở đâu |
|---|---|---|
| `config.json` | Tham số, seed, source, Python/OS, RAM/CPU count, commit, dirty state, clock, GPU NA | Reproduction, method |
| `summary.json` | Metric cấp run, status, per-camera và error nếu có | Bảng chính |
| `per_camera.csv` | Scheduled/attempted/enqueued/drop/stale/completed/backlog/FPS mỗi camera | Accounting, fairness |
| `frames.csv` | Metadata/status từng frame được enqueue, latency với completed | Phân tích latency và frame lifecycle |
| `resources.csv` | Mẫu CPU/system CPU/RSS/backlog mỗi khoảng0,5 s | Plot thời gian |
| `<run>.console.log` | stdout+stderr run trong suite | Debug, bằng chứng chạy |
| `<run>.command.json` | Danh sách argument chính xác | Lặp lại |
| `order.json` | Trình tự điều kiện, repetitions | Kiểm tra thiết kế đo |
| `summary.csv` | Một hàng/run | Bảng tổng hợp |
| `aggregate.csv` | Mean/SD/n_runs theo cấu hình/policy và family | So sánh repeats |
| `plots/*.png` | FPS/latency/drop và policy/backlog | Báo cáo/slide |

Rejected/schedule-missed chưa có payload nên chỉ được đếm aggregate theo camera, không có từng row `frames.csv`. Không dùng số dòng frames.csv làm số scheduled.

### 14.2. Plot cần dùng

1. **FPS vs N:** trụcX số virtual camera; trụcY FPS camera chậm nhất; legend resolution/FPS. Không chỉ plot aggregate vốn có thể tăng dù từng camera chậm.
2. **Latency P95 vs N:** error bar là SD của các P95/run, ghi n=3.
3. **Explicit drop vs N:** nhãn software drop, không gọi hardware drop.
4. **FIFO/latest vs consumer delay:** hai panel latency và drop; cùng pool.
5. **Backlog vs elapsed:** chọn r1 các điều kiện failure làm evidence diễn tiến.
6. **CPU/RAM:** có dữ liệu CSV; nếu cần plot, TV3 bổ sung sau khi xác minh bộ đo. Không vẽ missing CPU=0.

Plot từ script có nhãn synthetic/software. Đặt baseline, đơn vị, nguồn và commit trong caption báo cáo. Mở PNG kiểm tra chữ không bị cắt và điều kiện legend đúng; ảnh lỗi/thiếu dữ liệu phải sửa trước nộp.

### 14.3. Manifest môi trường thủ công

```powershell
Get-CimInstance Win32_Processor | Select-Object Name,NumberOfCores,NumberOfLogicalProcessors | Out-File -Encoding utf8 docs/cpu.txt
Get-CimInstance Win32_ComputerSystem | Select-Object Model,TotalPhysicalMemory | Out-File -Encoding utf8 docs/machine.txt
Get-CimInstance Win32_OperatingSystem | Select-Object Caption,Version,BuildNumber | Out-File -Encoding utf8 docs/windows.txt
Get-CimInstance Win32_VideoController | Select-Object Name,DriverVersion | Out-File -Encoding utf8 docs/gpu.txt
git rev-parse HEAD | Out-File -Encoding utf8 docs/benchmark-code-commit.txt
```

`docs/environment.txt` ghi thêm: cắm sạc, Windows power mode, HP thermal mode nếu có, tác vụ nền đã đóng, màn hình/viewer OFF, người chạy và thời điểm. Không cần xuất serial máy hoặc hostname cá nhân để chứng minh cấu hình.

### 14.4. GPU nếu có NVIDIA và nhóm cần đo bổ sung

Trong terminal riêng, nếu `nvidia-smi` hoạt động:

```powershell
nvidia-smi --query-gpu=timestamp,name,utilization.gpu,memory.used --format=csv -l 1 > results/gpu_session_01.csv
```

Dừng logging bằng Ctrl+C sau suite; ghi overhead, thời gian bắt đầu/kết thúc và cách ghép với run. Lệnh này chỉ là lựa chọn đo bổ sung; không giả định mọi HP Victus có cùng GPU hoặc công cụ đó đã được cài. Benchmark mẫu chạy CPU nên GPU thường không phản ánh tải pipeline; chỉ kết luận từ log thực tế.

### 14.5. Evidence index

Mẫu:

```markdown
| Claim | Loại | Điều kiện/run | Bằng chứng | Lệnh/commit |
|---|---|---|---|---|
| Consumer delay làm latency tăng | Nhóm quan sát | F0/F1/F2, r1-r3 | aggregate.csv + backlog plot | command JSON + code commit |
| Latest đánh đổi frame completeness lấy freshness | Nhóm quan sát | F1/I1 hoặc F2/I2 | latency/drop + per-camera | command JSON + code commit |
| Camera thật còn phụ thuộc USB/power/cable | Nguồn | RealSense guide | URL, mục đọc | R2 |
| Cần thử trên camera thật để chọn controller | Đề xuất | Chưa đo | limitations.md | Phép thử tiếp theo |
```

## 15. Phân tích failure case

### 15.1. Chọn một failure chính

Chọn cặp matched baseline và lỗi có khác biệt rõ. Nếu F2 chỉ cho throughput thấp nhưng P95 không tăng nhiều, đọc backlog/drop: pool hữu hạn có thể làm producer reject sớm; không buộc mọi metric phải cùng tăng.

Quy trình:

1. TV5 chỉ rõ run ID, condition, code commit và duration.
2. TV3 lấy scheduled/completed/drop/backlog, kiểm tra accounting.
3. TV3 đối chiếu queue wait P95 với total latency P95 và copy P95 để xem chờ queue hay copy đóng góp lớn.
4. TV4 tách nguyên nhân do **delay được cài có chủ đích** và nguyên nhân chưa đo được như OS scheduling/CPU/thermal.
5. TV2 đối chiếu latest cùng delay/capacity để xem có giảm độ trễ và thay đổi tính đầy đủ của frame.
6. Cả nhóm viết limitation: chưa chạy detector/SLAM, chưa xác minh tác động đến chất lượng tác vụ.

### 15.2. Mẫu đoạn báo cáo có chỗ điền

> **Nhóm quan sát được:** Với [N, W×H, FPS, policy, slots], tăng consumer delay từ [x] lên [y] ms làm P95 latency đổi từ [a] sang [b] ms, completion ratio từ [c] sang [d] và backlog cuối từ [e] sang [f]. Bằng chứng: [run IDs, CSV/plot].
>
> **Nguồn cho biết:** Tài liệu RealSense mô tả bandwidth, CPU, nguồn điện, cabling và buffering là các yếu tố cần xem xét khi chạy nhiều camera [R2]. Kết quả này không có cùng môi trường với benchmark tổng hợp của nhóm.
>
> **Suy luận kỹ thuật:** Dữ liệu nhận muộn có thể làm robot phản ứng dựa trên cảnh cũ. Nhóm chưa chạy chức năng điều khiển/nhận diện nên chưa đo mức ảnh hưởng đến độ chính xác hoặc an toàn.
>
> **Quyết định:** Với tác vụ ưu tiên độ mới, dùng latest [nếu số đo ủng hộ]; với recording đầy đủ, chọn giảm tải hoặc tăng consumer thay vì bỏ frame. Phép kiểm tra tiếp theo: [condition/metric cụ thể].

Không để các placeholder này trong bản nộp; nếu chưa đo thì ghi “chưa đo” và không tạo số giả.

### 15.3. Ma trận diễn giải

| Quan sát | Có thể giải thích | Cần xem thêm | Không được suy ra ngay |
|---|---|---|---|
| FPS thấp, deadline miss cao, queue nhỏ | Producer/scheduler có thể hạn chế nguồn | Attempt/enqueue, CPU, copy | USB bị nghẽn |
| FPS thấp, queue wait/backlog cao | Consumer không theo kịp | Delay và copy cost | Camera sensor hỏng |
| Latest P95 thấp, drop cao | Bỏ frame cũ để giữ freshness | Min-camera FPS, completion | Toàn bộ hệ thống tốt hơn mọi mặt |
| RSS sum cao | Pool/copy/process làm tăng working set | Pool size, private memory nếu có | RAM vật lý duy nhất bằng RSS sum |
| Không thấy suy giảm khi N tăng | Máy đủ cho workload đã thử | Tải cao hơn, viewer/AI riêng | Scale vô hạn hoặc đủ cho camera thật |

## 16. Engineering decision và phác thảo 4–8 camera

### 16.1. Decision record phải điền sau đo

Tạo `docs/decision.md` theo mẫu:

```markdown
# Quyết định xử lý nhiều luồng

Bối cảnh: robot cần [freshness / recording completeness], chưa có camera thật.
Điều kiện đã đo: [profile, N, policy, delay, slots, commit].
Bằng chứng: [CSV và plot, n=3].
Lựa chọn: [FIFO / latest / giảm tải].
Lý do: [latency/drop/completion/CPU phù hợp mục tiêu nào].
Đánh đổi: [frame bỏ qua, RAM, fairness, throughput].
Giới hạn: [synthetic, không USB/AI/physical sensor].
Kiểm tra tiếp: [mượn hardware, mode thật, controller, clock, tác vụ].
```

### 16.2. Chọn policy theo tác vụ

| Tác vụ | Lựa chọn có căn cứ | Điều kiện/đánh đổi |
|---|---|---|
| Live preview/robot cần cảnh mới | Latest per-camera có drop metric | Chấp nhận frame không đầy đủ; kiểm tra starvation |
| Ghi dữ liệu đầy đủ cho offline | FIFO + tốc độ nguồn phù hợp consumer | Không tăng queue vô hạn để che backlog |
| Producer không giữ target FPS | Giảm tải/giảm chi phí nguồn | Latest không sửa được mọi source deadline miss |
| Cần đồng bộ hình học nhiều camera | Thêm sync/frame alignment riêng | Latest độc lập chưa đảm bảo timestamp alignment |

### 16.3. Phác thảo sensor stack với compute budget cố định

Đây là phương án phân tích cho phần mở rộng T7, **không phải cấu hình đã kiểm chứng phần cứng**.

| Phương án | Cấu hình payload tổng hợp | Raw application payload | Sự đánh đổi cần kiểm tra |
|---|---|---:|---|
| A: 4 luồng | 4×640×480×30, RGB8+uint16 | 1.474,56 Mbps | Chi tiết ảnh cao hơn phương án B; số góc nhìn ít hơn |
| B: 8 luồng | 8×424×240×30, RGB8+uint16 | 976,896 Mbps | Nhiều góc nhìn, độ phân giải thấp; thêm process/sync cost |
| C: 8 luồng FPS thấp | 8×640×480×15, RGB8+uint16 | 1.474,56 Mbps | Cùng payload A nhưng update chậm, nhiều process |

Cùng payload không có nghĩa cùng CPU, latency hoặc chất lượng perception. Không ngoại suy kết quả N=6 thành số đo N=8. Nếu chưa chạy N=8, bảng là thiết kế đề xuất.

Đề xuất interface dựa trên điều kiện cần kiểm tra:

- USB: triển khai thuận tiện cho camera SDK, nhưng phải xem controller topology, mode on-wire, power/hub/cable; nhiều cổng không chứng minh nhiều controller độc lập [R2].
- GigE/USB3 Vision/CSI/GMSL2: chỉ đưa vào phần so sánh tương lai nếu nhóm đọc datasheet/standard tương ứng. Không tính “RGB8 app payload ≤ tốc độ danh nghĩa” rồi khẳng định interface đáp ứng thực tế.
- Chưa có ngân sách/phần cứng cụ thể: ưu tiên mượn/thử camera thay vì đưa khuyến nghị mua model hoặc controller đã được chứng minh.
- Trên cùng laptop, chọn cấu hình thấp hơn điểm suy giảm đo được và để dự phòng cho xử lý thực; không dùng toàn bộ budget chỉ cho copy pipeline.

**Kết quả tối thiểu cần trình bày:** một bảng cấu hình so với FPS/latency/drop, một failure và một khuyến nghị interface có điều kiện, ghi rõ phép kiểm chứng phần cứng tiếp theo.

## 17. Paper, tài liệu và kế hoạch đọc

Ngày đối chiếu nguồn: **05/10/2026**. Repo và tài liệu kỹ thuật không tự động trở thành peer-reviewed paper. Các tóm tắt paper dưới đây được đối chiếu từ trang abstract/bibliographic metadata; nhóm nên đọc toàn văn phần liên quan trước khi trích kết quả chi tiết hoặc số liệu.

| ID | Nguồn chính | Dùng trong bài | Giới hạn sử dụng |
|---|---|---|---|
| R1 | Fahad Mirza, `realsense-multicam`, commit ở mục2 | Method kiến trúc/process/queue/shared memory | FPS tác giả là số nguồn trên Jetson/D405 |
| R2 | RealSense, *Multi-Camera configurations – D400 Series Stereo Cameras* | Bandwidth, format, power, CPU, cable, buffering | Tài liệu hardware khác benchmark synthetic; kiểm tra unit nếu trích số |
| R3 | Python 3.11, `multiprocessing.shared_memory` | Ownership, close/unlink, Windows lifetime | Không khái quát hành vi POSIX sang Windows |
| R4 | Python 3.11, `multiprocessing` | Spawn, main guard, queue/process cleanup | Tránh dùng `qsize/empty` làm truth |
| P1 | Keselman, Woodfill, Grunnet-Jepsen, Bhowmik (2017), *Intel RealSense Stereoscopic Depth Cameras*, arXiv:1705.05548 | Cơ sở RGB-D/stereo, đặc tính và giới hạn cảm biến | Không cung cấp throughput proxy của laptop nhóm |
| P2 | Guo et al. (2023), *DeepStream: Bandwidth Efficient Multi-Camera Video Streaming for Deep Learning Analytics*, arXiv:2306.15129 | Bối cảnh bandwidth và trade-off nhiều camera | Nghiên cứu streaming/network/analytics; không phải benchmark USB; không nhầm với NVIDIA DeepStream SDK |
| P3, tùy chọn | Rustler, Volprecht, Hoffmann (2025), *Empirical Comparison of Four Stereoscopic Depth Sensing Cameras for Robotics Applications*, arXiv:2501.07421 | Thiết kế đánh giá cảm biến và task-specific limitations | Đánh giá depth quality, không chứng minh số FPS pipeline nhóm |

Links:

- R1: <https://github.com/mirzafahad/realsense-multicam>.
- R2: <https://dev.realsenseai.com/docs/multiple-depth-cameras-configuration/>.
- R3: <https://docs.python.org/3.11/library/multiprocessing.shared_memory.html>.
- R4: <https://docs.python.org/3.11/library/multiprocessing.html>.
- P1: <https://arxiv.org/abs/1705.05548> · PDF: <https://arxiv.org/pdf/1705.05548>.
- P2: <https://arxiv.org/abs/2306.15129> · PDF: <https://arxiv.org/pdf/2306.15129>.
- P3: <https://arxiv.org/abs/2501.07421> · PDF: <https://arxiv.org/pdf/2501.07421>.

### 17.1. Phân công đọc nguồn

- TV1: R1 setup/entrypoint, R4 start method.
- TV2: R1 producer/data contract, R3 lifetime, P1 phần sensor assumptions.
- TV3: R1 consumer, R4 queue, cách đo latency/copy.
- TV4: R2 bandwidth/CPU/power/cable/latency; P1/P2 abstract, method và limitation liên quan.
- TV5: R3 cleanup, R4 queue feeder/shutdown; đối chiếu điều kiện log/reproduction.

Mỗi người ghi bốn dòng: input/output của phương pháp; metric nguồn đo; limitation; điều nhóm sử dụng được. Lưu URL, section/page nếu đọc PDF, version/commit và ngày truy cập. Không copy nguyên đoạn paper dài vào report.

### 17.2. Chú ý khi trích tài liệu RealSense

Tài liệu R2 bàn về format YUYV trên đường truyền trong một số cấu hình, trong khi API có thể trả RGB8. Vì vậy công thức40bit/pixel của nhóm mô tả buffer ứng dụng, không tự động bằng payload USB. Tài liệu này có một chỗ unit bandwidth cần đọc cẩn thận; tự kiểm tra phép nhân/đổi bit-byte trước khi đưa số vào slide. Không lấy một con số giới hạn bus làm capacity guarantee cho mọi máy.

## 18. Bố cục 5 báo cáo cá nhân

Ảnh hướng dẫn một trang/slide ngắn theo **năm mục**. Đề xuất mỗi báo cáo 1–2 trang hoặc số trang giảng viên yêu cầu; chưa có yêu cầu khác thì dùng một trang nội dung chính + link evidence. Không tự tạo yêu cầu số trang bắt buộc.

### 18.1. Khung chung cho mọi người

Đầu trang: họ tên/MSV, T7, nhóm, repo URL, code commit, hardware, nguồn tổng hợp. Sau đó:

1. **Problem:** robot/tác vụ, input RGB-D, failure cần khảo sát, phạm vi không hardware.
2. **Method:** repo/paper, kiến trúc, nguồn tổng hợp, slot ownership, policy và giả định.
3. **Benchmark:** baseline/error, profile/N/FPS/duration/repeats, metric/unit, một bảng hoặc plot có số thật và linkCSV.
4. **Failure case:** một điều kiện rõ, metric thay đổi, quan sát so với suy luận, limitation.
5. **Engineering decision:** chọn thay đổi/rollback/fallback, trade-off, phép kiểm tra tiếp theo.

Cuối trang: đóng góp cá nhân và nguồn/lệnh. Dùng dữ liệu nhóm chung, viết lời giải thích của mình; không tách người này chỉ có Problem còn người kia chỉ có Method. **Mỗi bản riêng đều đủ năm mục.**

### 18.2. Trọng tâm riêng của từng người

| Người | Problem | Method | Benchmark | Failure case | Decision |
|---|---|---|---|---|---|
| TV1 | Triển khai pipeline trên laptop giới hạn | Windows spawn/dependency/entrypoint | Environment, reproducibility + một bảng chung | Cấu hình/code không đúng hoặc run invalid | Khóa version/giảm tải theo máy |
| TV2 | Nhiều nguồn cạnh tranh slot/copy | Template dtype, pacing, ownership | Per-camera count/FPS + bảng chung | Producer reject khi pool hết | Pool hữu hạn, lifetime rõ, latest theo mục tiêu |
| TV3 | Metric dễ bị hiểu nhầm | Window/clock/accounting/P95 | FPS/latency/drop/CPU và SD | Backlog khác drop; latency bias | Đo đầy đủ lifecycle trước kết luận |
| TV4 | T7 từ bandwidth đến robot freshness | Repo vs docs/paper; proxy/raw payload | Matrix và so sánh có đối chứng | Suy luận USB không được đo | Interface proposal có điều kiện |
| TV5 | Kết quả có tái lập không | Runner/order/repeats/log/shutdown | Reproduction run + failure | Slow consumer/interrupt và evidence | Chọn policy qua matched test, checklist QA |

Nếu secondary failure của TV1/TV5 chưa thực sự chạy, họ dùng cùng failure chính của nhóm và giải thích từ góc nhìn riêng; không bịa một case để làm khác báo cáo.

### 18.3. Mẫu báo cáo cá nhân

```markdown
# T7 — Họ tên, MSV

Nhóm: ... | Vai trò: ... | Repo: ... | Code commit: ...
Thiết bị: HP Victus 16, Windows 11; RGB-D tổng hợp, chưa có camera.

## Problem
[Tác vụ, failure, phạm vi cần trả lời.]

## Method
[Repo/paper, input/output, process/shared memory/queue và giả định.]

## Benchmark
[Baseline và lỗi; config, seed, T, n=3; metric/đơn vị.]
[Bảng/plot với số đo, link CSV/config/lệnh.]

## Failure case
[Nhóm quan sát ...; nguồn cho biết ...; giả thuyết ...; limitation ...]

## Engineering decision
[Lựa chọn, metric ủng hộ, trade-off, phép thử tiếp.]

Đóng góp cá nhân: ...
Nguồn: ...
```

Trước nộp, mỗi người phải tự trả lời: frame là gì; drop khác backlog ra sao; latency đo từ điểm nào; vì sao kết quả không chứng minh USB bandwidth; vì sao policy có trade-off.

## 19. Slide pitch 3–5 phút

### 19.1. Bản chuẩn 4 phút, 5 slide

| Slide | Thời gian | Người | Nội dung trên slide | Bằng chứng |
|---|---:|---|---|---|
| 1 — Problem & scope | 0:00–0:35 | TV1 | Robot nhiều luồng, laptop, chưa có hardware, câu hỏi | Một dòng scope |
| 2 — Method | 0:35–1:20 | TV2 | Producer/shared memory/queue/consumer; RGB8+depth; pool/clock | Sơ đồ gọn + commit/source |
| 3 — Benchmark | 1:20–2:20 | TV3 | Profiles, repeats, một plot FPS hoặc latency; bảng quan trọng | CSV link, n=3, đơn vị |
| 4 — Failure | 2:20–3:15 | TV5 | F0/F1/F2: delay ms, backlog và latency; quan sát trực tiếp | Run/log/plot |
| 5 — Decision & limitation | 3:15–4:00 | TV4 | FIFO/latest trade-off, interface có điều kiện, phép thử hardware tiếp | Policy plot + nguồn |

Bản3 phút: 25/30/50/40/35s. Bản5 phút: 40/55/75/65/65s. Không thêm10 slide nếu chỉ có5 phút.

### 19.2. Nội dung lời nói đề xuất

- **TV1:** “Nhóm khảo sát khi nhiều luồng RGB-D vượt khả năng consumer. Hiện chưa có camera nên kết quả là software benchmark, còn bandwidth là payload tính toán.”
- **TV2:** “Mỗi virtual camera là một process. Dữ liệu đi qua pool shared memory do parent giữ, metadata qua queue; timestamp dùng host clock. Đây là biến thể dựa trên repo.”
- **TV3:** Nói các số đã đo, target so với min-camera/aggregate FPS, P95, n=3. Không đọc mọi hàng CSV.
- **TV5:** Nói đúng delay/frameset, cặp matched baseline và lỗi; chỉ vào backlog/drop khác nhau.
- **TV4:** “Với mục tiêu freshness, [lựa chọn được số đo ủng hộ], đổi lại [drop/completeness]. Chúng tôi chưa đo USB/depth accuracy hoặc tác động lên SLAM; phép thử tiếp theo là [cụ thể].”

Slide ghi link/path ngắn để người chấm tìm evidence. Chuẩn bị sẵn console/config/CSV trong tab hoặc thư mục; không chạy toàn bộ30 phút benchmark khi pitch chỉ4 phút.

### 19.3. Câu hỏi phản biện cần tập

1. Không có camera thì benchmark đo gì và chưa đo gì?
2. Vì sao RGB-D là5 byte/pixel trong phép tính này?
3. Vì sao source gốc có shared memory mà vẫn copy?
4. Delay15 ms trên sáu camera khác delay 15 ms cho một batch sáu ảnh như thế nào?
5. Tại sao latest latency giảm nhưng drop tăng?
6. Backlog cuối có phải dropped frame không?
7. Hai resolution/FPS khác nhau có cho kết luận nhân quả về resolution không?
8. CPU chuẩn hóa và RSS sum có giới hạn gì?
9. Vì sao không kết luận USB 5 Gbps bão hòa từ synthetic payload?
10. Làm sao tái chạy đúng code và điều kiện đã đo?

## 20. Checklist VLearn và điều kiện hoàn thành

### 20.1. Repo chung

- [ ] Tên root/repo theo `K4-Track4-Day04-TenNhom-Sensor-Reality-Sprint`.
- [ ] `TEAMMATES.md` ở gốc, đúng 5 người, họ tên đầy đủ và MSV thật.
- [ ] Source, LICENSE/attribution upstream, commit/source URL.
- [ ] README có cài đặt, smoke, suite, plot, limitation và link evidence.
- [ ] requirements và lock môi trường thật.
- [ ] Có config/lệnh/log/CSV/plot của run hợp lệ; accounting kiểm tra.
- [ ] Có matched baseline + ít nhất lỗiA; lỗiB nếu làm full protocol.
- [ ] Có failure case cụ thể và engineering decision có metric hỗ trợ.
- [ ] Có bảng cấu hình–FPS/latency/drop và recommendation interface có điều kiện.
- [ ] Repo có đủ 5báo cáo/slide riêng với đúng tên/MSV.
- [ ] Báo cáo không chỉ đưa ý tưởng hoặc screenshot, thiếu số đo.
- [ ] Repo link mở được theo quyền người chấm; file report/plot không trỏ vào máy cá nhân.
- [ ] Link cố định code commit/tag và đường dẫn evidence còn hoạt động.

### 20.2. Mỗi người tự nộp

Ảnh quy định **5 lượt nộp riêng**, cùng repo URL và bản riêng đúng người. Chưa có tài khoản/URL assignment/deadline nên tài liệu không tự đặt tên bài hoặc thời hạn nộp.

| Người | Bản riêng trong repo | Repo URL chung | Lượt nộp VLearn | Mở lại sau nộp |
|---|---|---|---|---|
| TV1 | `reports/TV1_2A202602688.md` | CùngURL | Đã nộp | Đã kiểm tra |
| TV2 | `reports/TV2_2A202602978.md` | CùngURL | Đã nộp | Đã kiểm tra |
| TV3 | `reports/TV3_2A202602859.md` | CùngURL | Đã nộp | Đã kiểm tra |
| TV4 | `reports/TV4_2A202602611.md` | CùngURL | Đã nộp | Đã kiểm tra |
| TV5 | `reports/TV5_2A202602615.md` | CùngURL | Đã nộp | Đã kiểm tra |

Mỗi người:

1. Mở đúng assignment của lớp, kiểm tra định dạng/hạn nộp hiển thị.
2. Nộp bản riêng và URL repo chung; nếu form có chỗ ghi chú, thêm link trực tiếp report/evidence.
3. Kiểm tra bản riêng ghi đúng tên/MSV, đủ 5 mục, source/commit/lệnh, metric và limitation.
4. Submit theo giao diện, mở lại lượt nộp, xác nhận file/link đúng và quyền đọc.
5. Ghi xác nhận vào checklist nhóm. Một lượt nộp của trưởng nhóm không thay thế bốn lượt còn lại.

### 20.3. Đối chiếu rubric

| Trọng số | Bằng chứng tối thiểu trước nộp |
|---:|---|
| 40% chạy được | Clean-clone smoke, dataset generation, config/lệnh, CSV và plot |
| 25% failure | Condition cụ thể, baseline/error, số thật, phân biệt quan sát và suy luận |
| 20% method | Input/output, queue/shared memory, counting/clock, repo/paper và limitation |
| 15% trade-off | Policy/completeness/freshness, compute budget, interface có điều kiện |

### 20.4. Definition of Done

Coi bài hoàn thành khi người không tham gia nhóm tìm được: source/version, cách chạy, nguồn tổng hợp, metric, số baseline/lỗi, log/plot, failure, decision, limitations, đúng 5 thành viên và5 bản riêng. Sau đó xác nhận đủ 5 lượt nộp. Có code nhưng chưa chạy không đáp ứng phần demo.

## 21. Xử lý vướng mắc thường gặp

| Vướng mắc | Cách xử lý |
|---|---|
| `py -3.11` không tìm thấy | Xem `py -0p`, cài/đổi sang phiên bản đã kiểm tra, khóa protocol |
| Import `benchmark` không thấy | Chạy ở gốc repo và có `benchmark/__init__.py` |
| Import `pyrealsense2` lỗi | Benchmark không cần; kiểm tra đang chạy nhầm `multicam`/file import |
| Existing output directory | Đổi run/session ID; không xóa bằng chứng cũ để chạy lại |
| Memory guard từ chối | Khóa slot thấp hơn cho toàn thí nghiệm hoặc subset; ghi protocol mới |
| `status=invalid` | Xem console, accounting, worker exit; sửa và run ID mới |
| `NoSuchProcess`/AccessDenied bộ đo | Kiểm tra `resource_monitor_processes` trongconfig; số thiếu làNA, kiểm tra quyền/môi trường |
| CPU/RSS null | Không đổi thành0; run pipeline có thểOK nhưng bộ metric tài nguyên chưa hoàn chỉnh |
| P95 không có | Không có completed frames; dùng completion/backlog để phân tích, không bịa latency |
| Drop rất cao, latency latest thấp | Kiểm tra mọi camera FPS, completeness và survivorship bias |
| Backlog plot gần0 | Có thể consumer đủ nhanh, nguồn bị chậm hoặc latest bỏ stale; xem counters |
| Sau Ctrl+C cònprocess | Kiểm tra đúng process của benchmark, cleanup; ghi invalid, không giết toàn bộPython |
| Plot trống | Kiểm tra family tênrun (`matrix_*`, `failure_*`) và số summary hợp lệ |
| Kết quả 3 run dao động lớn | GhiSD, xem tác vụ nền/thermal/order; chỉ rerun khi có lý do được ghi |

## 22. Kiểm tra code mẫu và giới hạn xác minh

Trong lúc soạn tài liệu, code đã được kiểm tra syntax và chạy ngắn bằng **Python 3.12 trên môi trường Linux với start method `spawn`**:

- Một virtual camera 424×240 @ 5 FPS,2 s:10 slot thời gian,10 frame completed, accounting OK.
- Hai virtual camera64×48 @ 30 FPS,3 s,4 slot/camera,delay 30 ms: FIFO và latest đều accounting OK; latest cho độ trễ thấp hơn trong phép thử chức năng.
- Script plot đọc kết quả, xuất summary/aggregateCSV vàPNG.

Các phép thử trên chỉ kiểm tra luồng code, counting, overload và plotting. **Không phải kết quả của HP Victus, không dùng số này để điền bảng báo cáo nhóm.** CPU/RSS process monitor trong môi trường kiểm tra này không thu đủPID nên được ghiNA. Nhóm phải xác nhận bộ đo trên Windows trước phép đo chính.

Chưa xác minh trong tài liệu: suite54 run đầy đủ trên laptop nhóm; clean installPython 3.11 trên Windows; interrupt bằng bàn phím trên Windows; NVIDIA telemetry; mode camera thật. TV1/TV5 chịu trách nhiệm các smoke/QA ở mục8–13. Không coi code đã được kiểm tra ngắn là bảo đảm mọi platform/workload đều đã chạy.

## 23. Phụ lục A — Toàn bộ script benchmark

Ba script dưới đây chạy độc lập với SDK camera. Tạo file rỗng `benchmark/__init__.py` và requirements ở mục8. Tất cả lệnh dùng module từ gốc repo; metadata đi qua queue, ảnh qua shared memory. Thư mục output mới để giữ evidence cũ.

### A1. `benchmark/bench.py`

```python
"""Synthetic RGB-D software benchmark; no USB/camera measurement."""
import argparse
import csv
import json
import multiprocessing as mp
import platform
import queue
import subprocess
import time
from pathlib import Path
from multiprocessing.shared_memory import SharedMemory
import numpy as np
import psutil


def producer(cam, cfg, name, free, output, ready, start, stop, counts):
    shm = SharedMemory(name=name)
    view = np.ndarray((cfg['pool_bytes'],), np.uint8, buffer=shm.buf)
    rng = np.random.default_rng(cfg['seed'] + cam)
    rgb = rng.integers(0, 256, (cfg['height'], cfg['width'], 3), dtype=np.uint8)
    depth = rng.integers(500, 5000, (cfg['height'], cfg['width']), dtype=np.uint16)
    template = np.concatenate((rgb.ravel(), depth.view(np.uint8).ravel()))
    base = cam * 4  # attempted, enqueued, rejected, schedule_missed
    ready.put(cam)
    try:
        while not start.value and not stop.is_set():
            time.sleep(.001)
        end = start.value + cfg['duration']
        for seq in range(int(round(cfg['fps'] * cfg['duration']))):
            deadline = start.value + seq / cfg['fps']
            if stop.wait(max(0, deadline - time.perf_counter())):
                break
            now = time.perf_counter()
            if now >= end or now - deadline >= 1 / cfg['fps']:
                counts[base + 3] += 1
                continue  # skip missed schedule slots; do not emit a catch-up burst
            counts[base] += 1
            try:
                slot = free.get(timeout=.002)
            except queue.Empty:
                counts[base + 2] += 1
                continue
            offset = (cam * cfg['slots'] + slot) * cfg['frame_bytes']
            t_capture = time.perf_counter()
            np.copyto(view[offset:offset + cfg['frame_bytes']], template)
            t_enqueue = time.perf_counter()
            if t_enqueue >= end:
                free.put(slot)
                counts[base + 2] += 1
                continue
            output.put((cam, seq, slot, t_capture, t_enqueue))
            counts[base + 1] += 1
    finally:
        del view
        shm.close()  # parent retains the lifetime handle, including on Windows


def git_value(*args):
    try:
        return subprocess.check_output(['git', *args], stderr=subprocess.DEVNULL,
                                       text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return 'unavailable'


def run(args):
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)  # never overwrite an earlier run
    cfg = vars(args).copy()
    cfg['frame_bytes'] = args.width * args.height * 5
    cfg['pool_bytes'] = cfg['frame_bytes'] * args.cameras * args.slots
    if cfg['pool_bytes'] > min(1_500_000_000, psutil.virtual_memory().available * .35):
        raise RuntimeError('Pool exceeds memory budget. Lower resolution/slots; record the change.')
    config = {**cfg, 'python': platform.python_version(), 'platform': platform.platform(),
              'logical_cpus': psutil.cpu_count(), 'ram_bytes': psutil.virtual_memory().total,
              'git_commit': git_value('rev-parse', 'HEAD'),
              'git_dirty': git_value('status', '--porcelain'),
              'source': 'seeded static RGB8 + uint16 depth; full copy each frame',
              'clock': 'time.perf_counter; host software clock', 'gpu': 'NA',
              'viewer': False, 'utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
    (out / 'config.json').write_text(json.dumps(config, indent=2), encoding='utf-8')
    ctx = mp.get_context('spawn')
    shm = SharedMemory(create=True, size=cfg['pool_bytes'])
    output = ctx.Queue(maxsize=args.cameras * args.slots)
    ready = ctx.Queue()
    frees = [ctx.Queue(maxsize=args.slots) for _ in range(args.cameras)]
    for free in frees:
        for slot in range(args.slots):
            free.put(slot)
    start, stop = ctx.Value('d', 0), ctx.Event()
    counts = ctx.Array('q', args.cameras * 4, lock=False)
    workers = [ctx.Process(target=producer, args=(cam, cfg, shm.name, frees[cam],
                  output, ready, start, stop, counts)) for cam in range(args.cameras)]
    completed = [0] * args.cameras
    stale = [0] * args.cameras
    late = [0] * args.cameras
    shutdown = [0] * args.cameras
    pending = {}
    latencies, waits, copy_ms, resource_rows = [], [], [], []
    frames = []
    view = np.ndarray((cfg['pool_bytes'],), np.uint8, buffer=shm.buf)
    copied = np.empty(cfg['frame_bytes'], np.uint8)
    status = 'ok'
    failure = None

    def release(item, state, finish=None):
        cam, seq, slot, tc, tq = item
        frees[cam].put(slot)
        frames.append([cam, seq, state, tc, tq, finish if finish is not None else '',
                       (finish - tc) * 1000 if finish is not None else ''])

    try:
        for worker in workers:
            worker.start()
        for _ in workers:
            ready.get(timeout=30)
        probes = []
        for pid in [__import__('os').getpid(), *[w.pid for w in workers]]:
            try:
                probes.append(psutil.Process(pid))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        config['resource_monitor_processes'] = len(probes)
        config['resource_monitor_expected'] = args.cameras + 1
        (out / 'config.json').write_text(json.dumps(config, indent=2), encoding='utf-8')
        for probe in probes:
            probe.cpu_percent(None)
        psutil.cpu_percent(None)
        start.value = time.perf_counter() + 1  # exclude process startup from measurement
        stop.wait(max(0, start.value - time.perf_counter()))
        end = start.value + args.duration
        next_sample = start.value + .5
        while time.perf_counter() < end:
            if any(w.exitcode not in (None, 0) for w in workers):
                raise RuntimeError('Producer process failed')
            now = time.perf_counter()
            if now >= next_sample:
                cpu, rss = 0., 0
                for probe in probes:
                    try:
                        cpu += probe.cpu_percent(None)
                        rss += probe.memory_info().rss
                    except psutil.NoSuchProcess:
                        pass
                backlog = sum(counts[c * 4 + 1] - completed[c] - stale[c] - late[c]
                              for c in range(args.cameras))
                resource_rows.append([now - start.value, cpu / (psutil.cpu_count() or 1) if len(probes) == args.cameras + 1 else None,
                                      psutil.cpu_percent(None), rss / 1e6 if len(probes) == args.cameras + 1 else None,
                                      psutil.virtual_memory().percent, max(0, backlog)])
                next_sample = now + .5
            if args.policy == 'latest':
                # Drain only a bounded batch, keeping the newest per camera.
                for _ in range(args.cameras * args.slots):
                    try:
                        item = output.get_nowait()
                    except queue.Empty:
                        break
                    cam = item[0]
                    if cam in pending:
                        stale[cam] += 1
                        release(pending[cam], 'stale')
                    pending[cam] = item  # replacement preserves fair camera order
                if not pending:
                    try:
                        item = output.get(timeout=.005)
                        pending[item[0]] = item
                    except queue.Empty:
                        continue
                cam = next(iter(pending))
                item = pending.pop(cam)
            else:
                try:
                    item = output.get(timeout=.005)
                except queue.Empty:
                    continue
            cam, seq, slot, tc, tq = item
            t_receive = time.perf_counter()
            offset = (cam * args.slots + slot) * cfg['frame_bytes']
            np.copyto(copied, view[offset:offset + cfg['frame_bytes']])
            t_copy = time.perf_counter()
            time.sleep(args.delay_ms / 1000)  # delay per RGB-D frameset, not per camera set
            finish = time.perf_counter()
            if finish < end:
                completed[cam] += 1
                latencies.append((finish - tc) * 1000)
                waits.append((t_receive - tq) * 1000)
                copy_ms.append((t_copy - t_receive) * 1000)
                release(item, 'completed', finish)
            else:
                late[cam] += 1
                release(item, 'completed_after_window', finish)
    except BaseException as exc:
        status, failure = 'invalid', repr(exc)
    finally:
        stop.set()
        # Draining frees queue feeder threads before join; never use empty()/qsize().
        join_deadline = time.perf_counter() + 10
        while any(w.is_alive() for w in workers) and time.perf_counter() < join_deadline:
            try:
                item = output.get(timeout=.02)
                shutdown[item[0]] += 1
                release(item, 'shutdown_backlog')
            except queue.Empty:
                pass
            for worker in workers:
                if worker.pid:
                    worker.join(timeout=0)
        for worker in workers:
            if worker.pid and worker.is_alive():
                worker.terminate()
                status = 'invalid'
                failure = 'Worker required forced termination'
            if worker.pid:
                worker.join(timeout=2)
                if worker.exitcode != 0:
                    status = 'invalid'
        while True:
            try:
                item = output.get_nowait()
                shutdown[item[0]] += 1
                release(item, 'shutdown_backlog')
            except queue.Empty:
                break
        for item in pending.values():
            shutdown[item[0]] += 1
            release(item, 'shutdown_backlog')
        pending.clear()
        del view
        shm.close()
        shm.unlink()  # on Windows deletion occurs after all handles are closed
        for q in [output, ready, *frees]:
            q.cancel_join_thread()
            q.close()
    scheduled = int(round(args.fps * args.duration))
    percam = []
    for cam in range(args.cameras):
        attempted, enqueued, rejected, missed = list(counts[cam * 4:cam * 4 + 4])
        accounting_ok = (scheduled == attempted + missed and attempted == enqueued + rejected
                         and enqueued == completed[cam] + stale[cam] + late[cam] + shutdown[cam])
        if not accounting_ok:
            status = 'invalid'
        percam.append({'camera': cam, 'scheduled': scheduled, 'attempted': attempted,
                       'enqueued': enqueued, 'rejected': rejected, 'schedule_missed': missed,
                       'completed': completed[cam], 'stale': stale[cam],
                       'late_completion': late[cam], 'shutdown_backlog': shutdown[cam],
                       'fps': completed[cam] / args.duration, 'accounting_ok': accounting_ok})
    def percentile(values):
        return float(np.percentile(values, 95)) if values else None
    total_scheduled = args.cameras * scheduled
    done = sum(completed)
    summary = {'status': status, 'failure': failure,
               'cameras': args.cameras, 'width': args.width, 'height': args.height,
               'target_fps': args.fps, 'duration_s': args.duration,
               'delay_ms': args.delay_ms, 'policy': args.policy, 'slots': args.slots,
               'aggregate_fps': done / args.duration, 'min_camera_fps': min(completed) / args.duration,
               'completion_ratio': done / total_scheduled,
               'explicit_drop_pct': 100 * (sum(p['rejected'] for p in percam) + sum(stale)) / total_scheduled,
               'deadline_miss_pct': 100 * sum(p['schedule_missed'] for p in percam) / total_scheduled,
               'backlog_at_end': sum(shutdown) + sum(late),
               'latency_mean_ms': float(np.mean(latencies)) if latencies else None,
               'latency_p95_ms': percentile(latencies), 'queue_wait_p95_ms': percentile(waits),
               'copy_p95_ms': percentile(copy_ms),
               'target_payload_Mbps': args.cameras * args.width * args.height * args.fps * 40 / 1e6,
               'completed_payload_MBps': done * cfg['frame_bytes'] / args.duration / 1e6,
               'pool_MB': cfg['pool_bytes'] / 1e6,
               'cpu_normalized_mean_pct': float(np.mean([r[1] for r in resource_rows if r[1] is not None])) if any(r[1] is not None for r in resource_rows) else None,
               'rss_sum_peak_MB': max([r[3] for r in resource_rows if r[3] is not None], default=None),
               'backlog_sample_peak': max([r[5] for r in resource_rows], default=None),
               'gpu': 'NA', 'per_camera': percam}
    for name, header, rows in [
        ('frames.csv', ['camera','seq','status','capture_s','enqueue_s','finish_s','latency_ms'], frames),
        ('resources.csv', ['elapsed_s','cpu_normalized_pct','system_cpu_pct','rss_sum_MB','system_memory_pct','backlog_proxy'], resource_rows),
        ('per_camera.csv', list(percam[0]), [list(row.values()) for row in percam])]:
        with (out / name).open('w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(rows)
    (out / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k != 'per_camera'}, indent=2), flush=True)
    return 0 if status == 'ok' else 2


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cameras', type=int, default=1)
    parser.add_argument('--width', type=int, default=424)
    parser.add_argument('--height', type=int, default=240)
    parser.add_argument('--fps', type=int, default=5)
    parser.add_argument('--duration', type=float, default=30)
    parser.add_argument('--slots', type=int, default=32)
    parser.add_argument('--delay-ms', type=float, default=0)
    parser.add_argument('--policy', choices=['fifo','latest'], default='fifo')
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    if min(args.cameras, args.width, args.height, args.fps, args.slots) <= 0 or args.duration <= 0 or args.delay_ms < 0:
        parser.error('Dimensions/count/FPS/duration must be positive; delay must be nonnegative')
    if abs(args.fps * args.duration - round(args.fps * args.duration)) > 1e-6:
        parser.error('fps * duration must be an integer')
    raise SystemExit(run(args))


if __name__ == '__main__':
    mp.freeze_support()
    main()
```

### A2. `benchmark/suite.py`

```python
import argparse
import json
import random
import subprocess
import sys
import time
from pathlib import Path

PROFILES = [('P0',424,240,5), ('P1',640,480,30), ('P2',1280,720,30)]


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--set', choices=['matrix','failure','all'], default='all')
    p.add_argument('--root', required=True)
    p.add_argument('--duration', type=float, default=30)
    p.add_argument('--repeats', type=int, default=3)
    p.add_argument('--seed', type=int, default=42)
    p.add_argument('--slots', type=int, default=32)
    a = p.parse_args()
    if a.repeats < 1:
        p.error('repeats must be positive')
    root = Path(a.root)
    root.mkdir(parents=True, exist_ok=False)
    jobs = []
    rng = random.Random(a.seed)
    for rep in range(1, a.repeats + 1):
        block = []
        if a.set in ('matrix','all'):
            for profile,w,h,fps in PROFILES:
                for n in [1,2,4,6]:
                    block.append((f'matrix_{profile}_N{n}_r{rep}', n,w,h,fps,0,'fifo'))
        if a.set in ('failure','all'):
            for delay in [0,15,30]:
                for policy in ['fifo','latest']:
                    block.append((f'failure_D{delay}_{policy}_r{rep}',6,1280,720,30,delay,policy))
        rng.shuffle(block)  # block by repetition to reduce time/temperature confounding
        jobs.extend(block)
    (root / 'order.json').write_text(json.dumps(jobs, indent=2), encoding='utf-8')
    for index,(name,n,w,h,fps,delay,policy) in enumerate(jobs,1):
        run_path = root / name
        command = [sys.executable, '-m','benchmark.bench','--cameras',str(n),
                   '--width',str(w),'--height',str(h),'--fps',str(fps),
                   '--duration',str(a.duration),'--slots',str(a.slots),'--delay-ms',str(delay),
                   '--policy',policy,'--seed',str(a.seed),'--out',str(run_path)]
        print(f'[{index}/{len(jobs)}] {name}', flush=True)
        # Exact argument list, no shell interpolation.
        (root / f'{name}.command.json').write_text(json.dumps(command, indent=2), encoding='utf-8')
        with (root / f'{name}.console.log').open('w', encoding='utf-8') as log:
            result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT,
                                    timeout=a.duration + 90)
        if result.returncode:
            raise SystemExit(f'Run invalid: {name}. Inspect log; do not silently keep running.')
        time.sleep(2)


if __name__ == '__main__':
    main()
```

### A3. `benchmark/plot.py`

```python
import argparse
import csv
import json
import statistics
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--root', required=True)
    a = p.parse_args()
    root = Path(a.root)
    summaries = []
    for path in sorted(root.rglob('summary.json')):
        row = json.loads(path.read_text(encoding='utf-8'))
        row['run_id'] = path.parent.name
        if row['status'] != 'ok':
            raise SystemExit(f'Invalid run: {path}')
        summaries.append(row)
    if not summaries:
        raise SystemExit('No summaries found')
    out = root / 'plots'
    out.mkdir(exist_ok=True)
    columns = [k for k in summaries[0] if k != 'per_camera']
    with (root / 'summary.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(summaries)
    groups = {}
    for row in summaries:
        family = 'matrix' if row['run_id'].startswith('matrix_') else 'failure' if row['run_id'].startswith('failure_') else 'manual'
        key = (family,row['width'],row['height'],row['target_fps'],row['cameras'],row['delay_ms'],row['policy'])
        groups.setdefault(key,[]).append(row)
    metrics = ['min_camera_fps','latency_p95_ms','explicit_drop_pct','cpu_normalized_mean_pct']
    agg = []
    for key,rows in sorted(groups.items()):
        record = dict(zip(['family','width','height','target_fps','cameras','delay_ms','policy'],key))
        record['n_runs'] = len(rows)
        for metric in metrics:
            values = [r[metric] for r in rows if r[metric] is not None]
            record[metric+'_mean'] = statistics.mean(values) if values else None
            record[metric+'_sd'] = statistics.stdev(values) if len(values)>1 else (0 if values else None)
        agg.append(record)
    with (root / 'aggregate.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(agg[0]))
        writer.writeheader()
        writer.writerows(agg)
    for metric,label in [('min_camera_fps','Slowest virtual camera FPS'),
                          ('latency_p95_ms','Per-run P95 latency, mean ± SD (ms)'),
                          ('explicit_drop_pct','Explicit software drop (%)')]:
        matrix=[r for r in summaries if r['run_id'].startswith('matrix_')]
        if not matrix:
            continue
        fig,ax=plt.subplots(figsize=(8,4.8))
        for profile in sorted({(r['width'],r['height'],r['target_fps']) for r in matrix}):
            data=[r for r in agg if (r['width'],r['height'],r['target_fps'])==profile
                  and r['delay_ms']==0 and r['policy']=='fifo' and r['family']=='matrix']
            data.sort(key=lambda r:r['cameras'])
            ax.errorbar([r['cameras'] for r in data],
                        [r[metric+'_mean'] for r in data],
                        yerr=[r[metric+'_sd'] for r in data], marker='o',capsize=4,
                        label=f'{profile[0]}x{profile[1]} @ {profile[2]}')
        ax.set(xlabel='Virtual camera count',ylabel=label,
               title='Synthetic RGB-D software pipeline; USB not measured')
        ax.grid(alpha=.25)
        if matrix:
            ax.legend()
        fig.tight_layout()
        fig.savefig(out / f'matrix_{metric}.png',dpi=180)
        plt.close(fig)
    failure=[r for r in summaries if r['run_id'].startswith('failure_')]
    if failure:
        fig,axes=plt.subplots(1,2,figsize=(10,4))
        for policy in ['fifo','latest']:
            reference = failure[0]
            rows=[r for r in agg if all(r[k]==reference[k] for k in ['cameras','width','height','target_fps'])
                  and r['policy']==policy and r['family']=='failure']
            rows.sort(key=lambda r:r['delay_ms'])
            for ax,metric,label in zip(axes,['latency_p95_ms','explicit_drop_pct'],
                                      ['P95 latency (ms)','Explicit drop (%)']):
                ax.errorbar([r['delay_ms'] for r in rows],[r[metric+'_mean'] for r in rows],
                            yerr=[r[metric+'_sd'] for r in rows],marker='o',capsize=4,label=policy)
                ax.set(xlabel='Injected delay per frameset (ms)',ylabel=label)
                ax.grid(alpha=.25)
                ax.legend()
        fig.suptitle(f"Synthetic {reference['cameras']} streams {reference['width']}x{reference['height']} @{reference['target_fps']}; same pool")
        fig.tight_layout()
        fig.savefig(out / 'failure_policy_tradeoff.png',dpi=180)
        plt.close(fig)
    # Per-run time series gives evidence of backlog growth, not just one summary.
    for row in failure:
        if 'r1' not in row['run_id']:
            continue
        with (root / row['run_id'] / 'resources.csv').open(encoding='utf-8') as f:
            samples=list(csv.DictReader(f))
        fig,ax=plt.subplots(figsize=(7,3.8))
        ax.plot([float(r['elapsed_s']) for r in samples],
                [float(r['backlog_proxy']) for r in samples])
        ax.set(xlabel='Elapsed (s)',ylabel='Enqueued but unprocessed frames',title=row['run_id'])
        ax.grid(alpha=.25)
        fig.tight_layout()
        fig.savefig(out / f"backlog_{row['run_id']}.png",dpi=180)
        plt.close(fig)
    print(f'Wrote {root / "summary.csv"}, {root / "aggregate.csv"}, {out}')


if __name__ == '__main__':
    main()
```

### A4. Kiểm tra sau khi sao chép

```powershell
.\.venv\Scripts\python.exe -m py_compile benchmark\bench.py benchmark\suite.py benchmark\plot.py
.\.venv\Scripts\python.exe -m benchmark.bench --cameras 1 --duration 10 --out results/smoke_copy_01
Get-Content results/smoke_copy_01/summary.json
```

Sau khi smoke Windows hợp lệ, TV1/TV5 đóng dependency lock, TV4 xác nhận protocol và nhóm bắt đầu suite. Không dùng số kiểm tra chức năng của tài liệu thay cho số nhóm tự đo.
