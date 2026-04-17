# -*- coding: utf-8 -*-
"""
Flask Web App cho RAG Chatbot (Hỗ trợ nhiều tài liệu TXT, DOCX, PDF)
"""

from flask import Flask, render_template, request, jsonify, Response, stream_with_context
import os
import sys
import json
import hashlib
from typing import Dict, Any
from dotenv import load_dotenv

# Đảm bảo console Windows in được tiếng Việt
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Import RAG phases
from automation_retriever import AutomationRetriever as HybridRetriever
from phase5_llm_generation import LLMGenerator
from response_cache import get_cache
from config import get_admission_year

# Cấu hình
load_dotenv()

GROQ_API_KEY = os.getenv('GROQ_API_KEY')
if not GROQ_API_KEY:
    raise ValueError("[WARNING] Vui lòng set GROQ_API_KEY trong file .env")

app = Flask(__name__)

# Khởi tạo RAG components
# Retriever dùng để tìm kiếm context từ ChromaDB (đã index tất cả file trong data/)
retriever = HybridRetriever()
# Generator dùng Groq API và tạo câu trả lời từ context
generator = LLMGenerator(GROQ_API_KEY)

ADMISSION_YEAR = get_admission_year()

# Lưu chat sessions (history theo user/session)
chat_sessions = {}
MAX_HISTORY_TURNS = 20


def _resolve_user_id(payload: dict) -> str:
    user_id = (request.headers.get('X-User-Id') or '').strip()
    if user_id:
        return user_id
    if payload:
        user_id = str(payload.get('user_id', '')).strip()
        if user_id:
            return user_id
    return 'anonymous'


def _session_key(user_id: str, session_id: str) -> str:
    return f"{user_id}::{session_id}"


def _style_id_from_history(history: list, session_key: str) -> str:
    """Luân phiên style theo lượt + biến thể cố định theo session để giảm trùng câu chữ."""
    assistant_turns = sum(1 for t in history if (t.get('role') or '').lower() == 'assistant')
    styles = ['formal', 'friendly', 'concise']

    seed_hex = hashlib.sha256((session_key or '').encode('utf-8')).hexdigest()
    style_seed = int(seed_hex[:8], 16)
    variant_seed = int(seed_hex[8:16], 16)

    base_style = styles[(assistant_turns + (style_seed % len(styles))) % len(styles)]
    variant = (assistant_turns + variant_seed) % 3
    return f"{base_style}_v{variant}"


@app.route('/')
def home():
    """Trang chủ"""
    return render_template('index.html')


@app.route('/chat', methods=['POST'])
def chat():
    """API endpoint cho chat sử dụng RAG pipeline"""
    try:
        data = request.json or {}
        user_message = data.get('message', '')
        session_id = data.get('session_id', 'default')
        user_id = _resolve_user_id(data)
        session_key = _session_key(user_id, session_id)

        if not user_message:
            return jsonify({'error': 'No message provided'}), 400

        # 1. Nạp history theo session/user
        history = chat_sessions.get(session_key, [])

        # 2. Retrieve context (Tìm kiếm trong toàn bộ data/ đã index)
        print(f"[SEARCH] Đang tìm kiếm thông tin cho: {user_message}")
        chunks = retriever.retrieve(user_message, top_k=8, chat_history=history)

        # 3. Phân tích intent/query frame để truyền vào generator
        analysis = retriever.query_analyzer.analyze(user_message, chat_history=history)
        intent = analysis.get('intent', 'general')
        query_frame = analysis.get('query_frame', {})
        print(f"[TARGET] Intent: {intent}")
        if query_frame:
            print(f"[FRAME] scope={query_frame.get('scope')} nav={query_frame.get('nav_target_candidates', [])}")

        # 4. Chặn câu hỏi ngoài phạm vi dữ liệu tuyển sinh
        if intent == 'general':
            answer = (
                "Mình chỉ có dữ liệu về thủ tục nhập học, nên chưa có thông tin cho câu hỏi này.\n"
                "Bạn có thể hỏi về: học phí, hồ sơ, lịch nhập học, xác nhận nhập học hoặc các bước thủ tục."
            )
            history.append({'role': 'user', 'content': user_message})
            history.append({'role': 'assistant', 'content': answer})
            if len(history) > MAX_HISTORY_TURNS:
                history = history[-MAX_HISTORY_TURNS:]
            chat_sessions[session_key] = history
            return jsonify({'response': answer, 'sources': []})

        # 5. Generate response
        # giữ contract UI cũ (response) nhưng có thể truyền analysis mở rộng nội bộ về sau.
        style_id = _style_id_from_history(history, session_key=session_key)
        result = generator.generate(
            query=user_message,
            chunks=chunks,
            intent=intent,
            chat_history=history,
            analysis=analysis,
            session_id=session_id,
            user_id=user_id,
            style_id=style_id
        )
        result['style_id'] = style_id
        print(f"[STYLE] style_id={style_id}")

        if result.get('success'):
            # Lưu lại history gần nhất (không đổi UX hiển thị)
            history.append({'role': 'user', 'content': user_message})
            history.append({'role': 'assistant', 'content': result.get('answer', '')})
            if len(history) > MAX_HISTORY_TURNS:
                history = history[-MAX_HISTORY_TURNS:]
            chat_sessions[session_key] = history

            return jsonify({
                'response': result.get('answer', ''),
                'sources': [c.get('source', 'Unknown') for c in chunks[:3]]
            })

        return jsonify({
            'response': result.get('answer', 'Xin lỗi, tôi chưa thể phản hồi lúc này.')
        })

    except Exception as e:
        print(f"[ERROR] Error trong app.py: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'response': f'Xin lỗi, có lỗi hệ thống xảy ra: {str(e)}'
        })


