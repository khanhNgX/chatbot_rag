# -*- coding: utf-8 -*-
"""
PHASE 5: LLM Generation & Post-processing (Pure REST Version)
Module xử lý LLM generation qua REST API
Loại bỏ hoàn toàn thư viện google-generativeai để tránh lỗi pydantic-core/DLL load failed
"""

import re
import os
import requests
import json
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from phase4_prompt_engineering import PromptEngineer
from response_cache import get_cache

# Load biến môi trường (override=True để luôn dùng giá trị mới nhất trong .env)
load_dotenv(override=True)

class ResponseValidator:
    """Validate LLM response"""
    
    @staticmethod
    def validate_response(response: str, context: str, intent: str = None) -> Dict[str, Any]:
        validation_result = {'is_valid': True, 'errors': [], 'warnings': []}
        
        if not response or len(response.strip()) < 10:
            validation_result['is_valid'] = False
            validation_result['errors'].append("Response quá ngắn hoặc rỗng")
            return validation_result
        
        # Check hallucination (Basic)
        response_numbers = re.findall(r'\d{1,3}(?:[.,]\d{3})*', response)
        context_numbers = re.findall(r'\d{1,3}(?:[.,]\d{3})*', context)
        
        suspicious_numbers = [num for num in response_numbers if len(num) > 4 and num not in context_numbers]
        if suspicious_numbers:
            validation_result['warnings'].append(f"Phát hiện số liệu không có trong context: {suspicious_numbers[:3]}")
        
        # Intent-specific checks
        if intent == 'fee_info' and not re.search(r'\d{1,3}(?:[.,]\d{3})*\s*đ', response):
            validation_result['warnings'].append("Intent là fee_info nhưng không tìm thấy số tiền")
        
        if intent == 'schedule' and not re.search(r'\d{1,2}/\d{1,2}/\d{4}', response):
            validation_result['warnings'].append("Intent là schedule nhưng không tìm thấy ngày tháng")
            
        return validation_result

class ResponseFormatter:
    """Format và beautify response"""
    
    @staticmethod
    def add_citations(response: str, chunks: List[Dict[str, Any]]) -> str:
        if not chunks or '[SOURCE]' in response or 'Nguồn:' in response.lower():
            return response
        
        main_chunk = chunks[0]
        metadata = main_chunk.get('metadata', {})
        year = metadata.get('year', '')
        section = metadata.get('section_number', '')
        # Source có thể ở level ngoài hoặc trong metadata
        source = main_chunk.get('source', '') or metadata.get('source', 'Tài liệu tuyển sinh')
        
        citation_parts = [f"\n\n---"]
        if section and year:
            citation_parts.append(f"[SOURCE] Nguồn: {source} (PHẦN {section}, Năm {year})")
        elif section:
            citation_parts.append(f"[SOURCE] Nguồn: {source} (PHẦN {section})")
        elif year:
            citation_parts.append(f"[SOURCE] Nguồn: {source} (Năm {year})")
        else:
            citation_parts.append(f"[SOURCE] Nguồn: {source}")
            
        content = main_chunk.get('content', '')
        deadline_match = re.search(r'(?:trước|sau|từ ngày|đến ngày)\s+\d{1,2}[/\-]\d{1,2}[/\-]\d{4}', content)
        if deadline_match:
            citation_parts.append(f"[TIME] Lưu ý thời gian: {deadline_match.group(0)}")
            
        return response.strip() + "\n" + "\n".join(citation_parts)

    @staticmethod
    def format_markdown(response: str) -> str:
        formatted = re.sub(r'\n{3,}', '\n\n', response.strip())
        return formatted

    @staticmethod
    def create_fallback_response(query: str, reason: str = "unknown") -> str:
        return f"""Xin lỗi, tôi không tìm thấy thông tin về "{query}" trong tài liệu.

[TIP] Gợi ý:
- Kiểm tra lại năm học bạn đang hỏi (2025?)
- Thử diễn đạt câu hỏi khác đi
- Liên hệ trực tiếp với nhà trường: 024.38581283 | ctsv@hus.edu.vn
"""

