import google.generativeai as genai
from PIL import Image
import os
from dotenv import load_dotenv



load_dotenv()
api_key: str = os.getenv("YOUR_API_KEY")

# Cấu hình API key
genai.configure(api_key=api_key)

def read_image(image_input) -> Image:
    """Đọc ảnh từ đường dẫn hoặc bytes.
    
    Args:
        image_input: Đường dẫn file ảnh hoặc bytes của ảnh
    
    Returns:
        Đối tượng PIL.Image đã mở
    """
    if isinstance(image_input, str):
        # Nếu là đường dẫn file
        return Image.open(image_input)
    elif isinstance(image_input, bytes):
        # Nếu là bytes
        import io
        return Image.open(io.BytesIO(image_input))
    else:
        # Nếu đã là PIL Image
        return image_input

class Model:
    """Wrapper gọi Gemini để trích xuất thông tin từ ảnh danh thiếp."""
    def __init__(self, model_name: str, prompt_system_scan_image: str, path_image) -> None:
        self.__model_name: str = model_name
        self.__prompt_system_scan_image: str = prompt_system_scan_image
        self.__path_image = path_image

    @property
    def Call_API_Model(self) -> str:
        """Gọi API generate_content với prompt và ảnh.
        
        Returns:
            Chuỗi JSON (đã convert) chứa thông tin trích xuất từ ảnh
        """
        model = genai.GenerativeModel(self.__model_name)
        
        image = read_image(self.__path_image)
        system_prompt = self.__prompt_system_scan_image
        response = model.generate_content([system_prompt, image])
        return response.text

