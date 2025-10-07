import google.generativeai as genai
from PIL import Image
import os
import itertools
import re
from dotenv import load_dotenv

# --- Load biến môi trường ---
load_dotenv()

# Đọc danh sách key từ file .env
API_KEYS = os.getenv("YOUR_API_KEY").split(",")
key_cycle = itertools.cycle(API_KEYS)  # tạo vòng lặp key

def configure_next_key():
    """Chọn key kế tiếp và cấu hình lại Gemini."""
    api_key = next(key_cycle)
    genai.configure(api_key=api_key)
    print(f"[🔑] Đang sử dụng key: {api_key[:10]}...")  # chỉ in vài ký tự đầu
    return api_key


def read_image(image_input) -> Image:
    """Đọc ảnh từ đường dẫn hoặc bytes."""
    if isinstance(image_input, str):
        return Image.open(image_input)
    elif isinstance(image_input, bytes):
        import io
        return Image.open(io.BytesIO(image_input))
    else:
        return image_input


def clean_analysis_text(text: str) -> str:
    """Làm sạch và định dạng văn bản phân tích biểu đồ."""
    text = text.strip()
    text = re.sub(r'\n{2,}', '\n', text)

    replacements = {
        r'\*\*1\..*Mô tả.*\*\*': '🧩 **1. Mô tả ngắn gọn:**',
        r'\*\*2\..*Phân tích.*\*\*': '📊 **2. Phân tích chuyên sâu:**',
        r'\*\*3\..*Nhận định.*\*\*': '💡 **3. Nhận định & Ý nghĩa:**',
        r'\*\*4\..*Đề xuất.*\*\*': '🚀 **4. Đề xuất:**',
    }
    for pattern, replacement in replacements.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    text = re.sub(r'^\*\s+', '• ', text, flags=re.MULTILINE)
    text = re.sub(r'\n\s*\*\s+', '\n• ', text)
    text = text.replace('**', '')
    return text.strip()


class Model:
    """Wrapper gọi Gemini để trích xuất thông tin từ ảnh."""
    def __init__(self, model_name: str, prompt_system_scan_image: str, path_image) -> None:
        self.__model_name = model_name
        self.__prompt_system_scan_image = prompt_system_scan_image
        self.__path_image = path_image

    @property
    def Call_API_Model(self) -> str:
        """Gọi API Gemini và xử lý giới hạn."""
        for _ in range(len(API_KEYS)):
            api_key = configure_next_key()
            model = genai.GenerativeModel(self.__model_name)
            image = read_image(self.__path_image)
            try:
                response = model.generate_content([self.__prompt_system_scan_image, image])
                return clean_analysis_text(response.text)
            except Exception as e:
                error_str = str(e)
                print(f"[⚠️] Lỗi với key {api_key[:10]}...: {error_str}")
                if "429" in error_str or "quota" in error_str.lower():
                    print("[🔁] Thử key tiếp theo...")
                    continue  # chuyển sang key kế
                raise e  # lỗi khác thì dừng luôn
        raise RuntimeError("Tất cả API key đều bị giới hạn hoặc lỗi.")
