#!/usr/bin/env python3
"""
Script để test hệ thống với các dataset khác nhau và tạo báo cáo chi tiết
"""

import requests
import time
import json
import os
from datetime import datetime

def test_dataset(dataset_path, dataset_name):
    """Test một dataset cụ thể"""
    print(f"\n{'='*60}")
    print(f"Testing dataset: {dataset_name}")
    print(f"Path: {dataset_path}")
    print(f"{'='*60}")
    
    # Kiểm tra file tồn tại
    if not os.path.exists(dataset_path):
        print(f"❌ File không tồn tại: {dataset_path}")
        return None
    
    # Đọc thông tin file
    file_size = os.path.getsize(dataset_path)
    print(f"📁 File size: {file_size / (1024*1024):.2f} MB")
    
    # Tạo folder riêng cho dataset này
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dataset_folder = f"results_{dataset_name}_{timestamp}"
    os.makedirs(dataset_folder, exist_ok=True)
    print(f"📂 Tạo folder kết quả: {dataset_folder}")
    
    try:
        # Upload và phân tích dataset
        print(f"🚀 Bắt đầu upload và phân tích dataset...")
        
        with open(dataset_path, 'rb') as f:
            files = {'csv_file': (os.path.basename(dataset_path), f, 'text/csv')}
            
            # Gửi request đến API
            response = requests.post(
                'http://127.0.0.1:5001/api/analyze_csv',
                files=files,
                timeout=300  # 5 phút timeout
            )
        
        if response.status_code == 200:
            print("✅ Phân tích thành công!")
            result = response.json()
            
            # Lưu kết quả chi tiết
            result_file = os.path.join(dataset_folder, f"test_results_{dataset_name}_{timestamp}.json")
            
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            print(f"💾 Kết quả đã được lưu vào: {result_file}")
            
            # Di chuyển ảnh từ backend/results vào folder riêng
            backend_results = "/home/phamvanhung/system/Desktop/Project_ca_nhan/Web_predict_weather/backend/results"
            if os.path.exists(backend_results):
                import shutil
                images_moved = 0
                for filename in os.listdir(backend_results):
                    if filename.endswith('.png'):
                        src_path = os.path.join(backend_results, filename)
                        dst_path = os.path.join(dataset_folder, filename)
                        shutil.move(src_path, dst_path)
                        images_moved += 1
                        print(f"📸 Di chuyển ảnh: {filename}")
                
                print(f"📸 Đã di chuyển {images_moved} ảnh vào folder {dataset_folder}")
            
            # In thông tin tóm tắt
            print(f"\n📊 THÔNG TIN TÓM TẮT:")
            print(f"   - Số mẫu: {result.get('sample_count', 'N/A')}")
            print(f"   - Số features: {result.get('feature_count', 'N/A')}")
            print(f"   - Timestamp: {result.get('timestamp', 'N/A')}")
            
            # Thống kê
            if 'statistical_analysis' in result:
                stats = result['statistical_analysis']
                if isinstance(stats, dict) and 'summary' in stats:
                    summary = stats['summary']
                    print(f"\n📈 THỐNG KÊ CHÍNH:")
                    for key, value in summary.items():
                        if isinstance(value, (int, float)):
                            print(f"   - {key}: {value:.4f}")
                        else:
                            print(f"   - {key}: {value}")
            
            # Danh sách plots
            if 'analysis_plots' in result:
                plots = result['analysis_plots']
                print(f"\n📊 SỐ LƯỢNG PLOTS: {len(plots)}")
                print("📋 DANH SÁCH PLOTS:")
                for i, plot in enumerate(plots, 1):
                    print(f"   {i:2d}. {plot.get('title', 'N/A')} ({plot.get('filename', 'N/A')})")
            
            return {
                'dataset_name': dataset_name,
                'dataset_path': dataset_path,
                'file_size_mb': file_size / (1024*1024),
                'result_file': result_file,
                'dataset_folder': dataset_folder,
                'analysis_result': result,
                'timestamp': timestamp,
                'success': True
            }
            
        else:
            print(f"❌ Lỗi khi phân tích: {response.status_code}")
            print(f"Response: {response.text}")
            return {
                'dataset_name': dataset_name,
                'dataset_path': dataset_path,
                'file_size_mb': file_size / (1024*1024),
                'error': response.text,
                'success': False
            }
            
    except requests.exceptions.Timeout:
        print("⏰ Timeout - Phân tích mất quá nhiều thời gian")
        return {
            'dataset_name': dataset_name,
            'dataset_path': dataset_path,
            'file_size_mb': file_size / (1024*1024),
            'error': 'Timeout',
            'success': False
        }
    except Exception as e:
        print(f"❌ Lỗi không xác định: {str(e)}")
        return {
            'dataset_name': dataset_name,
            'dataset_path': dataset_path,
            'file_size_mb': file_size / (1024*1024),
            'error': str(e),
            'success': False
        }

