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
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import matplotlib.dates as mdates
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
try:
    from yellowbrick.cluster import KElbowVisualizer
    _YB_AVAILABLE = True
except Exception:
    _YB_AVAILABLE = False
from sklearn.ensemble import RandomForestRegressor, IsolationForest
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from PIL import Image
import cv2
from pathlib import Path
import time
import atexit
import signal

from model_gemini import Model
import yaml

# Load config
path_file_config = Path(__file__).parent.parent / "config.yaml"    
with open(path_file_config, "r", encoding="utf-8") as file:
    config = yaml.safe_load(file)

model_name = config["information_model"]["model_name"]
promt_system = config["information_model"]["prompt_system_scan_image"]

warnings.filterwarnings('ignore')

# Matplotlib config
plt.rcParams['font.family'] = ['DejaVu Sans', 'Liberation Sans', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.max_open_warning'] = 0
plt.ioff()

def cleanup_matplotlib():
    """Cleanup matplotlib figures to prevent memory leaks."""
    plt.close('all')
    matplotlib.pyplot.clf()

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
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
app.config['RESULTS_FOLDER'] = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backend/results')
app.config['MODELS_FOLDER'] = os.path.join(os.path.dirname(__file__), 'models')

# Create directories
for folder in [app.config['UPLOAD_FOLDER'], app.config['RESULTS_FOLDER'], app.config['MODELS_FOLDER']]:
    os.makedirs(folder, exist_ok=True)

ALLOWED_EXTENSIONS = {'csv'}
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg'}

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Vietnamese mappings
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
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def allowed_image_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

def get_vietnamese_name(column_name):
    """Convert column name to Vietnamese"""
    for eng, vi in POLLUTANT_NAMES_VI.items():
        if eng.lower() in column_name.lower():
            return vi
    return column_name

def classify_aqi_level(aqi_value):
    """Classify AQI pollution level"""
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

# ==================== ML FEATURE ENGINEERING ====================

def create_lag_features(df, columns, lags=[1, 3, 6, 24]):
    """Create lag features for time series"""
    df_copy = df.copy()
    
    for col in columns:
        if col in df_copy.columns:
            for lag in lags:
                df_copy[f'{col}_lag{lag}'] = df_copy[col].shift(lag)
    
    return df_copy

def create_rolling_features(df, columns, windows=[3, 12, 24]):
    """Create rolling statistics features"""
    df_copy = df.copy()
    
    for col in columns:
        if col in df_copy.columns:
            for window in windows:
                df_copy[f'{col}_rolling_mean_{window}'] = df_copy[col].rolling(window=window).mean()
                df_copy[f'{col}_rolling_std_{window}'] = df_copy[col].rolling(window=window).std()
                df_copy[f'{col}_rolling_min_{window}'] = df_copy[col].rolling(window=window).min()
                df_copy[f'{col}_rolling_max_{window}'] = df_copy[col].rolling(window=window).max()
    
    return df_copy

def create_temporal_features(df, timestamp_col=None):
    """Create temporal features if timestamp exists"""
    df_copy = df.copy()
    
    if timestamp_col and timestamp_col in df_copy.columns:
        try:
            df_copy[timestamp_col] = pd.to_datetime(df_copy[timestamp_col])
            df_copy['hour'] = df_copy[timestamp_col].dt.hour
            df_copy['day_of_week'] = df_copy[timestamp_col].dt.dayofweek
            df_copy['is_weekend'] = (df_copy['day_of_week'] >= 5).astype(int)
            df_copy['month'] = df_copy[timestamp_col].dt.month
            df_copy['day'] = df_copy[timestamp_col].dt.day
        except Exception as e:
            logger.warning(f"Could not parse timestamp: {str(e)}")
    
    return df_copy

def engineer_features(df, target_column='PM2.5', timestamp_col=None):
    """Complete feature engineering pipeline"""
    logger.info("Starting feature engineering...")
    
    # Identify numeric columns
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    
    # Remove target from feature list if exists
    feature_cols = [col for col in numeric_cols if col != target_column]
    
    # Create lag features (only for target)
    if target_column in df.columns:
        df = create_lag_features(df, [target_column], lags=[1, 3, 6, 24])
        df = create_rolling_features(df, [target_column], windows=[3, 12, 24])
    
    # Create temporal features
    df = create_temporal_features(df, timestamp_col)
    
    # Create interaction features if weather data exists
    if 'temperature' in df.columns and 'humidity' in df.columns:
        df['temp_humidity'] = df['temperature'] * df['humidity']
    
    if 'wind_speed' in df.columns:
        df['wind_speed_squared'] = df['wind_speed'] ** 2
    
    logger.info(f"Feature engineering complete. New shape: {df.shape}")
    return df

# ==================== ML MODELS ====================

def train_random_forest(X_train, y_train, X_test, y_test):
    """Train Random Forest Regressor"""
    logger.info("Training Random Forest model...")
    
    model = RandomForestRegressor(
        n_estimators=200,
        max_depth=20,
        min_samples_split=5,
        min_samples_leaf=2,
        max_features='sqrt',
        random_state=42,
        n_jobs=-1
    )
    
    model.fit(X_train, y_train)
    
    # Predictions
    y_pred_train = model.predict(X_train)
    y_pred_test = model.predict(X_test)
    
    # Metrics
    metrics = {
        'train': {
            'rmse': float(np.sqrt(mean_squared_error(y_train, y_pred_train))),
            'mae': float(mean_absolute_error(y_train, y_pred_train)),
            'r2': float(r2_score(y_train, y_pred_train))
        },
        'test': {
            'rmse': float(np.sqrt(mean_squared_error(y_test, y_pred_test))),
            'mae': float(mean_absolute_error(y_test, y_pred_test)),
            'r2': float(r2_score(y_test, y_pred_test))
        }
    }
    
    # Feature importance
    feature_importance = pd.DataFrame({
        'feature': X_train.columns,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    logger.info(f"Random Forest trained. Test R²: {metrics['test']['r2']:.4f}")
    
    return model, metrics, feature_importance

def apply_pca(X, n_components=2):
    """Apply PCA for dimensionality reduction"""
    logger.info(f"Applying PCA with {n_components} components...")
    
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    pca = PCA(n_components=n_components)
    X_pca = pca.fit_transform(X_scaled)
    
    explained_variance = pca.explained_variance_ratio_
    
    logger.info(f"PCA complete. Explained variance: {explained_variance}")
    
    return X_pca, pca, scaler, explained_variance

def apply_kmeans(X, timestamp, k_range=(1, 10)):
    """Apply KMeans using Yellowbrick KElbowVisualizer to find optimal k.

    Returns: clusters, kmeans, scaler, cluster_stats, optimal_k, elbow_plot_path
    """
    if not _YB_AVAILABLE:
        raise ImportError("yellowbrick is required for KElbowVisualizer. Please install 'yellowbrick'.")

    logger.info(f"Applying KMeans with KElbowVisualizer, k_range={k_range}...")

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Use Yellowbrick to determine optimal k
    base_model = KMeans(random_state=42, n_init=10)
    visualizer = KElbowVisualizer(base_model, k=(int(k_range[0]), int(k_range[1])), timings=False)

    # Fit visualizer
    visualizer.fit(X_scaled)

    optimal_k = int(visualizer.elbow_value_) if visualizer.elbow_value_ is not None else int(k_range[0])

    # Save elbow plot
    elbow_plot_path = os.path.join(app.config['RESULTS_FOLDER'], f"{timestamp}_ml_elbow_method.png")
    try:
        # yellowbrick 1.x supports .show(outpath=...) and .poof(outpath=...)
        if hasattr(visualizer, 'poof'):
            visualizer.poof(outpath=elbow_plot_path)
        else:
            visualizer.show(outpath=elbow_plot_path, clear_figure=True)
    except Exception as e:
        logger.error(f"Error saving elbow plot: {str(e)}")
        elbow_plot_path = None

    # Final KMeans with optimal k
    kmeans = KMeans(n_clusters=optimal_k, random_state=42, n_init=10)
    clusters = kmeans.fit_predict(X_scaled)

    # Cluster statistics
    cluster_stats = {}
    for i in range(optimal_k):
        cluster_mask = clusters == i
        cluster_stats[f'Cluster {i}'] = {
            'count': int(np.sum(cluster_mask)),
            'percentage': float(np.sum(cluster_mask) / len(clusters) * 100)
        }

    logger.info(f"KMeans complete with optimal_k={optimal_k}. Distribution: {cluster_stats}")

    return clusters, kmeans, scaler, cluster_stats, optimal_k, elbow_plot_path

def detect_anomalies_isolation_forest(X, contamination=0.05):
    """Detect anomalies using Isolation Forest"""
    logger.info("Detecting anomalies with Isolation Forest...")
    
    iso_forest = IsolationForest(
        contamination=contamination,
        random_state=42,
        n_estimators=100
    )
    
    anomaly_labels = iso_forest.fit_predict(X)
    anomaly_scores = iso_forest.score_samples(X)
    
    n_anomalies = np.sum(anomaly_labels == -1)
    anomaly_percentage = n_anomalies / len(X) * 100
    
    logger.info(f"Detected {n_anomalies} anomalies ({anomaly_percentage:.2f}%)")
    
    return anomaly_labels, anomaly_scores, iso_forest

# ==================== ML VISUALIZATIONS ====================

def plot_ml_results(df, model, X_test, y_test, y_pred, feature_importance, 
                    pca_result, clusters, anomaly_labels, timestamp):
    """Generate ML-specific visualizations"""
    plot_paths = []
    
    try:
        # 1. Predicted vs Actual
        plt.figure(figsize=(16, 10))
        sample_size = min(100, len(y_test))
        x_axis = range(sample_size)
        
        plt.plot(x_axis, y_test[:sample_size], label='Actual', color='#2E86AB', linewidth=2, marker='o', markersize=4)
        plt.plot(x_axis, y_pred[:sample_size], label='Predicted', color='#A23B72', linewidth=2, marker='s', markersize=4)
        plt.fill_between(x_axis, y_test[:sample_size], y_pred[:sample_size], alpha=0.3, color='#F18F01')
        
        plt.title('Dự báo PM2.5: So sánh giá trị thực tế và dự đoán', fontsize=16, fontweight='bold')
        plt.xlabel('Mẫu thời gian', fontsize=12)
        plt.ylabel('Nồng độ PM2.5 (µg/m³)', fontsize=12)
        plt.legend(fontsize=11)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        plot_path = os.path.join(app.config['RESULTS_FOLDER'], f"{timestamp}_ml_predicted_vs_actual.png")
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        plt.close()
        plot_paths.append(plot_path)
        
        # 2. Feature Importance
        plt.figure(figsize=(14, 10))
        top_features = feature_importance.head(15)
        colors = plt.cm.viridis(np.linspace(0, 1, len(top_features)))
        
        plt.barh(top_features['feature'], top_features['importance'], color=colors)
        plt.xlabel('Mức độ quan trọng', fontsize=12)
        plt.title('Top 15 Features quan trọng nhất (Random Forest)', fontsize=16, fontweight='bold')
        plt.gca().invert_yaxis()
        plt.tight_layout()
        
        plot_path = os.path.join(app.config['RESULTS_FOLDER'], f"{timestamp}_ml_feature_importance.png")
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        plt.close()
        plot_paths.append(plot_path)
        
        # 3. PCA 2D Visualization with Clusters
        if pca_result is not None and clusters is not None:
            plt.figure(figsize=(14, 10))
            X_pca, pca, scaler, explained_var = pca_result
            
            scatter = plt.scatter(X_pca[:, 0], X_pca[:, 1], c=clusters, cmap='viridis', 
                                 alpha=0.6, s=50, edgecolors='black', linewidth=0.5)
            
            plt.colorbar(scatter, label='Cluster')
            plt.xlabel(f'PC1 ({explained_var[0]*100:.1f}% variance)', fontsize=12)
            plt.ylabel(f'PC2 ({explained_var[1]*100:.1f}% variance)', fontsize=12)
            plt.title('PCA 2D: Phân cụm các mẫu ô nhiễm', fontsize=16, fontweight='bold')
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            
            plot_path = os.path.join(app.config['RESULTS_FOLDER'], f"{timestamp}_ml_pca_clusters.png")
            plt.savefig(plot_path, dpi=300, bbox_inches='tight')
            plt.close()
            plot_paths.append(plot_path)
        
        # 4. Anomaly Detection
        if anomaly_labels is not None and pca_result is not None:
            plt.figure(figsize=(14, 10))
            X_pca, _, _, _ = pca_result
            
            normal_mask = anomaly_labels == 1
            anomaly_mask = anomaly_labels == -1
            
            plt.scatter(X_pca[normal_mask, 0], X_pca[normal_mask, 1], 
                       c='#4ECDC4', label='Normal', alpha=0.6, s=50, edgecolors='black', linewidth=0.5)
            plt.scatter(X_pca[anomaly_mask, 0], X_pca[anomaly_mask, 1], 
                       c='#FF6B6B', label='Anomaly', alpha=0.8, s=100, marker='X', edgecolors='black', linewidth=1)
            
            plt.xlabel('PC1', fontsize=12)
            plt.ylabel('PC2', fontsize=12)
            plt.title('Phát hiện bất thường (Isolation Forest)', fontsize=16, fontweight='bold')
            plt.legend(fontsize=11)
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            
            plot_path = os.path.join(app.config['RESULTS_FOLDER'], f"{timestamp}_ml_anomaly_detection.png")
            plt.savefig(plot_path, dpi=300, bbox_inches='tight')
            plt.close()
            plot_paths.append(plot_path)
        
        # 5. Residual Plot
        plt.figure(figsize=(14, 10))
        residuals = y_test - y_pred
        
        plt.scatter(y_pred, residuals, alpha=0.6, s=50, color='#2E86AB', edgecolors='black', linewidth=0.5)
        plt.axhline(y=0, color='red', linestyle='--', linewidth=2)
        plt.xlabel('Giá trị dự đoán', fontsize=12)
        plt.ylabel('Residuals (Actual - Predicted)', fontsize=12)
        plt.title('Phân tích Residual: Đánh giá độ chính xác mô hình', fontsize=16, fontweight='bold')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        plot_path = os.path.join(app.config['RESULTS_FOLDER'], f"{timestamp}_ml_residual_plot.png")
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        plt.close()
        plot_paths.append(plot_path)
        
        return plot_paths
    
    except Exception as e:
        logger.error(f"Error generating ML plots: {str(e)}")
        return plot_paths
    finally:
        cleanup_matplotlib()

# ==================== ORIGINAL ANALYSIS FUNCTIONS (KEPT) ====================

def analyze_air_pollution_data(df):
    """Comprehensive air pollution data analysis (ORIGINAL - KEPT)"""
    try:
        numeric_df = df.select_dtypes(include=[np.number])
        
        if numeric_df.empty:
            raise ValueError("Không có dữ liệu số để phân tích")
        
        analysis_results = {}
        
        # 1. Basic statistics
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
        
        # 2. Time series data
        if len(numeric_df) > 1:
            time_series_data = {}
            sample_size = min(100, len(numeric_df))
            
            for col in numeric_df.columns[:3]:
                vi_name = get_vietnamese_name(col)
                time_series_data[vi_name] = {
                    'labels': [f"Mẫu {i+1}" for i in range(sample_size)],
                    'values': numeric_df[col].iloc[:sample_size].tolist()
                }
            
            analysis_results['time_series'] = time_series_data
        
        # 3. Distribution analysis
        distribution_data = {}
        for col in numeric_df.columns[:5]:
            vi_name = get_vietnamese_name(col)
            hist, bins = np.histogram(numeric_df[col].dropna(), bins=20)
            distribution_data[vi_name] = {
                'bins': bins[:-1].tolist(),
                'frequencies': hist.tolist(),
                'bin_width': float(bins[1] - bins[0])
            }
        
        analysis_results['distribution'] = distribution_data
        
        # 4. Correlation analysis
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
            analysis_results['correlations'] = correlations[:20]
        
        # 5. AQI analysis
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
        
        # 6. Outlier analysis (IQR)
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
                'values': outliers.tolist()[:10]
            }
        
        analysis_results['outliers'] = outliers_analysis
        
        # 7. Summary
        summary = {
            'total_samples': len(df),
            'total_features': len(numeric_df.columns),
            'missing_data_percentage': float(df.isnull().sum().sum() / (len(df) * len(df.columns)) * 100),
            'data_quality': "Tốt" if df.isnull().sum().sum() / (len(df) * len(df.columns)) < 0.05 else "Cần cải thiện"
        }
        
        analysis_results['summary'] = summary
        
        return analysis_results
    
    except Exception as e:
        logger.error(f"Error analyzing data: {str(e)}")
        raise

def generate_comprehensive_plots(df, timestamp):
    """Generate comprehensive statistical plots (ORIGINAL - KEPT)"""
    plot_paths = []
    numeric_df = df.select_dtypes(include=[np.number])
    
    try:
        # 1. Distribution plots
        if len(numeric_df.columns) >= 4:
            fig, axes = plt.subplots(2, 2, figsize=(20, 15))
            fig.suptitle('Phân phối các chỉ số ô nhiễm không khí', fontsize=20, y=0.98)
            
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
        
        # 2. Correlation matrix
        if len(numeric_df.columns) > 1:
            plt.figure(figsize=(16, 12))
            corr_matrix = numeric_df.corr()
            
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
        
        # 3. Time series trend
        if len(numeric_df) > 10:
            plt.figure(figsize=(18, 12))
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
        
        # 4. Box plot for outliers
        if len(numeric_df.columns) >= 3:
            plt.figure(figsize=(16, 10))
            box_data = []
            labels = []
            
            for col in numeric_df.columns[:6]:
                data = numeric_df[col].dropna()
                if len(data) > 0:
                    box_data.append(data)
                    labels.append(get_vietnamese_name(col))
            
            plt.boxplot(box_data, labels=labels)
            plt.title('Phân tích giá trị bất thường các chỉ số ô nhiễm', fontsize=14)
            plt.xticks(rotation=45, ha='right')
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            plot_path = os.path.join(app.config['RESULTS_FOLDER'], f"{timestamp}_gia_tri_bat_thuong.png")
            plt.savefig(plot_path, dpi=300, bbox_inches='tight')
            plt.close()
            plot_paths.append(plot_path)
        
        # 5. AQI classification pie chart
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
            
            plt.figure(figsize=(14, 10))
            categories = list(aqi_categories.keys())
            values = list(aqi_categories.values())
            
            plt.pie(values, labels=categories, colors=colors, autopct='%1.1f%%', startangle=90)
            plt.title('Phân loại chất lượng không khí theo AQI', fontsize=14)
            plot_path = os.path.join(app.config['RESULTS_FOLDER'], f"{timestamp}_phan_loai_aqi.png")
            plt.savefig(plot_path, dpi=300, bbox_inches='tight')
            plt.close()
            plot_paths.append(plot_path)
        
        # 6. Radar chart comparison
        if len(numeric_df.columns) >= 3:
            fig, ax = plt.subplots(figsize=(12, 12), subplot_kw=dict(projection='polar'))
            
            sample_data = numeric_df.iloc[:min(3, len(numeric_df))]
            categories = [get_vietnamese_name(col) for col in sample_data.columns[:6]]
            
            angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
            angles += angles[:1]
            
            colors = ['#FF6B6B', '#4ECDC4', '#45B7D1']
            
            for i, (idx, row) in enumerate(sample_data.iterrows()):
                if i >= 3:
                    break
                
                values = []
                for col in sample_data.columns[:6]:
                    min_val, max_val = numeric_df[col].min(), numeric_df[col].max()
                    if max_val > min_val:
                        normalized_val = (row[col] - min_val) / (max_val - min_val)
                    else:
                        normalized_val = 0.5
                    values.append(normalized_val)
                
                values += values[:1]
                
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
        logger.error(f"Error generating plots: {str(e)}")
        return plot_paths
    finally:
        cleanup_matplotlib()

# ==================== API ENDPOINTS ====================

@app.route('/')
def index():
    return send_from_directory('../frontend', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('../frontend', path)

@app.route('/api/analyze_csv', methods=['POST'])
def analyze_csv():
    """Enhanced CSV analysis with ML pipeline"""
    try:
        # Clear folders
        for folder in [app.config['RESULTS_FOLDER'], app.config['UPLOAD_FOLDER']]:
            if os.path.exists(folder):
                for filename in os.listdir(folder):
                    file_path = os.path.join(folder, filename)
                    try:
                        if os.path.isfile(file_path):
                            os.unlink(file_path)
                    except Exception as e:
                        logger.error(f'Error deleting file {file_path}: {e}')
            else:
                os.makedirs(folder)

        # Validate file
        if 'csv_file' not in request.files:
            return jsonify({'error': 'Không có file CSV được cung cấp'}), 400

        file = request.files['csv_file']

        if file.filename == '':
            return jsonify({'error': 'Chưa chọn file'}), 400

        if not allowed_file(file.filename):
            return jsonify({'error': 'Loại file không hợp lệ. Vui lòng upload file CSV.'}), 400

        # Save file
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        logger.info(f"Processing CSV file: {filename}")

        # Read CSV
        try:
            df = pd.read_csv(filepath)
        except Exception as e:
            return jsonify({'error': f'Lỗi đọc file CSV: {str(e)}'}), 400

        # Validate numeric data
        numeric_df = df.select_dtypes(include=[np.number])
        if numeric_df.empty:
            return jsonify({'error': 'File không chứa dữ liệu số để phân tích.'}), 400

        # === PHASE 1: Statistical Analysis (Original) ===
        logger.info("Phase 1: Statistical analysis...")
        analysis = analyze_air_pollution_data(df)
        plot_paths = generate_comprehensive_plots(df, timestamp)

        # === PHASE 2: ML Pipeline ===
        ml_results = None
        ml_plot_paths = []
        
        # Check if we have PM2.5 column for ML training
        pm25_col = None
        for col in df.columns:
            if 'pm2.5' in col.lower() or 'pm25' in col.lower():
                pm25_col = col
                break
        
        if pm25_col and len(df) >= 50:  # Need minimum data for ML
            try:
                logger.info("Phase 2: ML pipeline...")
                
                # Detect timestamp column
                timestamp_col = None
                for col in df.columns:
                    if 'time' in col.lower() or 'date' in col.lower():
                        timestamp_col = col
                        break
                
                # Feature engineering
                df_ml = engineer_features(df.copy(), target_column=pm25_col, timestamp_col=timestamp_col)
                
                # Prepare X and y
                # Drop rows with NaN (created by lag/rolling features)
                df_ml = df_ml.dropna()
                
                if len(df_ml) < 30:
                    logger.warning("Not enough data after feature engineering")
                else:
                    # Exclude target and non-numeric columns
                    feature_cols = [col for col in df_ml.columns if col != pm25_col]
                    feature_cols = df_ml[feature_cols].select_dtypes(include=[np.number]).columns.tolist()
                    
                    X = df_ml[feature_cols]
                    y = df_ml[pm25_col]
                    
                    # Time-aware split (80-20)
                    split_idx = int(len(X) * 0.8)
                    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
                    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
                    
                    logger.info(f"Train size: {len(X_train)}, Test size: {len(X_test)}")
                    
                    # Train Random Forest
                    rf_model, rf_metrics, feature_importance = train_random_forest(
                        X_train, y_train, X_test, y_test
                    )
                    
                    # Save model
                    model_path = os.path.join(app.config['MODELS_FOLDER'], f"{timestamp}_rf_pm25.joblib")
                    joblib.dump({
                        'model': rf_model,
                        'feature_columns': feature_cols,
                        'target_column': pm25_col
                    }, model_path)
                    logger.info(f"Model saved to {model_path}")
                    
                    # PCA
                    X_pca, pca_model, pca_scaler, explained_var = apply_pca(X, n_components=2)
                    pca_result = (X_pca, pca_model, pca_scaler, explained_var)
                    
                    # KMeans Clustering (Elbow via Yellowbrick)
                    clusters, kmeans_model, kmeans_scaler, cluster_stats, optimal_k, elbow_plot_path = apply_kmeans(X, timestamp, k_range=(1, 10))
                    
                    # Anomaly Detection
                    anomaly_labels, anomaly_scores, iso_forest = detect_anomalies_isolation_forest(X, contamination=0.05)
                    
                    # Generate predictions
                    y_pred = rf_model.predict(X_test)
                    
                    # Generate ML visualizations
                    ml_plot_paths = plot_ml_results(
                        df_ml, rf_model, X_test, y_test, y_pred, feature_importance,
                        pca_result, clusters, anomaly_labels, timestamp
                    )
                    if elbow_plot_path:
                        ml_plot_paths.append(elbow_plot_path)
                    
                    # Prepare ML results
                    ml_results = {
                        'random_forest': {
                            'metrics': rf_metrics,
                            'feature_importance': feature_importance.head(10).to_dict('records')
                        },
                        'pca': {
                            'explained_variance': [float(v) for v in explained_var],
                            'total_variance_explained': float(sum(explained_var))
                        },
                        'clustering': {
                            'n_clusters': int(optimal_k),
                            'cluster_distribution': cluster_stats
                        },
                        'anomaly_detection': {
                            'method': 'Isolation Forest',
                            'contamination': 0.05,
                            'n_anomalies': int(np.sum(anomaly_labels == -1)),
                            'anomaly_percentage': float(np.sum(anomaly_labels == -1) / len(anomaly_labels) * 100)
                        }
                    }
                    
                    logger.info("ML pipeline completed successfully")
            
            except Exception as e:
                logger.error(f"Error in ML pipeline: {str(e)}")
                ml_results = {'error': str(e)}
        else:
            logger.info("Skipping ML pipeline (no PM2.5 column or insufficient data)")

        # Combine all plot paths
        all_plot_paths = plot_paths + ml_plot_paths

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
                } for path in all_plot_paths
            ],
            'timestamp': datetime.now().isoformat(),
            'statistical_analysis': analysis,
            'ml_analysis': ml_results
        }

        # Clean up uploaded file
        try:
            os.remove(filepath)
        except:
            pass

        return jsonify(response)

    except Exception as e:
        logger.error(f"Error in analyze_csv: {str(e)}")
        return jsonify({'error': 'Lỗi hệ thống nội bộ', 'details': str(e)}), 500

