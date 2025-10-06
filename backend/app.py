from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import numpy as np
import pandas as pd
import json
from datetime import datetime, timedelta
import logging
from werkzeug.utils import secure_filename
import joblib
import warnings
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
import shutil
from scipy import stats
import matplotlib.dates as mdates
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from PIL import Image
import cv2
from pathlib import Path
import time
import atexit
import signal

from model_gemini import Model
import yaml

path_file_config = Path(__file__).parent.parent / "config.yaml"    

with open(path_file_config, "r", encoding="utf-8") as file:
    config = yaml.safe_load(file)

model_name = config["information_model"]["model_name"]
promt_system = config["information_model"]["prompt_system_scan_image"]



warnings.filterwarnings('ignore')

# Cấu hình matplotlib cho môi trường server
plt.rcParams['font.family'] = ['DejaVu Sans', 'Liberation Sans', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.max_open_warning'] = 0  # Tắt cảnh báo về số figure mở
plt.ioff()  # Tắt interactive mode

def cleanup_matplotlib():
    """Cleanup matplotlib figures to prevent memory leaks."""
    plt.close('all')  # Đóng tất cả figures
    matplotlib.pyplot.clf()  # Clear current figure

# Initialize Flask app
app = Flask(__name__)
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:8000", "http://127.0.0.1:8000", "http://localhost:3000", "http://127.0.0.1:3000"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['RESULTS_FOLDER'] = 'results'

# Create directories
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['RESULTS_FOLDER'], exist_ok=True)

