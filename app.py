"""
Flask Web App cho Chatbot Thủ Tục Nhập Học
"""

from flask import Flask, render_template, request, jsonify
import google.generativeai as genai

app = Flask(__name__)

# Cấu hình
GEMINI_API_KEY = "AIzaSyAEPKOsnGnArFYckGojz-s4ymfvyhzj4Ic"
genai.configure(api_key=GEMINI_API_KEY)

# Load dữ liệu
def load_admission_data():
    """Đọc file thủ tục nhập học"""
    try:
        with open('data/Thủ tục nhập học 2025.txt', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return ""

ADMISSION_DATA = load_admission_data()

# System prompt
SYSTEM_PROMPT = f"""Bạn là trợ lý tư vấn thủ tục nhập học cho Trường Đại học Khoa học Tự nhiên - ĐHQG Hà Nội.

DỮ LIỆU THỦ TỤC NHẬP HỌC 2025:
{ADMISSION_DATA}

NHIỆM VỤ:
- Trả lời các câu hỏi về thủ tục nhập học năm 2025
- Hướng dẫn sinh viên thực hiện từng bước nhập học
- Cung cấp thông tin chính xác về học phí, hồ sơ, lịch nhập học
- Trả lời bằng tiếng Việt, thân thiện và chuyên nghiệp
- Sử dụng emoji phù hợp để câu trả lời dễ đọc hơn

CHÚ Ý:
- Luôn dựa vào dữ liệu được cung cấp
- Đưa ra thông tin chi tiết với số liệu cụ thể
- Nếu không chắc chắn, khuyên sinh viên liên hệ: 024.38581283 hoặc ctsv@hus.edu.vn
"""

# Lưu chat sessions
chat_sessions = {}

def get_model():
    """Lấy model có sẵn"""
    try:
        models = genai.list_models()
        for model in models:
            if 'generateContent' in model.supported_generation_methods:
                return model.name
    except:
        pass
    return None

MODEL_NAME = get_model()

@app.route('/')
def home():
    """Trang chủ"""
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    """API endpoint cho chat"""
    try:
        data = request.json
        user_message = data.get('message', '')
        session_id = data.get('session_id', 'default')
        
        if not user_message:
            return jsonify({'error': 'No message provided'}), 400
        
        if not MODEL_NAME:
            return jsonify({
                'response': 'Xin lỗi, không thể kết nối với AI model. Vui lòng liên hệ: 024.38581283'
            })
        
        # Tạo hoặc lấy chat session
        if session_id not in chat_sessions:
            model = genai.GenerativeModel(
                model_name=MODEL_NAME,
                generation_config={
                    'temperature': 0.7,
                    'max_output_tokens': 1024,
                }
            )
            chat_sessions[session_id] = model.start_chat(history=[
                {
                    'role': 'user',
                    'parts': [SYSTEM_PROMPT]
                },
                {
                    'role': 'model',
                    'parts': ['Tôi đã hiểu. Tôi sẽ trả lời các câu hỏi về thủ tục nhập học năm 2025.']
                }
            ])
        
        # Send message
        chat = chat_sessions[session_id]
        response = chat.send_message(user_message)
        
        return jsonify({
            'response': response.text
        })
        
    except Exception as e:
        return jsonify({
            'response': f'Xin lỗi, có lỗi xảy ra: {str(e)}\n\nVui lòng liên hệ: 024.38581283 hoặc ctsv@hus.edu.vn'
        })

@app.route('/reset', methods=['POST'])
def reset():
    """Reset chat session"""
    try:
        data = request.json
        session_id = data.get('session_id', 'default')
        
        if session_id in chat_sessions:
            del chat_sessions[session_id]
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("=" * 70)
    print("🎓 CHATBOT WEB - THỦ TỤC NHẬP HỌC 2025")
    print("=" * 70)
    print()
    print("✅ Server đang chạy tại: http://localhost:5000")
    print("💡 Nhấn Ctrl+C để dừng server")
    print()
    app.run(debug=True, host='0.0.0.0', port=5000)
