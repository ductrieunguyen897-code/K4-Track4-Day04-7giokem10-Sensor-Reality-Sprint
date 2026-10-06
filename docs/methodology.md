# Phương pháp đo — TV4 (soạn) / TV3 (xác nhận metric, counter, cửa sổ, đồng hồ)

Ngày 05/10/2026 · Phiên bản TV4-draft-1.0 → **TV3-metrics-confirm-1.0**.

Bảng cấu hình duy nhất: [benchmark_plan.md](benchmark_plan.md). Nội dung dưới đây đối chiếu tĩnh với Phụ lục A của [kế hoạch gốc](../Ke_hoach_T7_MultiCamera_Team5_Windows11.md).

> **TV3 xác nhận (Metrics Lead).** Phần *Đếm và kiểm tra*, *Công thức và đơn vị*, *File và cột theo code mẫu*, *Hợp lệ và tổng hợp* dưới đây đã được đối chiếu với code tích hợp trong `bench.py` (SECTION 3 — `MetricsCollector`) và `plots/plot.py` tại nhánh `feat/tv3-metrics-report` (commit `93a4dc5`). Các điểm khác biệt so với bản nháp TV4-draft-1.0 được ghi rõ bằng khối **[TV3]** để nhóm đối chất trước khi khóa. Những mục còn lại (đường đi dữ liệu, khoảng đo, trình tự) là mô tả chung, TV2 xác nhận phần producer.

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

**[TV3] Ba đẳng thức trên được `MetricsCollector.finalize` kiểm tra cho từng camera và ghi vào `per_camera.csv` (`accounting_ok`) và `summary.json` (`accounting_all_ok`).** Nguồn số: `scheduled` = `round(F×T)`; `attempted/enqueued/rejected/schedule_missed` do producer ghi vào `ctx.Array('q')` (4 ô/camera); `completed/stale/late_completion/shutdown_backlog` do consumer đếm. `schedule_missed` là nhịp bị bỏ khi `now ≥ end` hoặc trễ ≥ 1/F — producer **không phát dồn bù**. `rejected` gồm hai trường hợp: hết ô trống (`queue.Empty` khi lấy slot) và bản sao xong sau `end`. `stale` chỉ sinh ở policy `latest`. Đây là các điểm dễ bị hiểu nhầm: **`rejected` (producer chủ động) khác `stale` (consumer bỏ ảnh cũ) khác `schedule_missed` (không thử phát)**, và cả ba đều khác `shutdown_backlog`/`late_completion` (ảnh thật đã vào hệ thống nhưng chưa xong trong cửa sổ).

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

**[TV3] Cửa sổ và đồng hồ (xác nhận theo code).** `start = perf_counter() + 1` sau khi mọi nguồn báo ready; `end = start + T`. Thời gian tạo process, tạo mẫu tĩnh và 1 giây đệm không nằm trong T. Mốc `t_capture` lấy **ngay trước** khi producer copy vào slot, `t_enqueue` **ngay sau** copy và trước `put` metadata, `t_receive` **sau** khi consumer lấy được metadata, `t_copy` **sau** khi consumer copy ra buffer riêng. Vì vậy `latency = t_finish − t_capture` là **end-to-end** (gồm copy nguồn + chờ hàng đợi + copy đích + delay cài), còn `queue_wait` và `copy` chỉ là hai thành phần. **[TV3] Không được cộng ba P95 lại** vì `latency P95`, `queue_wait P95`, `copy P95` có thể thuộc ba ảnh khác nhau — chỉ so độ lớn để biết nghẽn nằm ở hàng đợi hay ở copy.

**[TV3] Latency bias.** `latency_p95_ms` chỉ tính ảnh `completed`; khi drop nhiều (policy `latest` hoặc `rejected` cao), các ảnh chờ lâu bị loại khỏi mẫu nên **P95 trông thấp một cách giả tạo**. Vì thế luôn đọc `latency_p95_ms` song song với `completion_ratio`, `explicit_drop_pct` và `backlog_at_end`; một P95 thấp kèm drop cao không phải là "hệ thống nhanh".

CPU chuẩn hóa: tổng CPU% của tiến trình chính và N nguồn chia số CPU logic. CPU hệ thống gồm cả tác vụ ngoài benchmark. RAM báo tổng RSS (bộ nhớ đang hiện diện của các tiến trình), có thể đếm vùng nhớ chung nhiều lần; không gọi là RAM vật lý duy nhất. Mẫu tài nguyên theo code khoảng 0.5 giây nhưng có thể thưa hơn do xử lý chậm. GPU là NA (chưa đo), không điền 0.

## File và cột theo code mẫu

| File | Cột/nội dung |
|---|---|
| frames.csv | camera, seq, status, slot_id, capture_s, enqueue_s, finish_s, latency_ms |
| resources.csv | elapsed_s, cpu_normalized_pct, system_cpu_pct, rss_sum_MB, system_memory_pct, backlog_proxy, n_valid_processes |
| per_camera.csv | camera, scheduled, attempted, enqueued, rejected, schedule_missed, completed, stale, late_completion, shutdown_backlog, fps, accounting_ok |
| frames_telemetry.csv | timestamp, camera_id, frame_id, slot_id, t_produced, t_consumed, latency_ms, payload_bytes (schema `contract_spec.md`, cổng smoke test TV1) |
| config.json | Kích thước, FPS, duration, slots, seed, policy, delay_ms, nguồn, đồng hồ, commit, môi trường, số tiến trình giám sát |
| summary.json | Trạng thái, chỉ số tổng, chỉ số từng camera; trường thiếu là null/NA |
| summary.csv | Một dòng mỗi run do plot.py xuất, có run_id |
| aggregate.csv | Một dòng mỗi nhóm điều kiện, n_runs, mean/SD của các metric được script hỗ trợ |

