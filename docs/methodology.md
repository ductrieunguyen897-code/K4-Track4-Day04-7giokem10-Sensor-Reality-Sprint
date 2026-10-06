# Phương pháp đo — TV4

Ngày 05/10/2026 · Phiên bản TV4-draft-1.0 · Chưa được TV2/TV3/TV5 xác nhận.

Bảng cấu hình duy nhất: [benchmark_plan.md](benchmark_plan.md). Nội dung dưới đây đối chiếu tĩnh với Phụ lục A của [kế hoạch gốc](../Ke_hoach_T7_MultiCamera_Team5_Windows11.md); chưa đối chiếu với code tích hợp và chưa chạy thử.

## Đường đi của một cặp ảnh

Một cặp RGB-D là ảnh RGB và ảnh depth của một camera mô phỏng. Mỗi camera có một tiến trình tạo nguồn; tiến trình chính xử lý và ghi số liệu.

Nguồn tạo mẫu bằng seed + camera ID: RGB uint8 (H,W,3), depth uint16 (H,W), giá trị depth 500–4999 không mang đơn vị khoảng cách cảm biến. Mẫu tĩnh được tạo trước đo; mỗi lần phát vẫn sao chép toàn bộ vào vùng nhớ chung. Bộ xử lý sao chép toàn bộ ra vùng nhớ riêng rồi thực hiện delay.

Thông tin qua hàng chờ: `(camera, seq, slot, capture_time, enqueue_time)`: mã camera, số thứ tự, ô nhớ, thời điểm trước/sau sao chép nguồn. Ô chỉ được trả khi xử lý hoặc loại bỏ ảnh; không ghi đè ô đang dùng.

Nhịp phát dự kiến là 1/F giây. Code mẫu bỏ lịch bị trễ ít nhất một chu kỳ, không phát dồn để bù. Khi không lấy được ô nhớ trong thời hạn, ghi rejected. latest đọc một nhóm hữu hạn, giữ ảnh mới nhất từng camera trong nhóm đó; không bảo đảm lấy ảnh mới nhất tuyệt đối tại mọi thời điểm.

## Khoảng đo và trình tự

Sau khi các nguồn báo sẵn sàng, code đặt `start = perf_counter() + 1`; kết thúc tại `end = start + T`. Dùng cùng đồng hồ trên cùng máy. Thời gian tạo tiến trình và mẫu ảnh không nằm trong T. Làm nóng riêng P1 3 giây trước suite, không đưa vào thống kê chính.

Lần đo chính kéo dài T=30 giây. Ảnh hoàn thành trước end mới thuộc completed. Ảnh xử lý xong sau end ghi late_completion; ảnh dọn khi kết thúc ghi shutdown_backlog. Dọn bộ nhớ sau end không làm kéo dài mẫu số FPS.

Chạy 3 lượt độc lập mỗi cấu hình; code suite chia theo lần lặp rồi xáo thứ tự từng nhóm bằng seed 42. Lưu `order.json`. Chạy lần lượt trên cùng máy và chế độ nguồn. Lượt lỗi được giữ lại cùng lý do; lượt thay thế có ID mới, không tự bỏ lượt chậm.

## Đếm và kiểm tra

| Field | Ý nghĩa |
|---|---|
| scheduled | Số thời điểm phát dự kiến: round(F×T) cho từng camera |
| schedule_missed | Thời điểm phát bị lỡ |
| attempted | Số lần thực sự thử đưa ảnh vào hệ thống |
| enqueued | Ảnh sao chép xong trước end và đã gửi thông tin |
| rejected | Lần thử thất bại vì hết ô hoặc sao chép quá hạn |
| completed | Ảnh xử lý xong trước end |
| stale | Ảnh cũ bị latest bỏ |
| late_completion | Đã bắt đầu xử lý nhưng xong sau end |
| shutdown_backlog | Ảnh còn lại được dọn khi kết thúc |

Kiểm tra từng camera sau khi dọn:

```text
scheduled = attempted + schedule_missed
attempted = enqueued + rejected
enqueued = completed + stale + late_completion + shutdown_backlog
```

Ảnh chưa hoàn thành không đồng nghĩa ảnh bị bỏ. Kiểm tra thêm số dòng frames.csv theo camera và trạng thái khớp per_camera.csv; mỗi cặp camera/seq chỉ có một trạng thái cuối. `queue.empty()` hoặc `qsize()` không thay được các bộ đếm.

## Công thức và đơn vị

Trong công thức tổng, cộng các bộ đếm của tất cả camera. S=5WH byte/cặp ảnh, T là giây, F là FPS mục tiêu/camera, N là camera.