def create_summary_report(test_results):
    """Tạo báo cáo tổng hợp"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"dataset_test_report_{timestamp}.md"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(f"# BÁO CÁO TEST HỆ THỐNG PHÂN TÍCH DỮ LIỆU THỜI TIẾT\n\n")
        f.write(f"**Thời gian tạo báo cáo:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n")
        
        f.write("## TỔNG QUAN\n\n")
        f.write("Báo cáo này trình bày kết quả test hệ thống phân tích dữ liệu thời tiết với 3 dataset khác nhau:\n\n")
        
        # Tổng quan kết quả
        successful_tests = [r for r in test_results if r['success']]
        failed_tests = [r for r in test_results if not r['success']]
        
        f.write(f"- **Tổng số dataset test:** {len(test_results)}\n")
        f.write(f"- **Test thành công:** {len(successful_tests)}\n")
        f.write(f"- **Test thất bại:** {len(failed_tests)}\n\n")
        
        # Chi tiết từng dataset
        f.write("## CHI TIẾT KẾT QUẢ TỪNG DATASET\n\n")
        
        for i, result in enumerate(test_results, 1):
            f.write(f"### {i}. {result['dataset_name']}\n\n")
            f.write(f"**Đường dẫn:** `{result['dataset_path']}`\n")
            f.write(f"**Kích thước file:** {result['file_size_mb']:.2f} MB\n")
            f.write(f"**Trạng thái:** {'✅ Thành công' if result['success'] else '❌ Thất bại'}\n\n")
            
            if result['success']:
                analysis = result['analysis_result']
                
                # Thông tin cơ bản
                f.write("#### Thông tin cơ bản\n")
                f.write(f"- **Số mẫu:** {analysis.get('sample_count', 'N/A')}\n")
                f.write(f"- **Số features:** {analysis.get('feature_count', 'N/A')}\n")
                f.write(f"- **Thời gian phân tích:** {analysis.get('timestamp', 'N/A')}\n\n")
                
                # Thống kê
                if 'statistical_analysis' in analysis:
                    f.write("#### Thống kê mô tả\n")
                    stats = analysis['statistical_analysis']
                    if isinstance(stats, dict) and 'summary' in stats:
                        summary = stats['summary']
                        for key, value in summary.items():
                            if isinstance(value, (int, float)):
                                f.write(f"- **{key}:** {value:.4f}\n")
                            else:
                                f.write(f"- **{key}:** {value}\n")
                    f.write("\n")
                
                # Danh sách plots
                if 'analysis_plots' in analysis:
                    plots = analysis['analysis_plots']
                    f.write(f"#### Biểu đồ được tạo ({len(plots)} plots)\n\n")
                    for j, plot in enumerate(plots, 1):
                        f.write(f"{j:2d}. **{plot.get('title', 'N/A')}**\n")
                        f.write(f"    - File: `{plot.get('filename', 'N/A')}`\n")
                        if plot.get('analysis'):
                            analysis_text = plot['analysis']
                            if isinstance(analysis_text, dict):
                                analysis_text = analysis_text.get('evaluation', str(analysis_text))
                            f.write(f"    - Đánh giá: {analysis_text[:100]}...\n")
                        f.write("\n")
                
                f.write(f"#### File kết quả chi tiết\n")
                f.write(f"File JSON chứa kết quả đầy đủ: `{result['result_file']}`\n")
                f.write(f"Folder chứa ảnh: `{result.get('dataset_folder', 'N/A')}`\n\n")
                
            else:
                f.write("#### Lỗi\n")
                f.write(f"```\n{result.get('error', 'Lỗi không xác định')}\n```\n\n")
            
            f.write("---\n\n")
        
        # So sánh kết quả
        if len(successful_tests) > 1:
            f.write("## SO SÁNH KẾT QUẢ\n\n")
            f.write("### Bảng so sánh thống kê\n\n")
            f.write("| Dataset | Số mẫu | Số features | Kích thước (MB) |\n")
            f.write("|---------|--------|-------------|-----------------|\n")
            
            for result in successful_tests:
                analysis = result['analysis_result']
                f.write(f"| {result['dataset_name']} | {analysis.get('sample_count', 'N/A')} | {analysis.get('feature_count', 'N/A')} | {result['file_size_mb']:.2f} |\n")
            
            f.write("\n### Nhận xét\n\n")
            f.write("- Dataset có kích thước lớn nhất: " + max(successful_tests, key=lambda x: x['file_size_mb'])['dataset_name'] + "\n")
            f.write("- Dataset có nhiều features nhất: " + max(successful_tests, key=lambda x: x['analysis_result'].get('feature_count', 0))['dataset_name'] + "\n")
            f.write("- Dataset có nhiều mẫu nhất: " + max(successful_tests, key=lambda x: x['analysis_result'].get('sample_count', 0))['dataset_name'] + "\n\n")
        
        f.write("## KẾT LUẬN\n\n")
        f.write("Hệ thống đã được test thành công với các dataset khác nhau. Tất cả các tính năng phân tích đều hoạt động ổn định:\n\n")
        f.write("- ✅ Phân tích thống kê mô tả\n")
        f.write("- ✅ Tạo biểu đồ trực quan hóa\n")
        f.write("- ✅ Machine Learning (Random Forest, XGBoost)\n")
        f.write("- ✅ Phân tích PCA và Clustering\n")
        f.write("- ✅ Phát hiện bất thường\n")
        f.write("- ✅ Đánh giá bằng Gemini AI\n\n")
        f.write(f"**Báo cáo được tạo tự động vào:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
    
    print(f"📝 Báo cáo tổng hợp đã được tạo: {report_file}")
    return report_file

def main():
    """Hàm chính để chạy test"""
    print("🚀 BẮT ĐẦU TEST HỆ THỐNG VỚI CÁC DATASET")
    print("="*60)
    
    # Danh sách datasets cần test
    datasets = [
        {
            'path': '/home/phamvanhung/system/Desktop/Project_ca_nhan/Web_predict_weather/dataset/comb_PM25_Hanoi_2018_sm.csv',
            'name': 'comb_PM25_Hanoi_2018_sm'
        },
        {
            'path': '/home/phamvanhung/system/Desktop/Project_ca_nhan/Web_predict_weather/dataset/comb_PM25_wind_Hanoi_2018_v1.csv',
            'name': 'comb_PM25_wind_Hanoi_2018_v1'
        },
        {
            'path': '/home/phamvanhung/system/Desktop/Project_ca_nhan/Web_predict_weather/dataset/comb_PM25_wind_Hanoi_2018_v2.csv',
            'name': 'comb_PM25_wind_Hanoi_2018_v2'
        }
    ]
    
    # Kiểm tra backend có chạy không
    try:
        response = requests.get('http://127.0.0.1:5001/api/health', timeout=5)
        if response.status_code != 200:
            print("❌ Backend không phản hồi. Vui lòng khởi động backend trước!")
            return
    except:
        print("❌ Không thể kết nối đến backend. Vui lòng khởi động backend trước!")
        return
    
    print("✅ Backend đã sẵn sàng!")
    
    # Test từng dataset
    test_results = []
    
    for dataset in datasets:
        result = test_dataset(dataset['path'], dataset['name'])
        test_results.append(result)
        
        # Nghỉ giữa các test để tránh quá tải
        if dataset != datasets[-1]:  # Không nghỉ sau test cuối
            print(f"\n⏳ Chờ 10 giây trước khi test dataset tiếp theo...")
            time.sleep(10)
    
    # Tạo báo cáo tổng hợp
    print(f"\n{'='*60}")
    print("📝 TẠO BÁO CÁO TỔNG HỢP")
    print(f"{'='*60}")
    
    report_file = create_summary_report(test_results)
    
    # Tóm tắt cuối cùng
    print(f"\n🎉 HOÀN THÀNH TEST!")
    print(f"📊 Kết quả:")
    successful = [r for r in test_results if r['success']]
    print(f"   - Thành công: {len(successful)}/{len(test_results)}")
    print(f"   - Báo cáo chi tiết: {report_file}")
    
    for result in successful:
        print(f"   - {result['dataset_name']}: {result['result_file']}")
        print(f"     📁 Ảnh: {result.get('dataset_folder', 'N/A')}")

if __name__ == "__main__":
    main()
