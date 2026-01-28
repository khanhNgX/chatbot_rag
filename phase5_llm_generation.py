"""
PHASE 5: LLM Generation & Post-processing
Module xử lý LLM generation, validation và formatting
"""

import re
from typing import List, Dict, Any, Optional
import google.generativeai as genai
from phase4_prompt_engineering import PromptEngineer


class ResponseValidator:
    """Validate LLM response theo các rules trong file md"""
    
    @staticmethod
    def validate_response(response: str, context: str, intent: str = None) -> Dict[str, Any]:
        """
        Validate response theo 3 checks trong file md:
        
        Check 1: Có trả lời không?
        Check 2: Có hallucination không?
        Check 3: Có đầy đủ thông tin không?
        """
        validation_result = {
            'is_valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Check 1: Có trả lời không?
        if not response or len(response.strip()) < 10:
            validation_result['is_valid'] = False
            validation_result['errors'].append("Response quá ngắn hoặc rỗng")
            return validation_result
        
        # Check 2: Có hallucination không? (Basic check)
        # Kiểm tra xem có số tiền/ngày tháng không có trong context
        response_numbers = re.findall(r'\d{1,3}(?:[.,]\d{3})*', response)
        context_numbers = re.findall(r'\d{1,3}(?:[.,]\d{3})*', context)
        
        suspicious_numbers = []
        for num in response_numbers:
            if len(num) > 4 and num not in context_numbers:
                # Số lớn không có trong context - có thể hallucination
                suspicious_numbers.append(num)
        
        if suspicious_numbers:
            validation_result['warnings'].append(
                f"Phát hiện số liệu không có trong context: {suspicious_numbers[:3]}"
            )
        
        # Check 3: Với intent FEE_INFO, response phải chứa số tiền
        if intent == 'fee_info':
            if not re.search(r'\d{1,3}(?:[.,]\d{3})*\s*đ', response):
                validation_result['warnings'].append(
                    "Intent là fee_info nhưng không tìm thấy số tiền trong response"
                )
        
        # Check 3b: Với intent SCHEDULE, response phải có ngày tháng
        if intent == 'schedule':
            if not re.search(r'\d{1,2}/\d{1,2}/\d{4}', response):
                validation_result['warnings'].append(
                    "Intent là schedule nhưng không tìm thấy ngày tháng"
                )
        
        return validation_result


class ResponseFormatter:
    """Format và beautify response"""
    
    @staticmethod
    def add_citations(response: str, chunks: List[Dict[str, Any]]) -> str:
        """
        Add citation theo format trong file md
        
        Format:
        [Response từ LLM]
        
        📚 Nguồn: PHẦN X - Title, Thủ tục nhập học năm YYYY
        ⏰ Deadline: ...
        """
        if not chunks:
            return response
        
        # Nếu đã có citation, return
        if '📚' in response or 'Nguồn:' in response.lower():
            return response
        
        # Lấy metadata từ chunk đầu tiên
        main_chunk = chunks[0]
        metadata = main_chunk.get('metadata', {})
        
        year = metadata.get('year', '')
        section = metadata.get('section_number', '')
        title = metadata.get('title', '')
        
        # Build citation
        citation_parts = []
        
        if section and year:
            citation_parts.append(f"\n\n---")
            citation_parts.append(f"📚 Nguồn: PHẦN {section}, Thủ tục nhập học năm {year}")
        
        # Extract deadline từ content nếu có
        content = main_chunk.get('content', '')
        deadline_match = re.search(r'(?:trước|sau|từ ngày|đến ngày)\s+\d{1,2}[/\-]\d{1,2}[/\-]\d{4}', content)
        if deadline_match and '⏰' not in response:
            citation_parts.append(f"⏰ Lưu ý thời gian: {deadline_match.group(0)}")
        
        if citation_parts:
            return response.strip() + "\n" + "\n".join(citation_parts)
        
        return response
    
    @staticmethod
    def format_markdown(response: str) -> str:
        """
        Format response theo Markdown style
        
        Example từ file md:
        ## Học phí năm 2025
        
        Tổng số tiền: **7.019.750đ**
        
        1. 💼 Item 1
        2. 🏥 Item 2
        """
        formatted = response.strip()
        
        # Đã được format bởi LLM, không cần thêm
        # Chỉ đảm bảo spacing đẹp
        formatted = re.sub(r'\n{3,}', '\n\n', formatted)
        
        return formatted
    
    @staticmethod
    def create_fallback_response(query: str, reason: str = "unknown") -> str:
        """
        Tạo fallback response khi không tìm thấy thông tin
        
        Template từ file md PHASE 5
        """
        return f"""Xin lỗi, tôi không tìm thấy thông tin về "{query}" trong tài liệu.

💡 Gợi ý:
- Kiểm tra lại năm học bạn đang hỏi (2025?)
- Thử diễn đạt câu hỏi khác đi
- Liên hệ trực tiếp với nhà trường

📞 Liên hệ:
- Điện thoại: 024.38581283
- Email: ctsv@hus.edu.vn
- Địa chỉ: Phòng Công tác sinh viên & truyền thông, 
  Trường ĐHKHTN, 334 Nguyễn Trãi, Thanh Xuân, Hà Nội
"""


class LLMGenerator:
    """
    LLM Generation với Gemini
    
    Theo file md PHASE 5:
    - Lựa chọn model: Gemini 1.5 Flash (cân bằng giá/chất lượng)
    - Validation
    - Post-processing
    """
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        genai.configure(api_key=api_key)
        
        self.prompt_engineer = PromptEngineer()
        self.validator = ResponseValidator()
        self.formatter = ResponseFormatter()
        
        # Initialize model với system instruction
        self.model = genai.GenerativeModel(
            model_name='gemini-2.5-flash',
            system_instruction=self.prompt_engineer.system_prompt,
            generation_config=self.prompt_engineer.get_generation_config()
        )
    
    def generate(
        self, 
        query: str, 
        chunks: List[Dict[str, Any]], 
        intent: str = None,
        chat_history: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Main generation pipeline theo PHASE 5
        
        Steps:
        1. Call LLM API
        2. Response Validation
        3. Add Citation
        4. Format Output
        5. Fallback Handling
        """
        
        # Step 1: Build prompt và call LLM
        full_prompt = self.prompt_engineer.create_full_prompt(query, chunks)
        
        try:
            # Call LLM
            if chat_history:
                response = chat_history.send_message(full_prompt)
            else:
                response = self.model.generate_content(full_prompt)
            
            response_text = response.text
            
        except Exception as e:
            print(f"❌ LLM Error: {e}")
            return {
                'query': query,
                'answer': self.formatter.create_fallback_response(query, reason="llm_error"),
                'success': False,
                'error': str(e)
            }
        
        # Step 2: Validation
        context_text = self.prompt_engineer.create_context_prompt(chunks)
        validation = self.validator.validate_response(response_text, context_text, intent)
        
        if not validation['is_valid']:
            print(f"⚠️ Validation failed: {validation['errors']}")
            return {
                'query': query,
                'answer': self.formatter.create_fallback_response(query, reason="validation_failed"),
                'success': False,
                'validation': validation
            }
        
        # Step 3: Add citations
        response_with_citation = self.formatter.add_citations(response_text, chunks)
        
        # Step 4: Format output
        formatted_response = self.formatter.format_markdown(response_with_citation)
        
        # Log warnings if any
        if validation['warnings']:
            print(f"⚠️ Validation warnings: {validation['warnings']}")
        
        # Step 5: Return result
        return {
            'query': query,
            'answer': formatted_response,
            'success': True,
            'validation': validation,
            'chunks_used': len(chunks)
        }


def main():
    """Test LLM generation và post-processing"""
    print("=" * 70)
    print("PHASE 5: LLM Generation & Post-processing")
    print("=" * 70)
    print()
    
    # API key
    GEMINI_API_KEY = "AIzaSyAEPKOsnGnArFYckGojz-s4ymfvyhzj4Ic"
    
    # Initialize generator
    generator = LLMGenerator(GEMINI_API_KEY)
    
    # Sample chunks
    sample_chunks = [
        {
            'chunk_id': 'admission_2025_fees',
            'content': """Chi tiết các khoản phí cần nộp:
1. Tiền làm hồ sơ, tài liệu: 50.000đ
2. Hồ sơ sức khỏe, khám sức khỏe: 180.000đ
3. Bảo hiểm Y tế (bắt buộc): 789.750đ
4. Tạm thu học phí học kì 1 năm 2025-2026: 6.000.000đ

Tổng cộng: 7.019.750đ

Thời gian nộp: từ ngày 25/8/2025 đến 05/9/2025""",
            'metadata': {
                'type': 'fee_info',
                'year': 2025,
                'title': 'Chi tiết học phí và các khoản phí',
                'section_number': 3
            }
        }
    ]
    
    # Test query
    query = "Học phí năm 2025 là bao nhiêu?"
    print(f"🧪 Test Query: {query}")
    print("-" * 70)
    print()
    
    # Generate
    print("🤖 Generating response...")
    result = generator.generate(query, sample_chunks, intent='fee_info')
    
    print()
    print("=" * 70)
    print("📝 RESULT:")
    print("=" * 70)
    print()
    
    print(f"✅ Success: {result['success']}")
    print(f"📊 Chunks used: {result.get('chunks_used', 0)}")
    print()
    
    print("💬 Answer:")
    print("-" * 70)
    print(result['answer'])
    print()
    
    # Validation info
    if 'validation' in result:
        val = result['validation']
        if val['warnings']:
            print("⚠️ Warnings:")
            for warning in val['warnings']:
                print(f"   - {warning}")
            print()
    
    print("✅ PHASE 5 completed!")


if __name__ == '__main__':
    main()