| Chỉ số | Công thức | Đơn vị |
|---|---|---|
| FPS từng camera | completed_camera/T | cặp ảnh/giây |
| FPS tổng | sum(completed)/T | cặp ảnh/giây |
| FPS camera chậm nhất | min(completed_camera)/T | cặp ảnh/giây |
| Tỷ lệ hoàn thành | sum(completed)/sum(scheduled) | 0–1 |
| Tỷ lệ bỏ rõ ràng | 100×sum(rejected+stale)/sum(scheduled) | % |
| Tỷ lệ lỡ nhịp | 100×sum(schedule_missed)/sum(scheduled) | % |
| Ảnh chưa xong đúng hạn | sum(shutdown_backlog+late_completion) | cặp ảnh |
| Dữ liệu mục tiêu | 40NWHF/1000000 | Mbps |
| Dữ liệu hoàn thành | sum(completed)×S/(T×1000000) | MB/s |
| Pool | N×slots×S/1000000 | MB |

Độ trễ = 1000×(t_finish−t_capture), ms, chỉ tính completed. `t_capture` ngay trước nguồn sao chép, `t_enqueue` ngay sau sao chép và trước gửi thông tin, `t_receive` sau lấy thông tin, `t_copy` sau sao chép phía xử lý.

Chờ hàng đợi = 1000×(t_receive−t_enqueue); sao chép phía xử lý = 1000×(t_copy−t_receive). P95 là ngưỡng khoảng 95% mẫu không vượt quá; dùng np.percentile theo code mẫu, khóa phiên bản NumPy. Không cộng ba P95 để suy ra tổng P95 vì chúng có thể thuộc các ảnh khác nhau.

CPU chuẩn hóa: tổng CPU% của tiến trình chính và N nguồn chia số CPU logic. CPU hệ thống gồm cả tác vụ ngoài benchmark. RAM báo tổng RSS (bộ nhớ đang hiện diện của các tiến trình), có thể đếm vùng nhớ chung nhiều lần; không gọi là RAM vật lý duy nhất. Mẫu tài nguyên theo code khoảng 0.5 giây nhưng có thể thưa hơn do xử lý chậm. GPU là NA (chưa đo), không điền 0.

## File và cột theo code mẫu

| File | Cột/nội dung |
|---|---|
| frames.csv | camera, seq, status, capture_s, enqueue_s, finish_s, latency_ms |
| resources.csv | elapsed_s, cpu_normalized_pct, system_cpu_pct, rss_sum_MB, system_memory_pct, backlog_proxy |
| per_camera.csv | camera, scheduled, attempted, enqueued, rejected, schedule_missed, completed, stale, late_completion, shutdown_backlog, fps, accounting_ok |
| config.json | Kích thước, FPS, duration, slots, seed, policy, delay_ms, nguồn, đồng hồ, commit, môi trường, số tiến trình giám sát |
| summary.json | Trạng thái, chỉ số tổng, chỉ số từng camera; trường thiếu là null/NA |
| summary.csv | Một dòng mỗi run do plot.py xuất, có run_id |
| aggregate.csv | Một dòng mỗi nhóm điều kiện, n_runs, mean/SD của các metric được script hỗ trợ |

frames.csv không chứa dòng riêng cho rejected/schedule_missed; chúng nằm trong per_camera.csv. Nó có thể chứa độ trễ late_completion, nên phải lọc status=completed khi đối chiếu độ trễ trong summary. Thời gian `capture_s` là đồng hồ phần mềm, không phải ngày giờ lịch.

Đầu ra aggregate mẫu chỉ có FPS camera chậm nhất, P95 latency, drop và CPU. TV3 cần bổ sung tổng hợp các chỉ số còn lại nếu dùng trong báo cáo; không giả định chúng đã có sẵn.

## Hợp lệ và tổng hợp

Một lượt dùng để kết luận phải có status=ok; mọi accounting_ok=true; đúng cấu hình/commit/máy; đủ thời gian; completed>0 và độ trễ hữu hạn không âm. Thiếu CPU/RAM phải ghi lý do và phạm vi thiếu; chưa được kết luận về tài nguyên. `status=ok` một mình không đủ.

Từng nhóm cần đủ 3 lượt hợp lệ, cùng tất cả thông số ngoài yếu tố đang so sánh. Tính trung bình và SD (độ dao động giữa ba lượt) của từng chỉ số. P95 tổng hợp là trung bình/SD của ba P95 từng lượt, không phải P95 của ảnh ghép chung. Không lấy số ảnh làm số lần thí nghiệm độc lập.

Đọc latency cùng completion/drop/backlog: chỉ tính ảnh hoàn thành có thể làm độ trễ trông thấp khi nhiều ảnh bị bỏ. Giữ FPS camera chậm nhất bên cạnh FPS tổng.

Ngưỡng đề xuất trước đo theo mục 11.5: mỗi camera đạt ít nhất 95% FPS mục tiêu, completion ít nhất 95%, P95 ≤ max(100 ms, 2×1000/F ms). Đây là tiêu chí nội bộ chưa được nhóm chốt; không phải chuẩn an toàn robot. Mức CPU dự phòng cần nhóm xác nhận riêng.

Các điểm cần xử lý trước khóa: [integration_review.md](integration_review.md). Ghi kết luận và bằng chứng trong [EVIDENCE_INDEX](../results/EVIDENCE_INDEX.md).

