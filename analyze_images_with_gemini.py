#!/usr/bin/env python3
"""
Script để phân tích từng ảnh bằng Gemini AI và cập nhật báo cáo
"""

import requests
import json
import os
import time
from datetime import datetime

def analyze_image_with_gemini(image_path, dataset_name):
    """Phân tích một ảnh bằng Gemini AI"""
    try:
        # Kiểm tra file tồn tại
        if not os.path.exists(image_path):
            print(f"❌ File không tồn tại: {image_path}")
            return None
        
        filename = os.path.basename(image_path)
        print(f"🔍 Phân tích ảnh: {filename}")
        
        # Copy ảnh vào backend/results folder trước
        backend_results = "/home/phamvanhung/system/Desktop/Project_ca_nhan/Web_predict_weather/backend/results"
        import shutil
        backend_image_path = os.path.join(backend_results, filename)
        shutil.copy2(image_path, backend_image_path)
        
        # Gửi request đến API phân tích ảnh (chỉ cần filename)
        data = {
            'filename': filename
        }
        
        response = requests.post(
            'http://127.0.0.1:5001/api/analyze_image',
            json=data,
            headers={'Content-Type': 'application/json'},
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Phân tích thành công: {filename}")
            return result.get('analysis', {})
        else:
            print(f"❌ Lỗi phân tích: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Lỗi không xác định: {str(e)}")
        return None

def analyze_all_images_in_folder(folder_path, dataset_name):
    """Phân tích tất cả ảnh trong folder"""
    print(f"\n{'='*60}")
    print(f"Phân tích ảnh cho dataset: {dataset_name}")
    print(f"Folder: {folder_path}")
    print(f"{'='*60}")
    
    if not os.path.exists(folder_path):
        print(f"❌ Folder không tồn tại: {folder_path}")
        return {}
    
    # Lấy danh sách file PNG
    png_files = [f for f in os.listdir(folder_path) if f.endswith('.png')]
    png_files.sort()  # Sắp xếp theo tên
    
    print(f"📊 Tìm thấy {len(png_files)} ảnh cần phân tích")
    
    analyses = {}
    
    for i, filename in enumerate(png_files, 1):
        print(f"\n[{i}/{len(png_files)}] Phân tích: {filename}")
        
        image_path = os.path.join(folder_path, filename)
        analysis = analyze_image_with_gemini(image_path, dataset_name)
        
        if analysis:
            analyses[filename] = analysis
            print(f"✅ Hoàn thành phân tích: {filename}")
        else:
            print(f"❌ Thất bại phân tích: {filename}")
        
        # Nghỉ giữa các request để tránh rate limit
        if i < len(png_files):
            print("⏳ Chờ 2 giây...")
            time.sleep(2)
    
    return analyses

def update_report_with_analyses():
    """Cập nhật báo cáo với phân tích Gemini AI"""
    # Danh sách các folder cần phân tích
    folders = [
        {
            'path': 'results_comb_PM25_Hanoi_2018_sm_20251011_121424',
            'name': 'comb_PM25_Hanoi_2018_sm'
        },
        {
            'path': 'results_comb_PM25_wind_Hanoi_2018_v1_20251011_121456',
            'name': 'comb_PM25_wind_Hanoi_2018_v1'
        },
        {
            'path': 'results_comb_PM25_wind_Hanoi_2018_v2_20251011_121529',
            'name': 'comb_PM25_wind_Hanoi_2018_v2'
        }
    ]
    
    all_analyses = {}
    
    # Phân tích từng folder
    for folder in folders:
        analyses = analyze_all_images_in_folder(folder['path'], folder['name'])
        all_analyses[folder['name']] = analyses
    
    # Lưu kết quả phân tích
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    analysis_file = f"gemini_analyses_{timestamp}.json"
    
    with open(analysis_file, 'w', encoding='utf-8') as f:
        json.dump(all_analyses, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Đã lưu kết quả phân tích vào: {analysis_file}")
    
    return all_analyses, analysis_file

def main():
    """Hàm chính"""
    print("🚀 BẮT ĐẦU PHÂN TÍCH ẢNH BẰNG GEMINI AI")
    print("="*60)
    
    # Kiểm tra backend
    try:
        response = requests.get('http://127.0.0.1:5001/api/health', timeout=5)
        if response.status_code != 200:
            print("❌ Backend không phản hồi. Vui lòng khởi động backend trước!")
            return
    except:
        print("❌ Không thể kết nối đến backend. Vui lòng khởi động backend trước!")
        return
    
    print("✅ Backend đã sẵn sàng!")
    
    # Bắt đầu phân tích
    try:
        all_analyses, analysis_file = update_report_with_analyses()
        
        # Thống kê kết quả
        total_images = sum(len(analyses) for analyses in all_analyses.values())
        successful_analyses = sum(len(analyses) for analyses in all_analyses.values())
        
        print(f"\n🎉 HOÀN THÀNH PHÂN TÍCH!")
        print(f"📊 Thống kê:")
        print(f"   - Tổng số ảnh: {total_images}")
        print(f"   - Phân tích thành công: {successful_analyses}")
        print(f"   - File kết quả: {analysis_file}")
        
        # In chi tiết từng dataset
        for dataset_name, analyses in all_analyses.items():
            print(f"\n📁 {dataset_name}:")
            print(f"   - Số ảnh đã phân tích: {len(analyses)}")
            for filename, analysis in analyses.items():
                if analysis:
                    evaluation = analysis.get('evaluation', 'Không có đánh giá')
                    confidence = analysis.get('confidence', 0)
                    print(f"   ✅ {filename}: {evaluation[:50]}... (Độ tin cậy: {confidence:.2f})")
                else:
                    print(f"   ❌ {filename}: Phân tích thất bại")
        
    except Exception as e:
        print(f"❌ Lỗi trong quá trình phân tích: {str(e)}")

if __name__ == "__main__":
    main()