# Allowed file extensions
ALLOWED_EXTENSIONS = {'csv'}
# Add allowed extensions for images
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_image_file(filename):
    """Check if the file has an allowed image extension."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mapping các chỉ số ô nhiễm phổ biến sang tiếng Việt
POLLUTANT_NAMES_VI = {
    'PM2.5': 'Bụi mịn PM2.5',
    'PM10': 'Bụi thô PM10',
    'NO2': 'Nitơ dioxide (NO2)',
    'SO2': 'Lưu huỳnh dioxide (SO2)',
    'CO': 'Carbon monoxide (CO)',
    'O3': 'Ozon (O3)',
    'AQI': 'Chỉ số chất lượng không khí (AQI)',
    'temperature': 'Nhiệt độ',
    'humidity': 'Độ ẩm',
    'pressure': 'Áp suất',
    'wind_speed': 'Tốc độ gió',
    'visibility': 'Tầm nhìn'
}

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Check if the file is an allowed image type.
def allowed_image_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

def get_vietnamese_name(column_name):
    """Chuyển đổi tên cột sang tiếng Việt"""
    for eng, vi in POLLUTANT_NAMES_VI.items():
        if eng.lower() in column_name.lower():
            return vi
    return column_name

def classify_aqi_level(aqi_value):
    """Phân loại mức độ ô nhiễm theo AQI"""
    if aqi_value <= 50:
        return "Tốt", "#00e400"
    elif aqi_value <= 100:
        return "Trung bình", "#ffff00"
    elif aqi_value <= 150:
        return "Không tốt cho nhóm nhạy cảm", "#ff7e00"
    elif aqi_value <= 200:
        return "Không tốt", "#ff0000"
    elif aqi_value <= 300:
        return "Rất không tốt", "#8f3f97"
    else:
        return "Nguy hiểm", "#7e0023"

def analyze_air_pollution_data(df):
    """Phân tích toàn diện dữ liệu ô nhiễm không khí"""
    try:
        numeric_df = df.select_dtypes(include=[np.number])
        
        if numeric_df.empty:
            raise ValueError("Không có dữ liệu số để phân tích")
        
        analysis_results = {}
        
        # 1. Thống kê cơ bản
        basic_stats = {}
        for col in numeric_df.columns:
            vi_name = get_vietnamese_name(col)
            basic_stats[vi_name] = {
                'mean': float(numeric_df[col].mean()),
                'std': float(numeric_df[col].std()),
                'min': float(numeric_df[col].min()),
                'max': float(numeric_df[col].max()),
                'median': float(numeric_df[col].median()),
                'q25': float(numeric_df[col].quantile(0.25)),
                'q75': float(numeric_df[col].quantile(0.75))
            }
        
        analysis_results['basic_statistics'] = basic_stats
        
        # 2. Phân tích xu hướng thời gian
        if len(numeric_df) > 1:
            time_series_data = {}
            sample_size = min(100, len(numeric_df))
            
            for col in numeric_df.columns[:3]:  # Lấy 3 cột đầu tiên
                vi_name = get_vietnamese_name(col)
                time_series_data[vi_name] = {
                    'labels': [f"Mẫu {i+1}" for i in range(sample_size)],
                    'values': numeric_df[col].iloc[:sample_size].tolist()
                }
            
            analysis_results['time_series'] = time_series_data
        
        # 3. Phân tích phân phối
        distribution_data = {}
        for col in numeric_df.columns[:5]:  # Lấy 5 cột đầu tiên
            vi_name = get_vietnamese_name(col)
            hist, bins = np.histogram(numeric_df[col].dropna(), bins=20)
            distribution_data[vi_name] = {
                'bins': bins[:-1].tolist(),
                'frequencies': hist.tolist(),
                'bin_width': float(bins[1] - bins[0])
            }
        
        analysis_results['distribution'] = distribution_data
        
        # 4. Phân tích tương quan
        if len(numeric_df.columns) > 1:
            corr_matrix = numeric_df.corr()
            correlations = []
            
            for i, col1 in enumerate(numeric_df.columns):
                for j, col2 in enumerate(numeric_df.columns):
                    if i < j:
                        corr_val = corr_matrix.iloc[i, j]
                        if not np.isnan(corr_val):
                            correlations.append({
                                'feature1': get_vietnamese_name(col1),
                                'feature2': get_vietnamese_name(col2),
                                'correlation': float(corr_val)
                            })
            
            correlations.sort(key=lambda x: abs(x['correlation']), reverse=True)
            analysis_results['correlations'] = correlations[:20]  # Top 20 correlations
        
        # 5. Phân tích chất lượng không khí (nếu có AQI)
        aqi_analysis = None
        aqi_col = None
        for col in numeric_df.columns:
            if 'aqi' in col.lower() or 'air_quality' in col.lower():
                aqi_col = col
                break
        
        if aqi_col is not None:
            aqi_values = numeric_df[aqi_col].dropna()
            aqi_levels = {'Tốt': 0, 'Trung bình': 0, 'Không tốt cho nhóm nhạy cảm': 0, 
                         'Không tốt': 0, 'Rất không tốt': 0, 'Nguy hiểm': 0}
            
            for val in aqi_values:
                level, _ = classify_aqi_level(val)
                aqi_levels[level] += 1
            
            aqi_analysis = {
                'levels': aqi_levels,
                'average_aqi': float(aqi_values.mean()),
                'max_aqi': float(aqi_values.max()),
                'min_aqi': float(aqi_values.min())
            }
        
        analysis_results['aqi_analysis'] = aqi_analysis
        
        # 6. Phân tích bất thường (outliers)
        outliers_analysis = {}
        for col in numeric_df.columns[:5]:
            data = numeric_df[col].dropna()
            Q1 = data.quantile(0.25)
            Q3 = data.quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            
            outliers = data[(data < lower_bound) | (data > upper_bound)]
            outliers_analysis[get_vietnamese_name(col)] = {
                'count': len(outliers),
                'percentage': float(len(outliers) / len(data) * 100),
                'values': outliers.tolist()[:10]  # Top 10 outliers
            }
        
        analysis_results['outliers'] = outliers_analysis
        
        # 7. Tóm tắt chung
        summary = {
            'total_samples': len(df),
            'total_features': len(numeric_df.columns),
            'missing_data_percentage': float(df.isnull().sum().sum() / (len(df) * len(df.columns)) * 100),
            'data_quality': "Tốt" if df.isnull().sum().sum() / (len(df) * len(df.columns)) < 0.05 else "Cần cải thiện"
        }
        
        analysis_results['summary'] = summary
        
        return analysis_results
    
    except Exception as e:
        logger.error(f"Lỗi khi phân tích dữ liệu: {str(e)}")
        raise

def generate_comprehensive_plots(df, timestamp):
    """Tạo các biểu đồ phân tích toàn diện"""
    plot_paths = []
    numeric_df = df.select_dtypes(include=[np.number])
    
    try:
        # 1. Biểu đồ phân phối các chỉ số ô nhiễm
        if len(numeric_df.columns) >= 4:
            fig, axes = plt.subplots(2, 2, figsize=(15, 10))
            fig.suptitle('Phân phối các chỉ số ô nhiễm không khí', fontsize=16, y=0.98)
            
            for i, col in enumerate(numeric_df.columns[:4]):
                row, col_idx = i // 2, i % 2
                ax = axes[row, col_idx]
                
                data = numeric_df[col].dropna()
                ax.hist(data, bins=30, alpha=0.7, color=plt.cm.viridis(i/4))
                ax.set_title(get_vietnamese_name(col))
                ax.set_xlabel('Giá trị')
                ax.set_ylabel('Tần suất')
                ax.grid(True, alpha=0.3)
            
            plt.tight_layout()
            plot_path = os.path.join(app.config['RESULTS_FOLDER'], f"{timestamp}_phan_phoi_chi_so.png")
            plt.savefig(plot_path, dpi=300, bbox_inches='tight')
            plt.close()
            plot_paths.append(plot_path)
        
        # 2. Ma trận tương quan (đầy đủ)
        if len(numeric_df.columns) > 1:
            plt.figure(figsize=(12, 8))
            corr_matrix = numeric_df.corr()
            
            # Đổi tên columns sang tiếng Việt
            vi_columns = [get_vietnamese_name(col) for col in corr_matrix.columns]
            corr_matrix.columns = vi_columns
            corr_matrix.index = vi_columns
            
            sns.heatmap(corr_matrix, annot=True, fmt='.2f', 
                       cmap='RdYlBu_r', center=0, square=True,
                       cbar_kws={"shrink": .8})
            plt.title('Ma trận tương quan các chỉ số ô nhiễm', fontsize=14, pad=20)
            plt.tight_layout()
            plot_path = os.path.join(app.config['RESULTS_FOLDER'], f"{timestamp}_ma_tran_tuong_quan.png")
            plt.savefig(plot_path, dpi=300, bbox_inches='tight')
            plt.close()
            plot_paths.append(plot_path)
        
        # 3. Biểu đồ xu hướng thời gian
        if len(numeric_df) > 10:
            plt.figure(figsize=(14, 8))
            sample_size = min(100, len(numeric_df))
            x_values = range(sample_size)
            
            colors = plt.cm.tab10(np.linspace(0, 1, min(5, len(numeric_df.columns))))
            
            for i, col in enumerate(numeric_df.columns[:5]):
                plt.plot(x_values, numeric_df[col].iloc[:sample_size], 
                        label=get_vietnamese_name(col), color=colors[i], linewidth=2)
            
            plt.title('Xu hướng thay đổi các chỉ số ô nhiễm theo thời gian', fontsize=14)
            plt.xlabel('Thời gian (mẫu)')
            plt.ylabel('Giá trị')
            plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            plot_path = os.path.join(app.config['RESULTS_FOLDER'], f"{timestamp}_xu_huong_thoi_gian.png")
            plt.savefig(plot_path, dpi=300, bbox_inches='tight')
            plt.close()
            plot_paths.append(plot_path)
        
        # 4. Biểu đồ hộp (Box plot) để phát hiện giá trị bất thường
        if len(numeric_df.columns) >= 3:
            plt.figure(figsize=(12, 6))
            box_data = []
            labels = []
            
            for col in numeric_df.columns[:6]:
                data = numeric_df[col].dropna()
                if len(data) > 0:
                    box_data.append(data)
                    labels.append(get_vietnamese_name(col))
            
            plt.boxplot(box_data, labels=labels)
            plt.title('Phân tích giá trị bất thường các chỉ số ô nhiễm', fontsize=14)
            plt.ylabel('Giá trị')
            plt.xticks(rotation=45, ha='right')
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            plot_path = os.path.join(app.config['RESULTS_FOLDER'], f"{timestamp}_gia_tri_bat_thuong.png")
            plt.savefig(plot_path, dpi=300, bbox_inches='tight')
            plt.close()
            plot_paths.append(plot_path)
        
        # 5. Biểu đồ phân loại chất lượng không khí (nếu có AQI)
        aqi_col = None
        for col in numeric_df.columns:
            if 'aqi' in col.lower() or 'air_quality' in col.lower():
                aqi_col = col
                break
        
        if aqi_col is not None:
            aqi_values = numeric_df[aqi_col].dropna()
            aqi_categories = {'Tốt': 0, 'Trung bình': 0, 'Không tốt cho nhóm nhạy cảm': 0,
                             'Không tốt': 0, 'Rất không tốt': 0, 'Nguy hiểm': 0}
            colors = ['#00e400', '#ffff00', '#ff7e00', '#ff0000', '#8f3f97', '#7e0023']
            
            for val in aqi_values:
                level, _ = classify_aqi_level(val)
                aqi_categories[level] += 1
            
            plt.figure(figsize=(10, 6))
            categories = list(aqi_categories.keys())
            values = list(aqi_categories.values())
            
            plt.pie(values, labels=categories, colors=colors, autopct='%1.1f%%', startangle=90)
            plt.title('Phân loại chất lượng không khí theo AQI', fontsize=14)
            plot_path = os.path.join(app.config['RESULTS_FOLDER'], f"{timestamp}_phan_loai_aqi.png")
            plt.savefig(plot_path, dpi=300, bbox_inches='tight')
            plt.close()
            plot_paths.append(plot_path)
        
        # 6. Biểu đồ so sánh các chỉ số (Radar Chart)
        if len(numeric_df.columns) >= 3:
            fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(projection='polar'))
            
            # Chuẩn hóa dữ liệu để vẽ radar chart
            sample_data = numeric_df.iloc[:min(3, len(numeric_df))]  # Lấy 3 mẫu đầu
            categories = [get_vietnamese_name(col) for col in sample_data.columns[:6]]
            
            angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
            angles += angles[:1]  # Đóng vòng tròn
            
            colors = ['#FF6B6B', '#4ECDC4', '#45B7D1']
            
            for i, (idx, row) in enumerate(sample_data.iterrows()):
                if i >= 3:  # Chỉ vẽ tối đa 3 mẫu
                    break
                
                values = []
                for col in sample_data.columns[:6]:
                    # Chuẩn hóa giá trị từ 0-1
                    min_val, max_val = numeric_df[col].min(), numeric_df[col].max()
                    if max_val > min_val:
                        normalized_val = (row[col] - min_val) / (max_val - min_val)
                    else:
                        normalized_val = 0.5
                    values.append(normalized_val)
                
                values += values[:1]  # Đóng vòng tròn
                
                ax.plot(angles, values, 'o-', linewidth=2, label=f'Mẫu {i+1}', color=colors[i])
                ax.fill(angles, values, alpha=0.25, color=colors[i])
            
            ax.set_xticks(angles[:-1])
            ax.set_xticklabels(categories)
            ax.set_ylim(0, 1)
            ax.set_title('So sánh các chỉ số ô nhiễm (Chuẩn hóa)', y=1.08, fontsize=14)
            ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.0))
            
            plot_path = os.path.join(app.config['RESULTS_FOLDER'], f"{timestamp}_so_sanh_chi_so.png")
            plt.savefig(plot_path, dpi=300, bbox_inches='tight')
            plt.close()
            plot_paths.append(plot_path)
        
        return plot_paths
    
    except Exception as e:
        logger.error(f"Lỗi khi tạo biểu đồ: {str(e)}")
        return plot_paths
    finally:
        # Cleanup matplotlib figures
        cleanup_matplotlib()

@app.route('/')
def index():
    """Serve the main page"""
    return send_from_directory('../frontend', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    """Serve static files"""
    return send_from_directory('../frontend', path)

@app.route('/api/analyze_csv', methods=['POST'])
def analyze_csv():
    """Phân tích file CSV ô nhiễm không khí và trả về ảnh kèm đánh giá."""
    try:
        # Clear results and uploads folders before processing new file
        for folder in [app.config['RESULTS_FOLDER'], app.config['UPLOAD_FOLDER']]:
            if os.path.exists(folder):
                shutil.rmtree(folder)
                os.makedirs(folder)

        # Check if file is present
        if 'csv_file' not in request.files:
            return jsonify({'error': 'Không có file CSV được cung cấp'}), 400

        file = request.files['csv_file']

        if file.filename == '':
            return jsonify({'error': 'Chưa chọn file'}), 400

        if not allowed_file(file.filename):
            return jsonify({'error': 'Loại file không hợp lệ. Vui lòng upload file CSV.'}), 400

        # Save uploaded file
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        logger.info(f"Đang xử lý file CSV: {filename}")

        # Read CSV file
        try:
            df = pd.read_csv(filepath)
        except Exception as e:
            return jsonify({'error': f'Lỗi đọc file CSV: {str(e)}'}), 400

        # Ensure there is at least one numeric column
        numeric_df = df.select_dtypes(include=[np.number])
        if numeric_df.empty:
            return jsonify({'error': 'File upload không chứa dữ liệu số để phân tích.'}), 400

        # Perform comprehensive analysis
        analysis = analyze_air_pollution_data(df)

        # Generate comprehensive plots
        plot_paths = generate_comprehensive_plots(df, timestamp)

        # Prepare response
        response = {
            'success': True,
            'message': 'Phân tích dữ liệu ô nhiễm không khí hoàn tất',
            'sample_count': len(df),
            'feature_count': len(numeric_df.columns),
            'analysis_plots': [
                {
                    'filename': os.path.basename(path),
                    'title': get_plot_title(os.path.basename(path)),
                    'url': f"http://127.0.0.1:5000/results/{os.path.basename(path)}",
                    'evaluation': f"Đánh giá cho biểu đồ {get_plot_title(os.path.basename(path))}"
                } for path in plot_paths
            ],
            'timestamp': datetime.now().isoformat(),
            'analysis_results': analysis
        }

        # Clean up uploaded file
        try:
            os.remove(filepath)
        except:
            pass

        return jsonify(response)

    except Exception as e:
        logger.error(f"Lỗi trong analyze_csv: {str(e)}")
        return jsonify({'error': 'Lỗi hệ thống nội bộ', 'details': str(e)}), 500

def get_plot_title(filename):
    """Lấy tiêu đề biểu đồ từ tên file"""
    if 'phan_phoi_chi_so' in filename:
        return 'Phân phối các chỉ số ô nhiễm'
    elif 'ma_tran_tuong_quan' in filename:
        return 'Ma trận tương quan'
    elif 'xu_huong_thoi_gian' in filename:
        return 'Xu hướng thời gian'
    elif 'gia_tri_bat_thuong' in filename:
        return 'Phân tích giá trị bất thường'
    elif 'phan_loai_aqi' in filename:
        return 'Phân loại chất lượng không khí'
    elif 'so_sanh_chi_so' in filename:
        return 'So sánh các chỉ số'
    else:
        return 'Biểu đồ phân tích'

def resize_image_with_opencv(image_path, max_width=1000):
    """Resize the image using OpenCV and overwrite the original file."""
    img = cv2.imread(image_path)
    height, width = img.shape[:2]
    if width > max_width:
        new_height = int((max_width / width) * height)
        resized_img = cv2.resize(img, (max_width, new_height), interpolation=cv2.INTER_AREA)
        cv2.imwrite(image_path, resized_img)

@app.route('/results/<filename>')
def serve_image(filename):
    """Serve resized images from the results folder."""
    original_path = os.path.join(app.config['RESULTS_FOLDER'], filename)
    resize_image_with_opencv(original_path)
    return send_from_directory(app.config['RESULTS_FOLDER'], filename)

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'hoạt động tốt',
        'message': 'Hệ thống phân tích ô nhiễm không khí đang hoạt động',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/log', methods=['POST'])
def log_message():
    """Endpoint to log messages from the frontend"""
    try:
        data = request.get_json()
        log_message = data.get('log', '')

        # Append the log message to a log file
        log_file_path = os.path.join(app.config['RESULTS_FOLDER'], 'frontend.log')
        with open(log_file_path, 'a', encoding='utf-8') as log_file:
            log_file.write(log_message)

        return jsonify({'success': True, 'message': 'Đã ghi log thành công'}), 200
    except Exception as e:
        logger.error(f"Lỗi ghi log: {str(e)}")
        return jsonify({'error': 'Không thể ghi log', 'details': str(e)}), 500

# Import Gemini model (placeholder for actual implementation)
def analyze_image_with_gemini(image_path):
    """Analyze image using Gemini model."""
    try:
        logger.info(f"Analyzing image: {image_path}")
        
        # Check if API key is configured
        api_key = os.getenv("YOUR_API_KEY")
        if not api_key or api_key == "your_gemini_api_key_here":
            logger.warning("Gemini API key not configured. Using mock analysis.")
            return {
                'evaluation': f'Đây là phân tích mẫu cho ảnh {os.path.basename(image_path)}. Để sử dụng phân tích thực tế, vui lòng cấu hình Gemini API key trong file .env',
                'confidence': 0.5
            }
        
        result = Model(model_name, promt_system, image_path).Call_API_Model
        
        # Parse the result if it's a JSON string
        if isinstance(result, str):
            try:
                # Try to parse as JSON
                parsed_result = json.loads(result)
                return parsed_result
            except json.JSONDecodeError:
                # If not JSON, return as evaluation text
                return {
                    'evaluation': result,
                    'confidence': 0.8
                }
        return result
    except Exception as e:
        logger.error(f"Error analyzing image {image_path}: {str(e)}")
        return {
            'evaluation': f'Không thể phân tích ảnh: {str(e)}',
            'confidence': 0.0
        }

@app.route('/api/test', methods=['GET'])
def test_connection():
    """Test endpoint to check if backend is accessible."""
    return jsonify({
        'success': True,
        'message': 'Backend is running and accessible',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })

@app.route('/api/analyze_images/status', methods=['GET'])
def analyze_images_status():
    """Check the status of image analysis service."""
    try:
        results_folder = app.config['RESULTS_FOLDER']
        api_key = os.getenv("YOUR_API_KEY")
        
        # Check if results folder exists
        folder_exists = os.path.exists(results_folder)
        
        # Count image files
        image_count = 0
        if folder_exists:
            image_files = [f for f in os.listdir(results_folder) if allowed_image_file(f)]
            image_count = len(image_files)
        
        # Check API key status
        api_key_configured = bool(api_key and api_key != "your_gemini_api_key_here")
        
        return jsonify({
            'success': True,
            'status': {
                'results_folder_exists': folder_exists,
                'results_folder_path': results_folder,
                'image_count': image_count,
                'api_key_configured': api_key_configured,
                'supported_formats': list(ALLOWED_IMAGE_EXTENSIONS)
            },
            'message': 'Image analysis service status retrieved successfully'
        })
        
    except Exception as e:
        logger.error(f"Error checking analyze_images status: {str(e)}")
        return jsonify({
            'error': 'Internal server error', 
            'details': str(e)
        }), 500

@app.route('/api/analyze_images', methods=['GET'])
def analyze_images():
    """Analyze all images in the results folder using the Gemini model with a delay."""
    try:
        logger.info("Starting image analysis...")
        results_folder = app.config['RESULTS_FOLDER']
        
        if not os.path.exists(results_folder):
            logger.error(f"Results folder does not exist: {results_folder}")
            return jsonify({'error': 'Results folder does not exist', 'folder': results_folder}), 400

        # Get all image files
        image_files = [f for f in os.listdir(results_folder) if allowed_image_file(f)]
        
        if not image_files:
            logger.warning("No image files found in results folder")
            return jsonify({
                'success': True,
                'message': 'No image files found in results folder',
                'results': []
            })

        logger.info(f"Found {len(image_files)} image files to analyze")
        analysis_results = []
        error_count = 0

        # Iterate through all image files in the results folder
        for i, filename in enumerate(image_files, 1):
            file_path = os.path.join(results_folder, filename)
            logger.info(f"Processing image {i}/{len(image_files)}: {filename}")

            try:
                # Analyze the image using the Gemini model
                analysis_result = analyze_image_with_gemini(file_path)
                
                analysis_results.append({
                    'image': filename,
                    'analysis': analysis_result
                })
                
                logger.info(f"Successfully analyzed: {filename}")
                
                # Delay for 2 seconds between processing each image (reduced from 5)
                if i < len(image_files):  # Don't delay after the last image
                    time.sleep(2)
                    
            except Exception as e:
                error_count += 1
                logger.error(f"Error analyzing image {filename}: {str(e)}")
                
                # Add error result for this image
                analysis_results.append({
                    'image': filename,
                    'analysis': {
                        'evaluation': f'Lỗi phân tích: {str(e)}',
                        'confidence': 0.0
                    }
                })

        success_message = f'Phân tích hoàn thành: {len(image_files) - error_count}/{len(image_files)} ảnh thành công'
        if error_count > 0:
            success_message += f', {error_count} ảnh gặp lỗi'

        return jsonify({
            'success': True,
            'message': success_message,
            'total_images': len(image_files),
            'successful_analysis': len(image_files) - error_count,
            'errors': error_count,
            'results': analysis_results
        })

    except Exception as e:
        logger.error(f"Error in analyze_images: {str(e)}")
        return jsonify({
            'error': 'Internal server error', 
            'details': str(e),
            'message': 'Có lỗi xảy ra khi phân tích ảnh'
        }), 500

# Cleanup function for app shutdown
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

if __name__ == '__main__':
    logger.info("Starting Flask application...")
    logger.info("Matplotlib backend configured as 'Agg' (non-interactive)")
    
    # Run the app
    app.run(debug=True, host='0.0.0.0', port=5000)