@app.route('/api/predict', methods=['POST'])
def predict_pm25():
    """Predict PM2.5 using trained model"""
    try:
        data = request.get_json()
        
        # Find latest model
        models_dir = app.config['MODELS_FOLDER']
        model_files = [f for f in os.listdir(models_dir) if f.endswith('.joblib')]
        
        if not model_files:
            return jsonify({'error': 'Không tìm thấy mô hình đã huấn luyện'}), 404
        
        # Load latest model
        latest_model_file = sorted(model_files)[-1]
        model_path = os.path.join(models_dir, latest_model_file)
        model_data = joblib.load(model_path)
        
        model = model_data['model']
        feature_columns = model_data['feature_columns']
        
        # Prepare input features
        input_df = pd.DataFrame([data])
        
        # Check if all required features are present
        missing_features = set(feature_columns) - set(input_df.columns)
        if missing_features:
            return jsonify({
                'error': 'Thiếu features',
                'missing_features': list(missing_features)
            }), 400
        
        # Predict
        X = input_df[feature_columns]
        prediction = model.predict(X)[0]
        
        # Classify AQI
        # Rough PM2.5 to AQI conversion (simplified)
        if prediction <= 12:
            aqi = prediction * 50 / 12
        elif prediction <= 35.4:
            aqi = 50 + (prediction - 12) * 50 / (35.4 - 12)
        elif prediction <= 55.4:
            aqi = 100 + (prediction - 35.4) * 50 / (55.4 - 35.4)
        elif prediction <= 150.4:
            aqi = 150 + (prediction - 55.4) * 50 / (150.4 - 55.4)
        elif prediction <= 250.4:
            aqi = 200 + (prediction - 150.4) * 100 / (250.4 - 150.4)
        else:
            aqi = 300 + (prediction - 250.4) * 100 / (500 - 250.4)
        
        aqi_level, aqi_color = classify_aqi_level(aqi)
        
        return jsonify({
            'success': True,
            'predicted_pm25': float(prediction),
            'estimated_aqi': float(aqi),
            'aqi_level': aqi_level,
            'aqi_color': aqi_color,
            'model_used': latest_model_file,
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Error in predict_pm25: {str(e)}")
        return jsonify({'error': 'Lỗi dự báo', 'details': str(e)}), 500

def get_plot_title(filename):
    """Get plot title from filename"""
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
    elif 'ml_predicted_vs_actual' in filename:
        return '[ML] Dự báo PM2.5: Thực tế vs Dự đoán'
    elif 'ml_feature_importance' in filename:
        return '[ML] Độ quan trọng của Features'
    elif 'ml_pca_clusters' in filename:
        return '[ML] PCA 2D: Phân cụm mẫu'
    elif 'ml_anomaly_detection' in filename:
        return '[ML] Phát hiện bất thường (Isolation Forest)'
    elif 'ml_residual_plot' in filename:
        return '[ML] Phân tích Residual'
    elif 'ml_elbow_method' in filename:
        return '[ML] Elbow method: Chọn số cụm tối ưu'
    else:
        return 'Biểu đồ phân tích'

@app.route('/results/<filename>')
def serve_image(filename):
    """Serve images with CORS headers"""
    try:
        results_dir = app.config['RESULTS_FOLDER']
        if not os.path.exists(results_dir):
            os.makedirs(results_dir)

        file_path = os.path.join(results_dir, filename)
        if not os.path.exists(file_path):
            return jsonify({'error': 'File không tồn tại'}), 404

        response = send_from_directory(results_dir, filename, as_attachment=False)

        ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'png'
        if ext in ('jpg', 'jpeg'):
            response.mimetype = 'image/jpeg'
        elif ext == 'gif':
            response.mimetype = 'image/gif'
        else:
            response.mimetype = 'image/png'

        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'

        return response

    except Exception as e:
        logger.error(f'Error serving file {filename}: {str(e)}')
        return jsonify({'error': 'Lỗi khi tải file', 'details': str(e)}), 500

@app.route('/api/analyze_images_stream')
def analyze_images_stream():
    """Streaming endpoint for Gemini AI analysis with Server-Sent Events"""
    def generate():
        try:
            logger.info("Starting streaming analysis...")
            results_folder = app.config['RESULTS_FOLDER']
            
            if not os.path.exists(results_folder):
                yield f"data: {json.dumps({'error': 'Results folder does not exist'})}\n\n"
                return

            # Lọc các file ảnh và sắp xếp theo thời gian tạo mới nhất
            image_files = []
            for f in os.listdir(results_folder):
                if allowed_image_file(f):
                    file_path = os.path.join(results_folder, f)
                    # Chỉ lấy các file được tạo trong vòng 1 phút gần đây
                    if time.time() - os.path.getctime(file_path) < 60:
                        image_files.append(f)
            image_files.sort(key=lambda f: os.path.getctime(os.path.join(results_folder, f)), reverse=True)
            
            if not image_files:
                yield f"data: {json.dumps({'message': 'No image files found'})}\n\n"
                return

            logger.info(f"Found {len(image_files)} images to analyze")
            
            for i, filename in enumerate(image_files, 1):
                file_path = os.path.join(results_folder, filename)
                logger.info(f"Processing image {i}/{len(image_files)}: {filename}")

                try:
                    # Ensure file exists before analyzing
                    if not os.path.exists(file_path):
                        logger.error(f"File not found: {file_path}")
                        payload = {
                            'image': filename,
                            'title': get_plot_title(filename),
                            'analysis': {
                                'evaluation': f'File không tồn tại: {filename}',
                                'confidence': 0.0
                            }
                        }
                        yield f"event: progress\ndata: {json.dumps(payload)}\n\n"
                        continue
                        
                    analysis_result = analyze_image_with_gemini(file_path)
                    
                    payload = {
                        'image': filename,
                        'title': get_plot_title(filename),
                        'analysis': analysis_result
                    }
                    
                    yield f"event: progress\ndata: {json.dumps(payload)}\n\n"
                    logger.info(f"Successfully analyzed: {filename}")
                    
                    if i < len(image_files):
                        time.sleep(2)  # Rate limiting
                        
                except Exception as e:
                    logger.error(f"Error analyzing {filename}: {str(e)}")
                    
                    payload = {
                        'image': filename,
                        'title': get_plot_title(filename),
                        'analysis': {
                            'evaluation': f'Lỗi phân tích: {str(e)}',
                            'confidence': 0.0
                        }
                    }
                    
                    yield f"event: progress\ndata: {json.dumps(payload)}\n\n"

            # Send done signal
            yield f"data: {json.dumps({'status': 'done'})}\n\n"
            yield "event: done\ndata: {}\n\n"

        except Exception as e:
            logger.error(f"Error in streaming analysis: {str(e)}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return app.response_class(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Cache-Control'
        }
    )

@app.route('/api/results/list')
def list_results():
    """List all result images"""
    try:
        results_folder = app.config['RESULTS_FOLDER']
        
        if not os.path.exists(results_folder):
            return jsonify({'images': []})

        # Lọc các file ảnh và sắp xếp theo thời gian tạo mới nhất
        image_files = []
        current_time = time.time()
        timestamp = datetime.now().strftime("%Y%m%d")
        
        for f in os.listdir(results_folder):
            if allowed_image_file(f) and timestamp in f:  # Chỉ lấy ảnh của phiên hiện tại
                file_path = os.path.join(results_folder, f)
                # Chỉ lấy các file được tạo trong vòng 1 phút gần đây
                if current_time - os.path.getctime(file_path) < 60:
                    image_files.append(f)
        
        # Sắp xếp theo thời gian tạo mới nhất
        image_files.sort(key=lambda f: os.path.getctime(os.path.join(results_folder, f)), reverse=True)
        
        images = []
        for filename in image_files:
            images.append({
                'filename': filename,
                'title': get_plot_title(filename),
                'url': f"http://localhost:5001/results/{filename}?t={int(current_time)}"
            })

        return jsonify({
            'success': True,
            'images': images,
            'total': len(images)
        })

    except Exception as e:
        logger.error(f"Error listing results: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'hoạt động tốt',
        'message': 'Hệ thống phân tích ô nhiễm không khí đang hoạt động',
        'features': {
            'statistical_analysis': True,
            'ml_prediction': True,
            'gemini_ai_evaluation': True
        },
        'timestamp': datetime.now().isoformat()
    })

