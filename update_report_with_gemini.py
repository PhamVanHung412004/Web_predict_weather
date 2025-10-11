#!/usr/bin/env python3
"""
Script để cập nhật báo cáo với phân tích Gemini AI
"""

import json
import re

def load_gemini_analyses():
    """Load phân tích Gemini AI từ file JSON"""
    with open('gemini_analyses_20251011_120801.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def get_analysis_for_image(analyses, dataset_name, filename):
    """Lấy phân tích cho một ảnh cụ thể"""
    if dataset_name in analyses and filename in analyses[dataset_name]:
        analysis = analyses[dataset_name][filename]
        evaluation = analysis.get('evaluation', '')
        confidence = analysis.get('confidence', 0)
        return evaluation, confidence
    return None, 0

def format_analysis_text(evaluation):
    """Format text phân tích để hiển thị đẹp"""
    if not evaluation:
        return ""
    
    # Tách các phần chính
    lines = evaluation.split('\n')
    formatted_lines = []
    
    for line in lines:
        line = line.strip()
        if line.startswith('🧩'):
            # Tìm text sau emoji
            text = line[1:].strip()
            if text.startswith('1.'):
                text = text[2:].strip()
            formatted_lines.append(f"\n🧩 **Mô tả ngắn gọn:**")
        elif line.startswith('📊'):
            text = line[1:].strip()
            if text.startswith('2.'):
                text = text[2:].strip()
            formatted_lines.append(f"\n📊 **Phân tích chuyên sâu:**")
        elif line.startswith('💡'):
            text = line[1:].strip()
            if text.startswith('3.'):
                text = text[2:].strip()
            formatted_lines.append(f"\n💡 **Nhận định & Ý nghĩa:**")
        elif line.startswith('🚀'):
            text = line[1:].strip()
            if text.startswith('4.'):
                text = text[2:].strip()
            formatted_lines.append(f"\n🚀 **Đề xuất:**")
        elif line.startswith('•'):
            formatted_lines.append(f"- {line[1:].strip()}")
        elif line.startswith('-'):
            formatted_lines.append(f"- {line[1:].strip()}")
        elif line and not line.startswith('**') and not line.startswith('🧩') and not line.startswith('📊') and not line.startswith('💡') and not line.startswith('🚀'):
            formatted_lines.append(line)
    
    return '\n'.join(formatted_lines)

def update_report():
    """Cập nhật báo cáo với phân tích Gemini AI"""
    analyses = load_gemini_analyses()
    
    # Đọc file báo cáo hiện tại
    with open('dataset_test_report_20251011_115040.md', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Mapping dataset names
    dataset_mapping = {
        'comb_PM25_Hanoi_2018_sm': 'comb_PM25_Hanoi_2018_sm',
        'comb_PM25_wind_Hanoi_2018_v1': 'comb_PM25_wind_Hanoi_2018_v1', 
        'comb_PM25_wind_Hanoi_2018_v2': 'comb_PM25_wind_Hanoi_2018_v2'
    }
    
    # Pattern để tìm các biểu đồ
    pattern = r'!\[([^\]]+)\]\(([^)]+)\)\n\*\*(\d+)\. ([^*]+)\*\*\n- File: `([^`]+)`'
    
    def replace_image_section(match):
        title = match.group(1)
        image_path = match.group(2)
        number = match.group(3)
        description = match.group(4)
        filename = match.group(5)
        
        # Xác định dataset từ image path
        dataset_name = None
        for ds in dataset_mapping.keys():
            if ds in image_path:
                dataset_name = ds
                break
        
        if dataset_name:
            evaluation, confidence = get_analysis_for_image(analyses, dataset_name, filename)
            
            if evaluation:
                formatted_analysis = format_analysis_text(evaluation)
                confidence_text = f"\n**Độ tin cậy:** {confidence:.1%}" if confidence > 0 else ""
                
                return f"""![{title}]({image_path})
**{number}. {description}**
- File: `{filename}`

**Đánh giá của Gemini AI:**
{formatted_analysis}{confidence_text}"""
        
        return match.group(0)
    
    # Thay thế tất cả các section
    updated_content = re.sub(pattern, replace_image_section, content, flags=re.MULTILINE)
    
    # Lưu file đã cập nhật
    with open('dataset_test_report_20251011_115040.md', 'w', encoding='utf-8') as f:
        f.write(updated_content)
    
    print("✅ Đã cập nhật báo cáo với phân tích Gemini AI!")

if __name__ == "__main__":
    update_report()
