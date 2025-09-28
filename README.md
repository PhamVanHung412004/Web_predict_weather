# Frontend - Ứng dụng đánh giá ô nhiễm không khí

## Mô tả
Giao diện web hiện đại cho ứng dụng đánh giá ô nhiễm không khí từ ảnh vệ tinh. Sử dụng HTML5, CSS3 và JavaScript thuần.

## Tính năng

### 🎨 Giao diện hiện đại
- Design tối giản với màu xanh dương và trắng
- Responsive cho desktop và mobile
- Hiệu ứng hover mượt mà
- Font chữ Inter hiện đại

### 📤 Upload ảnh
- Drag & drop ảnh vệ tinh
- Chọn file từ máy tính
- Preview ảnh trước khi phân tích
- Hỗ trợ JPG, PNG, TIFF

### 🔍 Phân tích AI
- Gửi ảnh đến API backend
- Hiển thị loading state
- Xử lý lỗi gracefully

### 📊 Kết quả trực quan
- Hiển thị AQI với màu sắc tương ứng
- Thông tin chi tiết về chất lượng không khí
- Bản đồ nhiệt ô nhiễm
- Các chỉ số khí tượng

## Cấu trúc thư mục
```
frontend/
├── index.html          # Trang chủ
├── css/
│   └── style.css      # Stylesheet chính
├── js/
│   └── app.js         # JavaScript chính
├── images/            # Hình ảnh tĩnh
└── README.md          # Tài liệu này
```

## Sử dụng

### 1. Mở trực tiếp
Mở file `index.html` trong trình duyệt web.

### 2. Chạy với server local
```bash
# Sử dụng Python
python -m http.server 8000

# Sử dụng Node.js
npx serve .

# Sử dụng PHP
php -S localhost:8000
```

Truy cập: http://localhost:8000

## API Integration

Frontend giao tiếp với backend qua các endpoint:

- `GET /api/health` - Kiểm tra trạng thái API

## Responsive Design

### Desktop (≥ 768px)
- Layout 2 cột cho kết quả
- Sidebar navigation
- Grid layout cho features

### Mobile (< 768px)
- Layout 1 cột
- Hamburger menu
- Touch-friendly buttons
- Optimized images

## Browser Support
- Chrome 60+
- Firefox 55+
- Safari 12+
- Edge 79+

## Customization

### Màu sắc
Chỉnh sửa CSS variables trong `style.css`:
```css
:root {
  --primary-color: #4CAF50;
  --secondary-color: #2196F3;
  --background-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
```

### API Endpoint
Thay đổi API URL trong `app.js`:
```javascript
const API_BASE_URL = 'http://localhost:5000';
```

## Performance
- Lazy loading cho images
- Minified CSS và JS
- Optimized animations
- Efficient DOM manipulation

## Accessibility
- Semantic HTML
- ARIA labels
- Keyboard navigation
- Screen reader support
- High contrast support