def analyze_image_with_gemini(image_path):
    """Analyze image using Gemini model (ORIGINAL - KEPT)"""
    try:
        logger.info(f"Analyzing image with Gemini: {image_path}")
        
        api_key = os.getenv("YOUR_API_KEY")
        if not api_key or api_key == "your_gemini_api_key_here":
            logger.warning("Gemini API key not configured. Using mock analysis.")
            return {
                'evaluation': f'Đây là phân tích mẫu cho ảnh {os.path.basename(image_path)}. Để sử dụng phân tích thực tế, vui lòng cấu hình Gemini API key trong file .env',
                'confidence': 0.5
            }
        
        result = Model(model_name, promt_system, image_path).Call_API_Model
        
        if isinstance(result, str):
            try:
                parsed_result = json.loads(result)
                return parsed_result
            except json.JSONDecodeError:
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
@app.route('/api/analyze_image', methods=['POST'])
def analyze_single_image():
    """Analyze a single image using Gemini AI"""
    try:
        data = request.get_json()
        filename = data.get('filename')
        
        if not filename:
            return jsonify({'error': 'Filename is required'}), 400
            
        file_path = os.path.join(app.config['RESULTS_FOLDER'], filename)
        
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
            
        analysis_result = analyze_image_with_gemini(file_path)
        
        return jsonify({
            'success': True,
            'filename': filename,
            'title': get_plot_title(filename),
            'analysis': analysis_result
        })
        
    except Exception as e:
        logger.error(f"Error analyzing image: {str(e)}")
        return jsonify({
            'error': 'Analysis failed',
            'details': str(e)
        }), 500