class LLMGenerator:
    """LLM Generation sử dụng Gemini API qua REST CALL (Pure Python)"""
    
    def __init__(self, api_key: str = None, mode: str = 'compact'):
        # CHỈ SỬ DỤNG GROQ
        self.api_key = os.getenv('GROQ_API_KEY')
        self.mode = mode
        self.prompt_engineer = PromptEngineer(mode=mode)
        self.validator = ResponseValidator()
        self.formatter = ResponseFormatter()
    
    def _call_groq(self, system_prompt: str, user_prompt: str, intent: str = 'general') -> str:
        """Gọi Groq API (Chọn mô hình thông minh tùy theo Intent)"""
        if not self.api_key: return ""
        
        # CHỌN MÔ HÌNH: 
        # - Nếu hỏi về học phí (Cần tính toán): Dùng Llama 3.3 70B (Siêu mạnh)
        # - Nếu hỏi chung chung (Cần tốc độ): Dùng Llama 3.1 8B (Siêu nhanh)
        model = "llama-3.3-70b-versatile" if intent == 'fee_info' else "llama-3.1-8b-instant"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.1, # Rất thấp để tránh AI sáng tạo bừa số liệu
            "max_tokens": 1024
        }
        
        try:
            print(f"[GROQ] Generating answer via {model}...")
            response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=15)
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content']
            
            print(f"[WARNING] Groq API error: {response.status_code}")
            return None
        except Exception as e:
            print(f"[ERROR] Connection lost: {e}")
            return None

    def generate(
        self, 
        query: str, 
        chunks: List[Dict[str, Any]], 
        intent: str = None,
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """Engine tối giản: Groq -> Smart Search"""
        cache = get_cache()
        cached_response = cache.get(query)
        if cached_response:
            return {'query': query, 'answer': cached_response['response'], 'success': True, 'source': 'cache'}
        
        full_prompt = self.prompt_engineer.create_full_prompt(query, chunks)
        system_instruction = self.prompt_engineer.system_prompt
        
        # 1. Gọi duy nhất Groq (Kèm theo Intent để chọn Model phù hợp)
        groq_answer = self._call_groq(system_instruction, full_prompt, intent=intent)
        
        if groq_answer:
            final_answer = self.formatter.format_markdown(self.formatter.add_citations(groq_answer, chunks))
            cache.save(query, final_answer)
            return {
                'query': query,
                'answer': final_answer,
                'success': True,
                'source': 'groq'
            }
                
        # 2. Nếu Groq không khả dụng, dùng Smart Manual Search ngay
        print("[FALLBACK] Groq bận, đang tìm kiếm thủ công trong tài liệu...")
        return self._generate_manual_fallback(query, chunks)
                
        # 3. Fallback cuối cùng: SMART MANUAL SEARCH
        return self._generate_manual_fallback(query, chunks)

    def _generate_manual_fallback(self, query: str, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Tạo câu trả lời thông minh dựa trên Regex khi AI không khả dụng"""
        if not chunks:
            return {
                'query': query,
                'answer': "⚠️ AI đang bận và tôi không tìm thấy dữ liệu nào liên quan trong tài liệu.",
                'success': False,
                'source': 'error'
            }
            
        parts = ["🚀 **CHẾ ĐỘ TÌM KIẾM TRỰC TIẾP (AI ĐANG BẬN)**\n"]
        parts.append(f"Kết quả tìm kiếm cho: *{query}*\n")
        
        # Logic trích xuất thông tin quan trọng (Tiền, Ngày tháng)
        important_info = []
        for chunk in chunks[:5]:
            content = chunk.get('content', '')
            # Tìm số tiền
            money = re.findall(r'\d{1,3}(?:\.\d{3})*(?:\s*đ|\s*đồng|\s*VNĐ)', content, re.IGNORECASE)
            # Tìm ngày tháng
            dates = re.findall(r'\d{1,2}/\d{1,2}/\d{4}', content)
            
            if money: important_info.extend([f"💰 Số tiền: **{m}**" for m in money])
            if dates: important_info.extend([f"📅 Ngày/Lịch: **{d}**" for d in dates])

        if important_info:
            parts.append("💡 **Thông tin tiêu điểm tìm thấy:**")
            # Loại bỏ trùng lặp và giới hạn
            for info in list(dict.fromkeys(important_info))[:5]:
                parts.append(f"- {info}")
            parts.append("")

        parts.append("-" * 20)
        
        # Chỉ hiển thị 2 chunk liên quan nhất để tránh quá dài
        for i, chunk in enumerate(chunks[:2], 1):
            content = chunk.get('content', '').strip()
            # Highlight query trong content (đơn giản)
            meta = chunk.get('metadata', {})
            source = meta.get('source', 'Tài liệu')
            year = meta.get('year', '2025')
            
            parts.append(f"📂 **Nguồn {i}: {source} ({year})**")
            # Cắt ngắn content nếu quá dài
            display_content = content[:400] + "..." if len(content) > 400 else content
            parts.append(f"> {display_content}\n")
            
        parts.append("-" * 20)
        parts.append("💬 *Bạn có thể thử hỏi lại sau 1-2 phút để AI có thể phục vụ tốt hơn.*")
        
        return {
            'query': query,
            'answer': "\n".join(parts),
            'success': True,
            'source': 'smart_manual_search',
            'chunks_used': len(chunks)
        }

def main():
    import sys
    # Thiết lập stdout encoding cho Windows terminal
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8', errors='replace')

    print("=" * 70)
    print("PHASE 5: LLM Generation (Pure REST)")
    print("=" * 70)
    
    GROQ_API_KEY = os.getenv('GROQ_API_KEY')
    if not GROQ_API_KEY:
        print("[ERROR] Lỗi: Thiếu GROQ_API_KEY trong .env")
        return
        
    generator = LLMGenerator()
    sample_chunks = [{
        'chunk_id': 'test_chunk',
        'content': "Học phí năm 2025 là 7.019.750đ.",
        'metadata': {'type': 'fee_info', 'year': 2025, 'source': 'Tài liệu nhập học', 'section_number': 1}
    }]
    
    print("[BOT] Đang gọi Groq API (Llama 3.1 8B)...")
    result = generator.generate("Học phí bao nhiêu?", sample_chunks, intent='fee_info')
    print(f"\n[OK] Kết quả (Nguồn: {result['source']}):\n{result['answer']}")

if __name__ == '__main__':
    main()
