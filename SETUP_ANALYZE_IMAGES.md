# Hướng dẫn cấu hình tính năng phân tích ảnh

## Vấn đề đã được sửa

Endpoint `/api/analyze_images` trước đây không hoạt động do:
1. ❌ Thiếu hàm `allowed_image_file()`
2. ❌ Xử lý lỗi không đầy đủ
3. ❌ Không có kiểm tra API key
4. ❌ Không có endpoint kiểm tra trạng thái

## Các cải tiến đã thực hiện

### ✅ Backend (app.py)
1. **Thêm hàm `allowed_image_file()`** - kiểm tra định dạng ảnh hợp lệ
2. **Cải thiện `analyze_image_with_gemini()`** - xử lý lỗi và kiểm tra API key
3. **Cải thiện endpoint `/api/analyze_images`** - logging chi tiết, xử lý lỗi tốt hơn
4. **Thêm endpoint `/api/analyze_images/status`** - kiểm tra trạng thái hệ thống

### ✅ Frontend (app.js + index.html)
1. **Thêm nút "Kiểm tra trạng thái"** - kiểm tra trước khi phân tích
2. **Cải thiện hàm `analyzeImages()`** - hiển thị tiến trình và thống kê
3. **Thêm hàm `checkAnalysisStatus()`** - kiểm tra trạng thái chi tiết
4. **Cải thiện UI** - thêm section phân tích ảnh riêng biệt

## Cách sử dụng

### 1. Kiểm tra trạng thái
- Nhấn nút **"Kiểm tra trạng thái"** để xem:
  - ✅ Thư mục kết quả có tồn tại không
  - 📊 Số lượng ảnh có sẵn
  - 🔑 API key đã được cấu hình chưa
  - 📋 Định dạng ảnh được hỗ trợ

### 2. Phân tích ảnh
- Nhấn nút **"Phân tích ảnh"** để:
  - 🤖 Phân tích tất cả ảnh trong thư mục `results/`
  - 📈 Hiển thị kết quả phân tích từ Gemini AI
  - 📊 Hiển thị thống kê quá trình phân tích

### 3. Cấu hình API Key (tùy chọn)

Để sử dụng phân tích thực tế với Gemini AI:

1. **Lấy API key từ Google:**
   ```
   https://makersuite.google.com/app/apikey
   ```

2. **Tạo file `.env` trong thư mục `backend/`:**
   ```env
   YOUR_API_KEY=your_actual_gemini_api_key_here
   ```

3. **Khởi động lại backend**

**Lưu ý:** Nếu không cấu hình API key, hệ thống sẽ sử dụng phân tích mẫu.

## Các endpoint mới

### `GET /api/analyze_images/status`
Kiểm tra trạng thái hệ thống phân tích ảnh.

**Response:**
```json
{
  "success": true,
  "status": {
    "results_folder_exists": true,
    "results_folder_path": "results",
    "image_count": 5,
    "api_key_configured": false,
    "supported_formats": ["png", "jpg", "jpeg"]
  },
  "message": "Image analysis service status retrieved successfully"
}
```

### `GET /api/analyze_images` (đã cải thiện)
Phân tích tất cả ảnh trong thư mục results.

**Response:**
```json
{
  "success": true,
  "message": "Phân tích hoàn thành: 5/5 ảnh thành công",
  "total_images": 5,
  "successful_analysis": 5,
  "errors": 0,
  "results": [
    {
      "image": "chart1.png",
      "analysis": {
        "evaluation": "Biểu đồ cho thấy xu hướng tăng...",
        "confidence": 0.8
      }
    }
  ]
}
```

## Xử lý lỗi

Hệ thống hiện tại xử lý các lỗi sau:
- ❌ Thư mục results không tồn tại
- ❌ Không có ảnh nào để phân tích
- ❌ API key chưa được cấu hình
- ❌ Lỗi khi phân tích từng ảnh
- ❌ Lỗi kết nối mạng

Tất cả lỗi đều được ghi log chi tiết và hiển thị thông báo rõ ràng cho người dùng.

## Test endpoint

Bạn có thể test endpoint bằng cách:

1. **Kiểm tra trạng thái:**
   ```bash
   curl http://127.0.0.1:5000/api/analyze_images/status
   ```

2. **Phân tích ảnh:**
   ```bash
   curl http://127.0.0.1:5000/api/analyze_images
   ```

Hoặc sử dụng giao diện web với các nút đã được thêm vào.
