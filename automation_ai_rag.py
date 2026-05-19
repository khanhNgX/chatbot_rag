# -*- coding: utf-8 -*-
"""
AUTOMATION AI-RAG PIPELINE
Tự động hóa toàn bộ quy trình: Chunking (AI) -> Tagging (AI) -> Query Rewriting (AI)
Sử dụng Groq API.
"""

import json
import re
import os
import requests
from typing import List, Dict, Any
from dotenv import load_dotenv

from config import get_admission_year

load_dotenv()
GROQ_API_KEY = (os.getenv('GROQ_API_KEY') or '').strip()
GROQ_MODEL_TEXT = (os.getenv('GROQ_MODEL_TEXT') or 'llama-3.3-70b-versatile').strip()
ADMISSION_YEAR = get_admission_year()
ADMISSION_YEAR_STR = str(ADMISSION_YEAR)

# Cấu hình tập hợp nhãn (Metadata Keywords) cho tuyển sinh
TOPIC_SET = {
    'fee': 'Thông tin về học phí, lệ phí, tiền nong',
    'admission_docs': 'Hồ sơ, giấy tờ, bằng cấp cần nộp',
    'schedule': 'Thời gian, lịch trình, hạn chót',
    'procedure': 'Quy trình, các bước thực hiện',
    'contact': 'Địa chỉ, số điện thoại, email liên hệ',
    'major_info': 'Thông tin về ngành học, chương trình đào tạo',
    'location': 'Địa điểm nhập học, bản đồ, phòng ban',
    'general': 'Thông tin chung khác'
}

class AIService:
    """Tương tác với Groq để xử lý AI-Tasks."""

    def call(self, system_prompt: str, user_prompt: str, json_mode: bool = False) -> str:
        if not GROQ_API_KEY:
            print("[AI ERROR] missing_GROQ_API_KEY")
            return ""

        payload = {
            'model': GROQ_MODEL_TEXT,
            'temperature': 0.1,
            'max_tokens': 1200,
            'messages': [
                {'role': 'system', 'content': (system_prompt + "\n\nTrả về JSON object hợp lệ." if json_mode else system_prompt)},
                {'role': 'user', 'content': user_prompt}
            ]
        }

        try:
            response = requests.post(
                'https://api.groq.com/openai/v1/chat/completions',
                headers={
                    'Authorization': f'Bearer {GROQ_API_KEY}',
                    'content-type': 'application/json'
                },
                json=payload,
                timeout=45
            )
            if response.status_code == 429:
                print("[AI ERROR] quota")
                return ""
            if response.status_code != 200:
                print(f"[AI ERROR] API {response.status_code}: {response.text[:300]}")
                return ""

            result = response.json()
            choices = result.get('choices') or []
            if not choices:
                print("[AI ERROR] empty_choices")
                return ""
            text = ((choices[0].get('message') or {}).get('content') or '').strip()
            return text
        except Exception as e:
            print(f"[AI ERROR] {e}")
            return ""


