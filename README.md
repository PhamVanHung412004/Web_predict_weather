# Ứng dụng Dự đoán Thời tiết AI

Ứng dụng dự đoán thời tiết sử dụng trí tuệ nhân tạo với giao diện web thân thiện, được xây dựng bằng Flask (Backend) và Next.js (Frontend).

## 🎬 Demo sản phẩm

Xem video demo ứng dụng tại đây: **[https://youtu.be/FKRR3InKK34](https://youtu.be/FKRR3InKK34)**

## 📋 Yêu cầu hệ thống

- **Python**: 3.10.18
- **Node.js**: LTS (Long Term Support)
- **Conda**: Miniconda hoặc Anaconda
- **Git**: Để clone repository

## 🚀 Hướng dẫn cài đặt

### Bước 1: Tải mã nguồn về máy

```bash
git clone https://github.com/PhamVanHung412004/Web_predict_weather.git
cd Web_predict_weather
```

### Bước 2: Cài đặt Backend (Python + Flask)

#### 2.1. Tạo môi trường ảo với Conda

```bash
conda create -n weather_env python=3.10.18
conda activate weather_env
```

#### 2.2. Cài đặt các thư viện Python

```bash
pip install -r requirements.txt
```

### Bước 3: Cài đặt Frontend (Next.js)

#### 3.1. Cài đặt Node.js

Mở **Command Prompt** hoặc **PowerShell** với **quyền Administrator** và chạy:

```bash
winget install OpenJS.NodeJS.LTS
```

> **Lưu ý**: Sau khi cài đặt xong, hãy **đóng và mở lại terminal** để hệ thống nhận Node.js.

#### 3.2. Cài đặt dependencies và khởi chạy Frontend

Mở terminal thông thường (không cần quyền admin):

```bash
cd FE_nextjs
npm install
npm run dev
```

✅ Frontend sẽ chạy tại: **http://localhost:3000**

### Bước 4: Cấu hình và khởi chạy Backend

#### 4.1. Tạo file cấu hình API Key

Tạo file `.env` trong thư mục `backend` với nội dung sau:

```env
# Danh sách API key Gemini (ngăn cách bằng dấu phẩy)
YOUR_API_KEY=AIzaSyA123abc,AIzaSyB456def,AIzaSyC789ghi,AIzaSyD012jkl,AIzaSyE345mno
```

> **💡 Khuyến nghị**: Tạo 4-5 tài khoản Gemini để có 4-5 API key khác nhau. Hệ thống sẽ tự động luân phiên sử dụng các key để tránh bị giới hạn API (rate limit).

#### 4.2. Khởi động server Flask

```bash
cd backend
python server.py
```

✅ Backend API sẽ chạy tại cổng mặc định của Flask (thường là **http://localhost:5001**)

## 📝 Cách sử dụng

1. Đảm bảo cả Backend và Frontend đều đang chạy
2. Mở trình duyệt và truy cập **http://localhost:3000**
3. Sử dụng giao diện web để dự đoán thời tiết

## 🔧 Khắc phục sự cố

- **Lỗi API key**: Kiểm tra file `.env` đã được tạo đúng trong thư mục `backend`
- **Lỗi cổng đã được sử dụng**: Đảm bảo không có ứng dụng nào khác đang chạy trên cổng 3000 hoặc 5000
- **Lỗi cài đặt packages**: Thử xóa thư mục `node_modules` và chạy lại `npm install`

## 📧 Liên hệ

Nếu gặp vấn đề, vui lòng tạo issue trên GitHub repository.