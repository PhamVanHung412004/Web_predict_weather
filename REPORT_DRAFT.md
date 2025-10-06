# Báo cáo (Bản nháp) — Phân tích chất lượng không khí từ dữ liệu khí tượng

> NOTE: Đây là bản nháp tự động tạo. Thay các placeholder bằng số liệu thực và các ảnh trong `backend/results`.

## Title
Phân tích chất lượng không khí dựa trên dữ liệu khí tượng

## Authors
Tên tác giả

## Date
YYYY-MM-DD

---

## Abstract
(Bạn có thể chỉnh lại 100–200 từ)

Báo cáo này trình bày phân tích dữ liệu khí tượng nhằm đánh giá chất lượng không khí. Dữ liệu đầu vào là file CSV chứa các yếu tố khí tượng và các chỉ số ô nhiễm. Chúng tôi tiến hành khám phá dữ liệu, thống kê mô tả, phân tích phân phối, ma trận tương quan, biểu đồ xu hướng thời gian, và phát hiện giá trị bất thường. Kết quả chính được minh họa bởi các biểu đồ lưu trong `backend/results`.

---

## 1. Introduction
- Bối cảnh: ô nhiễm không khí ảnh hưởng sức khỏe và cần giám sát.
- Mục tiêu: phân tích EDA để xác định các yếu tố liên quan đến PM2.5/AQI, phát hiện bất thường, và trình bày biểu đồ trực quan.
- Dữ liệu: `frontend/sample_data.csv` (mô tả các cột trong phần Appendix).

---

## 2. Methods
### 2.1 Dữ liệu
- Nguồn: local CSV (upload qua giao diện web).
- Các cột chính: PM2.5, PM10, NO2, SO2, CO, O3, temperature, humidity, pressure, wind_speed.

### 2.2 Tiền xử lý
- Loại bỏ dòng không hợp lệ, xử lý missing values (drop/mean impute tùy mục tiêu).
- Chuẩn hóa khi cần (StandardScaler) cho một số phân tích.

### 2.3 Phân tích
- Thống kê mô tả: mean, std, min, max, median, percentiles.
- Phân phối: histogram cho từng chỉ số.
- Tương quan: ma trận tương quan (heatmap).
- Xu hướng theo thời gian: line plots (lấy tối đa 100 mẫu đầu để minh họa).
- Phát hiện outliers: IQR method.
- Phân loại AQI: theo hàm `classify_aqi_level` trong code.

### 2.4 Công cụ
- Flask backend tạo các biểu đồ (`backend/app.py`).
- Frontend: `frontend/index.html` + `frontend/js/app.js`.
- Kết quả lưu trong `backend/results`.

---

## 3. Results
> Thay các placeholder ảnh bằng các file thực tế trong `backend/results`.

### Hình 1 — Kiến trúc hệ thống
![Hình 1: Kiến trúc hệ thống](backend/results/architecture.png)
*Chú thích:* Luồng upload CSV -> backend phân tích -> lưu ảnh -> frontend hiển thị/tải.

### Hình 2 — Luồng xử lý dữ liệu
![Hình 2: Luồng xử lý dữ liệu](backend/results/data_pipeline.png)
*Chú thích:* Tiền xử lý -> EDA -> Tạo biểu đồ -> Lưu và serve.

### Hình 3 — Phân phối các chỉ số
![Phân phối các chỉ số](backend/results/2025XXXX_phan_phoi_chi_so.png)
*Chú thích:* Mô tả quan sát chính về phân bố (ví dụ: PM2.5 tập trung ở ...).

### Hình 4 — Ma trận tương quan
![Ma trận tương quan](backend/results/2025XXXX_ma_tran_tuong_quan.png)
*Chú thích:* Nêu các cặp có tương quan cao/âm mạnh.

### Hình 5 — Xu hướng thời gian
![Xu hướng thời gian](backend/results/2025XXXX_xu_huong_thoi_gian.png)

### Hình 6 — Boxplot (outliers)
![Boxplot](backend/results/2025XXXX_gia_tri_bat_thuong.png)

### Hình 7 — Phân loại AQI
![AQI categories](backend/results/2025XXXX_phan_loai_aqi.png)

---

## 4. Discussion
- Tóm tắt các quan sát chính từ các biểu đồ.
- Nguyên nhân có thể của tương quan hoặc outliers.
- Hạn chế: kích thước mẫu, chất lượng đo lường, thiếu thông tin thời gian chính xác...

---

## 5. Conclusion
- Kết luận ngắn: ghi lại các điểm quan trọng và khuyến nghị (thêm dữ liệu, kiểm tra nguồn outlier, xây dựng mô hình dự báo...)

---

## Appendix
- Code chính: `backend/app.py` (hàm phân tích `analyze_air_pollution_data`, `generate_comprehensive_plots`).
- Hướng dẫn nhanh:
```powershell
# (PowerShell)
cd c:\Users\admin\Desktop\test_project\Web_predict_weather\backend
python app.py
# Mở frontend/index.html bằng trình duyệt hoặc serve tĩnh
```

---

*Hết bản nháp.*