@app.route('/chat/stream', methods=['POST'])
def chat_stream():
    """API endpoint streaming (SSE) - không ảnh hưởng /chat hiện tại."""

    def _event(name: str, payload: Dict[str, Any]) -> str:
        return f"event: {name}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"

    @stream_with_context
    def generate_stream():
        try:
            data = request.json or {}
            user_message = data.get('message', '')
            session_id = data.get('session_id', 'default')
            user_id = _resolve_user_id(data)
            session_key = _session_key(user_id, session_id)

            if not user_message:
                yield _event('error', {'message': 'No message provided'})
                return

            history = chat_sessions.get(session_key, [])
            chunks = retriever.retrieve(user_message, top_k=8, chat_history=history)
            analysis = retriever.query_analyzer.analyze(user_message, chat_history=history)
            intent = analysis.get('intent', 'general')
            query_frame = analysis.get('query_frame', {})
            if query_frame:
                print(f"[FRAME] stream scope={query_frame.get('scope')} nav={query_frame.get('nav_target_candidates', [])}")

            if intent == 'general':
                answer = (
                    "Mình chỉ có dữ liệu về thủ tục nhập học, nên chưa có thông tin cho câu hỏi này.\n"
                    "Bạn có thể hỏi về: học phí, hồ sơ, lịch nhập học, xác nhận nhập học hoặc các bước thủ tục."
                )
                history.append({'role': 'user', 'content': user_message})
                history.append({'role': 'assistant', 'content': answer})
                if len(history) > MAX_HISTORY_TURNS:
                    history = history[-MAX_HISTORY_TURNS:]
                chat_sessions[session_key] = history

                chunk_size = 80
                for i in range(0, len(answer), chunk_size):
                    yield _event('chunk', {'text': answer[i:i + chunk_size]})
                yield _event('done', {'sources': [], 'success': True, 'style_id': 'domain_guard'})
                return

            style_id = _style_id_from_history(history, session_key=session_key)
            result = generator.generate(
                query=user_message,
                chunks=chunks,
                intent=intent,
                chat_history=history,
                analysis=analysis,
                session_id=session_id,
                user_id=user_id,
                style_id=style_id
            )
            result['style_id'] = style_id
            print(f"[STYLE] stream style_id={style_id}")

            answer = result.get('answer', '')
            if result.get('success'):
                history.append({'role': 'user', 'content': user_message})
                history.append({'role': 'assistant', 'content': answer})
                if len(history) > MAX_HISTORY_TURNS:
                    history = history[-MAX_HISTORY_TURNS:]
                chat_sessions[session_key] = history

            # Streaming theo chunk nhỏ để client có thể render dần
            chunk_size = 80
            for i in range(0, len(answer), chunk_size):
                yield _event('chunk', {'text': answer[i:i + chunk_size]})

            yield _event('done', {
                'sources': [c.get('source', 'Unknown') for c in chunks[:3]],
                'success': bool(result.get('success', False)),
                'style_id': result.get('style_id')
            })

        except Exception as e:
            yield _event('error', {'message': str(e)})

    return Response(generate_stream(), mimetype='text/event-stream')


@app.route('/reset', methods=['POST'])
def reset():
    """Reset chat session"""
    try:
        data = request.json or {}
        session_id = data.get('session_id', 'default')
        user_id = _resolve_user_id(data)
        session_key = _session_key(user_id, session_id)

        if session_key in chat_sessions:
            del chat_sessions[session_key]

        cache = get_cache()
        cache.clear_session(session_id=session_id, user_id=user_id)

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
