# Quyết định Kỹ thuật Xử lý Đa luồng (Engineering Decision Record)

**Phiên bản:** 1.0 · **Ngày:** 06/10/2026  
**Đề tài:** T7 — Multi-camera bandwidth profiling  
**Thiết bị thực nghiệm:** HP Victus 16-e0xxx (Windows 11)  
**Bộ số liệu chứng cứ:** [`results/session_hp_victus_full/`](../results/session_hp_victus_full/) (54 runs, n=3 lặp độc lập)  

---

## 1. Bối cảnh & Vấn đề Kỹ thuật
Khi một hệ thống robot tự hành tiếp nhận dữ liệu từ 6 camera RGB-D độ phân giải cao ($1280 \times 720$ @ 30 FPS, tải danh định 180 frameset/s ~ 6.6 Gbps raw payload), nếu tiến trình xử lý downstream (consumer: AI detector, visual odometry, mapping) bị trễ $15\text{ ms}$ hoặc $30\text{ ms}$ cho mỗi frameset, hàng đợi metadata và bộ đệm Shared Memory sẽ bị quá tải nghiêm trọng. Nhóm cần đưa ra quyết định kỹ thuật lựa chọn chính sách hàng đợi và cấu hình cảm biến tối ưu dựa trên số liệu thực nghiệm.

---

## 2. Bằng chứng Thực nghiệm Đo được trên HP Victus 16

So sánh trực tiếp giữa chính sách FIFO và Latest trên cùng cấu hình P2 ($1280 \times 720$), 6 camera, $N=6$, 32 slots/camera, thời lượng 30s:

| Điều kiện | Chính sách | Aggregate FPS | Độ trễ P95 (Mean ± SD) | Tỷ lệ Drop (%) | Tồn đọng (Backlog cuối) |
|---|---|---:|---:|---:|---:|
| **Delay 0 ms** | FIFO (F0)<br>Latest (I0) | $180.00 \pm 0.00$<br>$179.87 \pm 0.23$ | $7.03 \pm 1.37\text{ ms}$<br>$8.13 \pm 3.73\text{ ms}$ | $0.00\%$<br>$0.08\%$ | 0 frames<br>0 frames |
| **Delay 15 ms** | FIFO (F1)<br>Latest (I1) | $61.10 \pm 0.26$<br>$59.67 \pm 0.25$ | **$3,175.09 \pm 42.64\text{ ms}$**<br>**$53.00 \pm 0.10\text{ ms}$** | $62.52\%$<br>$66.74\%$ | **191 frames**<br>**6 frames** |
| **Delay 30 ms** | FIFO (F2)<br>Latest (I2) | $31.60 \pm 0.10$<br>$31.07 \pm 0.12$ | **$6,165.38 \pm 16.77\text{ ms}$**<br>**$68.13 \pm 0.08\text{ ms}$** | $78.88\%$<br>$82.60\%$ | **191 frames**<br>**8 frames** |

- Đồ thị đối chứng: [`failure_policy_tradeoff.png`](../results/session_hp_victus_full/plots/failure_policy_tradeoff.png)
- Đồ thị diễn tiến hàng đợi: [`backlog_failure_D15_fifo_r1.png`](../results/session_hp_victus_full/plots/backlog_failure_D15_fifo_r1.png) và [`backlog_failure_D15_latest_r1.png`](../results/session_hp_victus_full/plots/backlog_failure_D15_latest_r1.png).

---

## 3. Quyết định Kỹ thuật Lựa chọn

### Quyết định 1: Áp dụng chính sách `Latest per-camera` cho tác vụ điều khiển thời gian thực
- **Lý do:** Ở delay 15ms và 30ms, chính sách FIFO tích lũy hàng đợi khiến độ trễ P95 tăng vọt lên **$3.18 - 6.17\text{ giây}$**, khiến robot phản ứng dựa trên hình ảnh quá khứ. Chính sách Latest chủ động drop khung hình cũ để ghìm độ trễ P95 ở mức **$< 70\text{ ms}$** (giảm 60–90 lần), giữ vững độ tươi mới của dữ liệu (data freshness).
- **Sự đánh đổi (Trade-off):** Tỷ lệ drop tăng nhẹ từ $62.5\%$ lên $66.7\%$ (ở delay 15ms) và từ $78.9\%$ lên $82.6\%$ (ở delay 30ms). Đây là sự đánh đổi chấp nhận được vì dữ liệu trễ 3-6 giây hoàn toàn vô dụng cho điều hướng thời gian thực.

### Quyết định 2: Duy trì dung lượng pool cố định (Bounded Slot Pool: 32 slots/camera)
- **Lý do:** Giới hạn cứng dung lượng Shared Memory ở mức $884.7\text{ MB}$ (cho 6 camera P2), bảo vệ hệ điều hành laptop không bị cạn kiệt RAM vật lý (Out-Of-Memory) khi có bão hòa hàng đợi. Producer bị từ chối lấy slot sẽ drop ngay tại nguồn thay vì cấp phát vô hạn.

### Quyết định 3: Khuyến nghị kiến trúc cảm biến có điều kiện (4 vs 8 luồng)
- **Phương án 4 camera VGA ($4 \times 640 \times 480$ @ 30 FPS):** Tải ứng dụng ~1.47 Gbps, độ trễ P95 thực tế chỉ **$2.30\text{ ms}$**, CPU sử dụng ~1.08%, phù hợp cho robot có tải tính toán biên trung bình.
- **Phương án 6 camera HD ($6 \times 1280 \times 720$ @ 30 FPS):** Tải ứng dụng ~6.6 Gbps, P95 Latency chỉ **$6.95\text{ ms}$**, CPU sử dụng ~3.88%, nhưng đòi hỏi consumer phải có năng lực xử lý cực nhanh (delay $< 5.5\text{ ms}$/frameset) nếu không sẽ nghẽn.

---

## 4. Ranh giới & Phép kiểm tra Phần cứng tiếp theo
- **Ranh giới:** Kết quả trên đo lường khả năng luân chuyển dữ liệu của pipeline phần mềm trên RAM và IPC Windows 11; chưa phản ánh giới hạn băng thông USB 3.0 controller và độ trễ ISP/ASIC của cảm biến vật lý.
- **Phép thử tiếp theo:** Kết nối camera Intel RealSense D435/D455 vật lý, phân bố trên các USB Host Controller độc lập và đo lường độ trễ phơi sáng quang học thực tế.