**[TV3] Trạng thái trong `frames.csv`** là một trong bốn giá trị: `completed` (xong trước `end`), `completed_after_window` (late_completion), `stale` (latest bỏ), `shutdown_backlog` (dọn lúc kết thúc). Tổng số dòng `frames.csv` đúng bằng `enqueued` từng camera, nên `frames.csv` không chứa dòng riêng cho `rejected`/`schedule_missed` — chúng chỉ nằm trong `per_camera.csv`.

**[TV3] `latency_ms` trong `frames.csv`** được ghi cho cả `completed_after_window`, còn các metric độ trễ trong `summary.json` (`latency_mean_ms`, `latency_p95_ms`, `queue_wait_p95_ms`, `copy_p95_ms`) **chỉ tính `completed`**. Khi đối chiếu độ trễ từ `frames.csv`, phải lọc `status=completed`. `capture_s`/`enqueue_s`/`finish_s` là đồng hồ phần mềm `time.perf_counter`, không phải ngày giờ lịch và không so được giữa hai máy.

**[TV3] `resources.csv`** thêm cột `n_valid_processes` (số tiến trình trả lời thành công mỗi mẫu). Khi `n_valid_processes < cameras+1`, dòng đó là tổng thiếu và bị loại khỏi `cpu_normalized_mean_pct`/`rss_sum_peak_MB`; `summary.json` ghi kèm `resource_samples`, `resource_samples_valid`, `resource_monitor_expected`. GPU luôn `NA`, không điền 0.

Đầu ra aggregate của `plots/plot.py` tổng hợp **đủ 12 chỉ số** (không chỉ FPS chậm nhất/P95/drop/CPU): thêm FPS tổng, completion, deadline miss, backlog, latency mean, queue-wait P95, copy P95, RSS đỉnh. Mỗi chỉ số có `_mean`, `_sd` và `_n` (số lượt có giá trị hợp lệ) để không giả định đủ ba lượt khi có giá trị null.

## Hợp lệ và tổng hợp

Một lượt dùng để kết luận phải có status=ok; mọi accounting_ok=true; đúng cấu hình/commit/máy; đủ thời gian; completed>0 và độ trễ hữu hạn không âm. Thiếu CPU/RAM phải ghi lý do và phạm vi thiếu; chưa được kết luận về tài nguyên. `status=ok` một mình không đủ.

**[TV3] Bộ kiểm tra hợp lệ trong code.** `MetricsCollector.finalize` gán `status="invalid"` (kèm trường `failure` nêu lý do) nếu bất kỳ điều nào sau đây xảy ra, ngay cả khi đếm khớp:
1. `accounting_all_ok` sai (một trong ba đẳng thức vỡ ở bất kỳ camera nào);
2. `completed == 0` (không có ảnh hoàn thành trong cửa sổ);
3. có mẫu latency không hữu hạn hoặc âm;
4. một worker phải `terminate()` (cờ `forced_termination`).

`summary.json` cũng ghi `valid` (bool) và `failure` để `plot.py` lọc. **[TV3]** `status=ok` chưa đủ để đưa vào tổng hợp — `plots/plot.py` còn yêu cầu `accounting_all_ok=true` và `frames_received>0`, và loại run không đạt ra khỏi `summary.csv`/`aggregate.csv` (vẫn giữ trên đĩa và in lý do).

Từng nhóm cần đủ 3 lượt hợp lệ, cùng tất cả thông số ngoài yếu tố đang so sánh. Tính trung bình và SD (độ dao động giữa ba lượt) của từng chỉ số. P95 tổng hợp là trung bình/SD của ba P95 từng lượt, không phải P95 của ảnh ghép chung. Không lấy số ảnh làm số lần thí nghiệm độc lập.

**[TV3] Khóa nhóm tổng hợp.** `plots/plot.py` gom nhóm theo đủ 11 khóa: `family, width, height, target_fps, cameras, delay_ms, policy, slots, duration_s, seed, code_commit` — nên hai điều kiện khác slots/duration/seed/commit **không bị trộn** dù nằm chung một root. Script cảnh báo (`[WARN]`) khi một nhóm có ít hơn `--min-repeats` (mặc định 3) lượt hợp lệ, nhưng không tự bịa lượt thiếu.

**[TV3] SD không phải khoảng tin cậy.** `_sd` là độ lệch chuẩn mẫu giữa các lượt (n=3), phản ánh dao động chạy lại, **không** phải CI 95% và không suy ra được ý nghĩa thống kê. `_n` ghi số lượt thực có giá trị cho từng chỉ số (metric có thể thiếu ở vài lượt), nên không giả định luôn đủ 3.

Đọc latency cùng completion/drop/backlog: chỉ tính ảnh hoàn thành có thể làm độ trễ trông thấp khi nhiều ảnh bị bỏ. Giữ FPS camera chậm nhất bên cạnh FPS tổng.

Ngưỡng đề xuất trước đo theo mục 11.5: mỗi camera đạt ít nhất 95% FPS mục tiêu, completion ít nhất 95%, P95 ≤ max(100 ms, 2×1000/F ms). Đây là tiêu chí nội bộ chưa được nhóm chốt; không phải chuẩn an toàn robot. Mức CPU dự phòng cần nhóm xác nhận riêng.

Các điểm cần xử lý trước khóa: [integration_review.md](integration_review.md). Ghi kết luận và bằng chứng trong [EVIDENCE_INDEX](../results/EVIDENCE_INDEX.md).