@app.route('/api/analyze_images', methods=['GET'])
def analyze_images():
    """Analyze all images using Gemini AI (ORIGINAL - KEPT)"""
    try:
        logger.info("Starting image analysis with Gemini AI...")
        results_folder = app.config['RESULTS_FOLDER']
        
        if not os.path.exists(results_folder):
            logger.error(f"Results folder does not exist: {results_folder}")
            return jsonify({'error': 'Results folder does not exist'}), 400

        image_files = [f for f in os.listdir(results_folder) if allowed_image_file(f)]
        
        if not image_files:
            return jsonify({
                'success': True,
                'message': 'No image files found',
                'results': []
            })

        logger.info(f"Found {len(image_files)} images to analyze")
        analysis_results = []
        error_count = 0

        for i, filename in enumerate(image_files, 1):
            file_path = os.path.join(results_folder, filename)
            logger.info(f"Processing image {i}/{len(image_files)}: {filename}")

            try:
                analysis_result = analyze_image_with_gemini(file_path)
                
                analysis_results.append({
                    'image': filename,
                    'title': get_plot_title(filename),
                    'analysis': analysis_result
                })
                
                logger.info(f"Successfully analyzed: {filename}")
                
                if i < len(image_files):
                    time.sleep(2)  # Rate limiting
                    
            except Exception as e:
                error_count += 1
                logger.error(f"Error analyzing {filename}: {str(e)}")
                
                analysis_results.append({
                    'image': filename,
                    'title': get_plot_title(filename),
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
            'details': str(e)
        }), 500

# Cleanup
def cleanup_on_exit():
    try:
        cleanup_matplotlib()
        logger.info("Cleanup completed")
    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")

atexit.register(cleanup_on_exit)

def signal_handler(signum, frame):
    logger.info(f"Received signal {signum}, cleaning up...")
    cleanup_on_exit()
    exit(0)

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

if __name__ == '__main__':
    logger.info("=== Starting Air Quality Analysis System ===")
    logger.info("Features: Statistical Analysis + ML Prediction + Gemini AI Evaluation")
    logger.info("Matplotlib backend: Agg (non-interactive)")
    
    app.run(debug=True, host='0.0.0.0', port=5001)