class AIAutomation:
    """Class điều phối toàn bộ quy trình Automation"""

    def __init__(self):
        self.ai = AIService()
        
    # --- BƯỚC 1: AI HIERARCHICAL CHUNKING (Advanced Granular) ---
    def auto_hierarchical_scan(self, raw_text: str, source: str) -> List[Dict]:
        """Dùng AI phân tích sâu để tạo cấu trúc CHA-CON đa tầng"""
        print(f"[AUTO] Đang bóc tách phân cấp chi tiết cho: {source}")
        
        system_prompt = f"""Bạn là chuyên gia bóc tách dữ liệu tuyển sinh.
Nhiệm vụ: Chia tài liệu thành các PHẦN LỚN (Parents) và các Ý NHỎ CHI TIẾT (Children).
Tập hợp nhãn (topics): {list(TOPIC_SET.keys())}

QUY TẮC PHÂN CHIA (BẮT BUỘC):
1. GIỮ NỘI DUNG Ở PARENT: Parent chunk PHẢI chứa ĐẦY ĐỦ nội dung gốc của phần đó để làm ngữ cảnh nền.
2. KHÔNG CHIA QUÁ NHỎ: Không được chia mỗi dòng hay mỗi loại giấy tờ thành 1 Child. Hãy gom nhóm các thông tin liên quan chặt chẽ vào 1 Child (Ví dụ: Toàn bộ danh sách hồ sơ bản chính là 1 child, danh sách hồ sơ nộp sau là 1 child).
3. BÓC TÁCH LỊCH (SCHEDULE): Gom nhóm lịch theo NGÀY. Một Child nên chứa toàn bộ các ngành nhập học trong cùng 1 ngày (cả sáng và chiều) để tránh mất ngữ cảnh.
4. CHI TIẾT GIẤY TỜ: Tuyệt đối không chia mỗi loại giấy tờ thành 1 Child. Hãy giữ danh sách hồ sơ đầy đủ trong Parent hoặc gom vào tối đa 2-3 Child lớn theo nhóm mục đích.
5. KHÔNG ĐƯỢC BỎ SÓT: Phải quét hết toàn bộ văn bản từ đầu đến cuối.

Yêu cầu định dạng JSON:
{{
  "sections": [
    {{
      "parent_title": "Tiêu đề mục lớn",
      "parent_content": "Nội dung gốc của mục này",
      "topic": "nhãn",
      "children": [
        {{
          "child_title": "Ý nhỏ chi tiết",
          "child_content": "Nội dung gốc chi tiết",
          "keywords": ["từ khóa"]
        }}
      ]
    }}
  ]
}}"""
        
        all_final_chunks = []
        user_prompt = f"Tài liệu {source}:\n\n{raw_text}"
        
        result_json = self.ai.call(system_prompt, user_prompt, json_mode=True)
        if not result_json: return []
        
        try:
            data = json.loads(result_json)
            sections = data.get('sections', [])
            for s_idx, sec in enumerate(sections):
                parent_id = f"p_{s_idx}_{source[:10]}"
                # Lưu Cha
                all_final_chunks.append({
                    "chunk_id": parent_id,
                    "title": sec.get("parent_title"),
                    "content": sec.get("parent_content"),
                    "topic": sec.get("topic", "general"),
                    "level": "parent",
                    "source": source
                })
                # Lưu Con
                for c_idx, child in enumerate(sec.get("children", [])):
                    all_final_chunks.append({
                        "chunk_id": f"{parent_id}_c_{c_idx}",
                        "parent_id": parent_id,
                        "title": child.get("child_title"),
                        "content": child.get("child_content"),
                        "topic": sec.get("topic", "general"),
                        "keywords": child.get("keywords", []),
                        "level": "child",
                        "source": source
                    })
            return all_final_chunks
        except Exception as e:
            print(f"[HIERARCHY ERROR] {e}")
            return []

    # --- BƯỚC 2: QUERY REWRITER & TAGGING --- (Giữ nguyên)
    def process_user_query(self, query: str) -> Dict[str, Any]:
        """Tối ưu hóa câu hỏi của người dùng và gán nhãn để lọc"""
        system_prompt = f"""Nhiệm vụ:
1. Viết lại câu hỏi của người dùng cho rõ ràng, đầy đủ ý nghĩa (Query Expansion).
2. Phân loại câu hỏi vào các chủ đề tuyển sinh: {list(TOPIC_SET.keys())}

Trả về định dạng JSON:
{{
  "refined_query": "câu hỏi đã viết lại",
  "detected_topic": "nhãn phù hợp nhất",
  "reason": "tại sao"
}}"""
        
        result_json = self.ai.call(system_prompt, f"Câu hỏi người dùng: {query}", json_mode=True)
        if not result_json:
            return {"refined_query": query, "detected_topic": "general"}
            
        try:
            return json.loads(result_json)
        except Exception:
            # Model có thể trả prose + JSON; cố gắng tách object JSON đầu tiên.
            try:
                start = result_json.find('{')
                end = result_json.rfind('}')
                if start >= 0 and end > start:
                    payload = result_json[start:end + 1]
                    return json.loads(payload)
            except Exception:
                pass
            return {"refined_query": query, "detected_topic": "general"}

# Dùng thử nhanh
if __name__ == "__main__":
    auto = AIAutomation()
    
    # Test thử Rewriter
    test_q = "học phí bao nhiêu"
    processed = auto.process_user_query(test_q)
    print(f"\n[QUERY REWRITE]")
    print(f"Gốc: {test_q}")
    print(f"Mới: {processed['refined_query']}")
    print(f"Tag: {processed['detected_topic']}")
    
    # Test thử AI Chunking
    test_text = f"Học phí năm {ADMISSION_YEAR_STR} là 7.000.000đ. Thí sinh nộp hồ sơ tại phòng A1 từ ngày 1/1/{ADMISSION_YEAR_STR}."
    chunks = auto.auto_scan_and_chunk(test_text, "test_file.txt")
    print(f"\n[AI CHUNKS CREATED]: {len(chunks)}")
    for c in chunks:
        print(f"- [{c['topic']}] {c['title']}")
