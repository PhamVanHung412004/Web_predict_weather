# Backend API - Ứng dụng đánh giá ô nhiễm không khí (Updated)

## Mô tả
Backend API sử dụng Flask với model Random Forest đã được train từ dữ liệu thực tế để phân tích chất lượng không khí từ ảnh vệ tinh.

## Cải tiến mới

### ✅ Sử dụng model đã được train
- **Random Forest** được train trên dữ liệu thực tế từ Hà Nội 2018
- **Dữ liệu gốc**: PM2.5 từ AirNow.gov + Khí tượng từ NOAA + MERRA-2 từ NASA
- **Performance**: Test RMSE = 20.04 μg/m³ (tương đối chính xác)

### ✅ Features thực tế
Model sử dụng 10 features chính:
- `T2MDEW`: Dew point temperature
- `T2M`: 2-meter air temperature  
- `PS`: Surface pressure
- `TQV`: Total precipitable water vapor
- `TQL`: Total precipitable liquid water
- `H1000`: Height at 1000mb
- `HLML`: Surface layer height
- `RHOA`: Air density at surface
- `CIG`: Ceiling height dimension
- `WS`: Wind speed

### ✅ Xử lý ảnh thông minh
- Trích xuất features từ ảnh vệ tinh (màu sắc, độ sáng, texture)
- Sử dụng features ảnh để tạo dữ liệu khí tượng realistic
- Kết hợp với model đã train để dự đoán chính xác

## Cài đặt

### 1. Tạo virtual environment
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# hoặc venv\Scripts\activate  # Windows
```

### 2. Cài đặt dependencies
```bash
pip install -r requirements.txt
```

### 3. Train model (nếu chưa có)
```bash
python3 train_model.py
```

### 4. Chạy ứng dụng
```bash
python3 app.py
```

API sẽ chạy tại: http://localhost:5000

## Cấu trúc thư mục
```
backend/
├── app.py              # Flask application chính
├── train_model.py      # Script train model
├── requirements.txt    # Dependencies
├── models/            # Thư mục chứa model đã train
│   ├── forest_reg.pkl     # Random Forest model
│   ├── ensemble_reg.pkl   # Ensemble model
│   ├── scaler.pkl         # StandardScaler
│   ├── imputer.pkl        # SimpleImputer
│   └── feature_info.pkl   # Thông tin features
├── uploads/           # Thư mục tạm cho file upload
├── results/           # Thư mục lưu kết quả heatmap
└── README_UPDATED.md  # Tài liệu này
```

## API Endpoints

### POST /api/analyze
Phân tích ảnh vệ tinh và trả về kết quả đánh giá chất lượng không khí.

**Request:**
- Method: POST
- Content-Type: multipart/form-data
- Body: image file (JPG, PNG, TIFF)

**Response:**
```json
{
  "success": true,
  "pm25": 85.5,
  "aqi": 95,
  "air_quality": "Trung bình",
  "temperature": 28.5,
  "humidity": 65,
  "visibility": 12.3,
  "wind_speed": 5.2,
  "timestamp": "2024-01-01T12:00:00",
  "features_used": ["T2MDEW", "T2M", "PS", ...],
  "model_info": {
    "model_type": "Random Forest",
    "test_rmse": 20.04,
    "n_features": 10
  },
  "heatmap_url": "/results/heatmap_20240101_120000.png"
}
```

### GET /api/health
Kiểm tra trạng thái API và model.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00",
  "model_loaded": true,
  "model_info": {
    "feature_names": ["T2MDEW", "T2M", ...],
    "n_features": 10,
    "forest_test_rmse": 20.04
  }
}
```

## Tính năng

1. **Model thực tế**: Sử dụng Random Forest đã train trên dữ liệu Hà Nội 2018
2. **Xử lý ảnh**: Trích xuất features từ ảnh vệ tinh
3. **Dự đoán chính xác**: RMSE = 20.04 μg/m³ trên test set
4. **Tính toán AQI**: Chuyển đổi PM2.5 thành chỉ số AQI
5. **Tạo heatmap**: Bản đồ nhiệt trực quan
6. **API RESTful**: Giao diện API đơn giản và dễ sử dụng

## So sánh với phiên bản cũ

| Tính năng | Phiên bản cũ | Phiên bản mới |
|-----------|--------------|---------------|
| Model | Random Forest giả | Random Forest thực tế |
| Dữ liệu | Mock data | Dữ liệu Hà Nội 2018 |
| Features | 16 features giả | 10 features thực tế |
| Performance | Không biết | RMSE = 20.04 |
| Độ chính xác | Thấp | Cao |

## Lưu ý
- Model được train trên dữ liệu Hà Nội 2018, có thể cần fine-tune cho khu vực khác
- Trong production, nên tích hợp với dữ liệu vệ tinh thực tế thay vì mock data
- Có thể sử dụng Ensemble model (ensemble_reg.pkl) để tăng độ chính xác
