# Hướng dẫn sửa lỗi tkinter trong matplotlib

## Vấn đề
```
RuntimeError: main thread is not in main loop
Exception ignored in: <function Variable.__del__ at 0x7a781d1d7d90>
```

## Nguyên nhân
Lỗi này xảy ra khi matplotlib cố gắng sử dụng tkinter backend (GUI) trong môi trường server không có GUI hoặc khi chạy trong background thread.

## Giải pháp đã áp dụng

### 1. ✅ Cấu hình matplotlib backend
```python
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
```

### 2. ✅ Cấu hình matplotlib cho môi trường server
```python
plt.rcParams['font.family'] = ['DejaVu Sans', 'Liberation Sans', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.max_open_warning'] = 0  # Tắt cảnh báo về số figure mở
plt.ioff()  # Tắt interactive mode
```

### 3. ✅ Thêm hàm cleanup
```python
def cleanup_matplotlib():
    """Cleanup matplotlib figures to prevent memory leaks."""
    plt.close('all')  # Đóng tất cả figures
    matplotlib.pyplot.clf()  # Clear current figure
```

### 4. ✅ Cleanup tự động khi tạo biểu đồ
```python
def generate_comprehensive_plots(df, timestamp):
    try:
        # ... tạo biểu đồ ...
        return plot_paths
    except Exception as e:
        logger.error(f"Lỗi khi tạo biểu đồ: {str(e)}")
        return plot_paths
    finally:
        # Cleanup matplotlib figures
        cleanup_matplotlib()
```

### 5. ✅ Cleanup khi ứng dụng shutdown
```python
import atexit
import signal

def cleanup_on_exit():
    """Cleanup matplotlib on app exit."""
    try:
        cleanup_matplotlib()
        logger.info("Matplotlib cleanup completed on exit")
    except Exception as e:
        logger.error(f"Error during matplotlib cleanup: {str(e)}")

# Register cleanup function
atexit.register(cleanup_on_exit)

# Signal handlers for graceful shutdown
def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    logger.info(f"Received signal {signum}, cleaning up...")
    cleanup_on_exit()
    exit(0)

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)
```

## Cách test

### 1. Khởi động backend
```bash
cd backend
source weather/bin/activate  # Nếu sử dụng virtual environment
python app.py
```

### 2. Kiểm tra log
Backend sẽ hiển thị:
```
INFO:__main__:Starting Flask application...
INFO:__main__:Matplotlib backend configured as 'Agg' (non-interactive)
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5000
 * Running on http://[::1]:5000
```

### 3. Test tạo biểu đồ
- Upload file CSV và phân tích
- Kiểm tra không có lỗi tkinter trong console
- Biểu đồ được tạo thành công trong thư mục `results/`

### 4. Test shutdown
- Nhấn Ctrl+C để dừng server
- Kiểm tra log cleanup:
```
INFO:__main__:Received signal 2, cleaning up...
INFO:__main__:Matplotlib cleanup completed on exit
```

## Lưu ý

### ✅ Backend 'Agg' 
- Không cần GUI
- Hoạt động tốt trong môi trường server
- Vẫn tạo được file ảnh PNG chất lượng cao

### ✅ Cleanup tự động
- Đóng tất cả figure sau khi tạo biểu đồ
- Cleanup khi ứng dụng shutdown
- Xử lý signal SIGTERM/SIGINT

### ✅ Error handling
- Xử lý lỗi trong quá trình tạo biểu đồ
- Logging chi tiết
- Graceful shutdown

## Troubleshooting

### Nếu vẫn gặp lỗi tkinter:
1. Kiểm tra matplotlib version:
   ```bash
   pip show matplotlib
   ```

2. Cài đặt lại matplotlib nếu cần:
   ```bash
   pip uninstall matplotlib
   pip install matplotlib
   ```

3. Kiểm tra environment variables:
   ```bash
   echo $DISPLAY  # Nên trống trong môi trường server
   ```

4. Thêm vào đầu script nếu cần:
   ```python
   import os
   os.environ['MPLBACKEND'] = 'Agg'
   ```

Bây giờ backend sẽ hoạt động mà không gặp lỗi tkinter! 🎉
