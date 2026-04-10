# -*- coding: utf-8 -*-
"""
Flask Web App cho RAG Chatbot (Hỗ trợ nhiều tài liệu TXT, DOCX, PDF)
"""

from flask import Flask, render_template, request, jsonify
import os
from dotenv import load_dotenv

# Import RAG phases
from automation_retriever import AutomationRetriever
from phase5_llm_generation import LLMGenerator
from config import get_admission_year

# Cấu hình
load_dotenv()

GROQ_API_KEY = os.getenv('GROQ_API_KEY')
if not GROQ_API_KEY:
    raise ValueError("[WARNING] Vui lòng set GROQ_API_KEY trong file .env")

app = Flask(__name__)

# Khởi tạo RAG components (SỬ DỤNG BỘ MÁY AUTOMATION)
# Retriever bây giờ sẽ tự động Rewrite Query và Tagging Query để lọc Metadata
retriever = AutomationRetriever()
# Generator chỉ gọi duy nhất Groq và tạo câu trả lời
generator = LLMGenerator()

ADMISSION_YEAR = get_admission_year()

# Lưu chat sessions
chat_sessions = {}

@app.route('/')
def home():
    """Trang chủ"""
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    """API endpoint cho chat sử dụng RAG pipeline"""
    try:
        data = request.json
        user_message = data.get('message', '')
        session_id = data.get('session_id', 'default')
        
        if not user_message:
            return jsonify({'error': 'No message provided'}), 400
        
        # 1. Retrieve context (Tìm kiếm trong toàn bộ data/ đã index)
        print(f"[SEARCH] Đang tìm kiếm thông tin cho: {user_message}")
        chunks = retriever.retrieve(user_message, top_k=8)
        
        # 2. Phân tích intent để truyền vào generator
        analysis = retriever.query_analyzer.analyze(user_message)
        intent = analysis.get('intent', 'general')
        print(f"[TARGET] Intent: {intent}")
        
        # 3. Generate response
        # generator.generate sẽ tự động xây dựng prompt với chunks và gọi Gemini
        result = generator.generate(
            query=user_message,
            chunks=chunks,
            intent=intent,
            chat_history=None # Có thể mở rộng để dùng history của Gemini session
        )
        
        if result['success']:
            return jsonify({
                'response': result['answer'],
                'sources': [c.get('source', 'Unknown') for c in chunks[:3]]
            })
        else:
            return jsonify({
                'response': result['answer']
            })
        
    except Exception as e:
        print(f"[ERROR] Error trong app.py: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'response': f'Xin lỗi, có lỗi hệ thống xảy ra: {str(e)}'
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
    print(f"[EDUCATION] RAG CHATBOT - HỖ TRỢ ĐA TÀI LIỆU (Năm {ADMISSION_YEAR})")
    print("=" * 70)
    print()
    print("[OK] Server đang chạy tại: http://localhost:5000")
    print("[TIP] Đảm bảo bạn đã chạy phase1_chunking.py và phase2_embedding.py")
    print()
    app.run(debug=False, host='0.0.0.0', port=5000)
