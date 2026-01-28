"""
Simple Chatbot - Không dùng RAG phức tạp
Đọc trực tiếp file data và dùng Gemini để trả lời
"""

import google.generativeai as genai
import os

# Cấu hình API key
GEMINI_API_KEY = "AIzaSyAEPKOsnGnArFYckGojz-s4ymfvyhzj4Ic"
genai.configure(api_key=GEMINI_API_KEY)

# Đọc dữ liệu về thủ tục nhập học
def load_admission_data():
    """Đọc file thủ tục nhập học"""
    try:
        with open('data/Thủ tục nhập học 2025.txt', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print("⚠️ Không tìm thấy file dữ liệu.")
        return ""

# Tạo system prompt với dữ liệu thủ tục nhập học
def create_system_prompt(admission_data):
    """Tạo system prompt cho chatbot"""
    return f"""Bạn là trợ lý tư vấn thủ tục nhập học cho Trường Đại học Khoa học Tự nhiên - ĐHQG Hà Nội.

DỮ LIỆU THỦ TỤC NHẬP HỌC 2025:
{admission_data}

NHIỆM VỤ:
- Trả lời các câu hỏi về thủ tục nhập học năm 2025
- Hướng dẫn sinh viên thực hiện từng bước nhập học
- Cung cấp thông tin chính xác về học phí, hồ sơ, lịch nhập học
- Trả lời bằng tiếng Việt, thân thiện và chuyên nghiệp
- Nếu không chắc chắn về thông tin, hãy khuyên sinh viên liên hệ trực tiếp với nhà trường

CHÚ Ý:
- Luôn dựa vào dữ liệu được cung cấp ở trên
- Đưa ra thông tin chi tiết với số liệu cụ thể (ngày tháng, số tiền, địa chỉ, link...)
- Sử dụng emoji phù hợp để câu trả lời dễ đọc hơn
- Nếu câu hỏi không liên quan đến thủ tục nhập học, hãy lịch sự từ chối và hướng dẫn về chủ đề chính
"""

def test_available_models():
    """Kiểm tra các model có sẵn"""
    print("🔍 Đang kiểm tra models có sẵn...")
    try:
        models = genai.list_models()
        available_models = []
        for model in models:
            if 'generateContent' in model.supported_generation_methods:
                available_models.append(model.name)
                print(f"   ✅ {model.name}")
        return available_models
    except Exception as e:
        print(f"   ❌ Lỗi: {e}")
        return []

def main():
    """Chương trình chính"""
    print("=" * 70)
    print("🎓 CHATBOT TƯ VẤN THỦ TỤC NHẬP HỌC 2025")
    print("🏫 Trường Đại học Khoa học Tự nhiên - ĐHQG Hà Nội")
    print("=" * 70)
    print()
    
    # Load data
    print("📚 Đang load dữ liệu...")
    admission_data = load_admission_data()
    
    if not admission_data:
        print("❌ Không thể khởi động chatbot do thiếu dữ liệu.")
        return
    
    print("✅ Đã load dữ liệu thủ tục nhập học")
    print()
    
    # Test models
    available_models = test_available_models()
    
    if not available_models:
        print("\n❌ Không tìm thấy model Gemini nào có sẵn.")
        print("💡 Vui lòng kiểm tra lại API key hoặc thử key khác.")
        return
    
    # Chọn model
    model_name = available_models[0]
    print(f"\n🤖 Sử dụng model: {model_name}")
    print()
    
    # Initialize model
    try:
        model = genai.GenerativeModel(
            model_name=model_name,
            generation_config={
                'temperature': 0.7,
                'top_p': 0.9,
                'top_k': 40,
                'max_output_tokens': 1024,
            }
        )
        
        # Start chat với system prompt
        system_prompt = create_system_prompt(admission_data)
        chat = model.start_chat(history=[
            {
                'role': 'user',
                'parts': [system_prompt]
            },
            {
                'role': 'model', 
                'parts': ['Tôi đã hiểu. Tôi sẽ trả lời các câu hỏi về thủ tục nhập học năm 2025 dựa trên dữ liệu đã cung cấp.']
            }
        ])
        
        print("✅ Chatbot đã sẵn sàng!")
        print("💡 Gõ 'thoat', 'quit' hoặc 'exit' để kết thúc.")
        print("💡 Gõ 'xoa' hoặc 'clear' để bắt đầu hội thoại mới.")
        print("-" * 70)
        print()
        
        # Chat loop
        while True:
            user_input = input("🧑‍🎓 Bạn: ").strip()
            
            if not user_input:
                continue
                
            if user_input.lower() in ['thoat', 'quit', 'exit', 'bye']:
                print("\n👋 Cảm ơn bạn đã sử dụng dịch vụ. Chúc bạn nhập học thành công!")
                break
            
            if user_input.lower() in ['xoa', 'clear', 'reset']:
                chat = model.start_chat(history=[
                    {
                        'role': 'user',
                        'parts': [system_prompt]
                    },
                    {
                        'role': 'model',
                        'parts': ['Tôi đã hiểu. Tôi sẽ trả lời các câu hỏi về thủ tục nhập học năm 2025 dựa trên dữ liệu đã cung cấp.']
                    }
                ])
                print("\n🔄 Đã bắt đầu hội thoại mới.\n")
                continue
            
            # Send message
            try:
                print()
                response = chat.send_message(user_input)
                print(f"🤖 Trợ lý: {response.text}")
                print()
                print("-" * 70)
                print()
            except Exception as e:
                print(f"\n❌ Lỗi: {str(e)}")
                print("💡 Vui lòng thử lại hoặc liên hệ: 024.38581283\n")
    
    except Exception as e:
        print(f"❌ Lỗi khởi tạo chatbot: {e}")
        return


if __name__ == "__main__":
    main()
