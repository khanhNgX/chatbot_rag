"""
PHASE 4: Prompt Engineering
Module xây dựng prompts tối ưu cho RAG
"""

from typing import List, Dict, Any


class PromptEngineer:
    """Xây dựng các prompts tối ưu cho RAG chatbot"""
    
    def __init__(self):
        self.system_prompt = self._create_system_prompt()
    
    def _create_system_prompt(self) -> str:
        """
        Tạo system prompt theo template trong file md
        
        Mục tiêu:
        - Hướng dẫn LLM trả lời dựa trên context
        - Yêu cầu trích dẫn nguồn
        - Format output dễ đọc
        """
        return """Bạn là trợ lý tư vấn thủ tục nhập học của Trường Đại học Khoa học Tự nhiên - ĐHQG Hà Nội.

NHIỆM VỤ:
- Trả lời câu hỏi của sinh viên dựa HOÀN TOÀN trên ngữ cảnh được cung cấp
- Trích dẫn chính xác nguồn (PHẦN, Bước, Năm)
- Trả lời ngắn gọn, rõ ràng, dễ hiểu bằng tiếng Việt
- Nếu không có thông tin trong ngữ cảnh, nói rõ "Không tìm thấy thông tin trong tài liệu"

LƯU Ý:
- Luôn đề cập năm học để tránh nhầm lẫn
- Highlight các deadline quan trọng với emoji ⏰
- Format số tiền dễ đọc (VD: 7.019.750đ)
- Nếu có nhiều bước, liệt kê rõ ràng với số thứ tự
- Sử dụng emoji phù hợp để câu trả lời sinh động hơn

CÁCH TRẢ LỜI:
- Ngắn gọn, đi thẳng vào vấn đề
- Ưu tiên thông tin quan trọng nhất
- Kết thúc bằng nguồn tham khảo nếu cần
- Không bịa đặt thông tin không có trong ngữ cảnh

FORMAT MẪU:
Khi trả lời về học phí:
"Tổng số tiền cần nộp là X đồng, bao gồm:
1. [Khoản 1]: X đồng
2. [Khoản 2]: X đồng
...
⏰ Thời gian nộp: [deadline]
📚 Nguồn: PHẦN X, Thủ tục nhập học năm YYYY"

Khi trả lời về lịch:
"Lịch nhập học cho ngành [tên ngành]:
📅 Ngày: [ngày tháng năm]
🕐 Thời gian: [giờ]
📍 Địa điểm: [địa chỉ]
📚 Nguồn: PHẦN 4, Thủ tục nhập học năm YYYY"

Khi không có thông tin:
"Xin lỗi, tôi không tìm thấy thông tin về [chủ đề] trong tài liệu.

Bạn có thể liên hệ trực tiếp:
📞 024.38581283
📧 ctsv@hus.edu.vn"
"""
    
    def create_context_prompt(self, chunks: List[Dict[str, Any]]) -> str:
        """
        Tạo context prompt từ retrieved chunks
        
        Template theo file md:
        ----- NGỮ CẢNH TỪ TÀI LIỆU -----
        [CHUNK 1 - Type: ..., Year: ...]
        Tiêu đề: ...
        Nội dung: ...
        Nguồn: ...
        ----- HẾT NGỮ CẢNH -----
        """
        if not chunks:
            return self._create_empty_context()
        
        context_parts = ["\n----- NGỮ CẢNH TỪ TÀI LIỆU -----\n"]
        
        for i, chunk in enumerate(chunks, 1):
            metadata = chunk.get('metadata', {})
            content = chunk.get('content', '')
            
            # Extract metadata fields
            chunk_type = metadata.get('type', 'N/A')
            year = metadata.get('year', 'N/A')
            title = metadata.get('title', 'N/A')
            section_num = metadata.get('section_number', '')
            
            # Format chunk header
            context_parts.append(f"\n[CHUNK {i} - Type: {chunk_type}, Year: {year}]")
            context_parts.append(f"Tiêu đề: {title}")
            context_parts.append(f"Nội dung:")
            context_parts.append(content)
            
            # Add source citation
            if section_num:
                context_parts.append(f"Nguồn: PHẦN {section_num}")
            
            context_parts.append("")  # Empty line separator
        
        context_parts.append("----- HẾT NGỮ CẢNH -----\n")
        
        return "\n".join(context_parts)
    
    def _create_empty_context(self) -> str:
        """Context khi không tìm thấy thông tin"""
        return """
----- NGỮ CẢNH TỪ TÀI LIỆU -----

Không tìm thấy thông tin liên quan trong tài liệu.

----- HẾT NGỮ CẢNH -----
"""
    
    def create_user_prompt(self, query: str) -> str:
        """
        Tạo user prompt với query
        
        Format đơn giản nhưng rõ ràng
        """
        return f"""CÂU HỎI: {query}

Hãy trả lời dựa trên ngữ cảnh trên. Nhớ trích dẫn nguồn nếu cần thiết."""
    
    def create_full_prompt(self, query: str, chunks: List[Dict[str, Any]]) -> str:
        """
        Tạo full prompt bao gồm context + user query
        
        Returns:
            Full prompt string để gửi cho LLM
        """
        context_prompt = self.create_context_prompt(chunks)
        user_prompt = self.create_user_prompt(query)
        
        return context_prompt + "\n" + user_prompt
    
    def get_generation_config(self) -> Dict[str, Any]:
        """
        Lấy config cho LLM generation theo file md
        
        Optimization tips từ PHASE 4:
        - Temperature: 0.1-0.3 (cần chính xác, không sáng tạo)
        - Max tokens: 500-1000 (đủ cho câu trả lời chi tiết)
        """
        return {
            'temperature': 0.3,  # Low temperature for accuracy
            'max_output_tokens': 1000,  # Enough for detailed answers
            'top_p': 0.9,
            'top_k': 40
        }


class PromptTemplates:
    """Templates cho các loại câu hỏi khác nhau"""
    
    @staticmethod
    def get_template_for_intent(intent: str) -> str:
        """Lấy template phù hợp với intent"""
        templates = {
            'fee_info': """Khi trả lời về học phí, hãy:
1. Liệt kê tất cả các khoản phí
2. Tính tổng rõ ràng
3. Nói rõ deadline nộp
4. Thêm nguồn tham khảo""",
            
            'schedule': """Khi trả lời về lịch, hãy:
1. Nói rõ ngày giờ
2. Thời gian (sáng/chiều)
3. Địa điểm cụ thể
4. Ngành/khoa liên quan""",
            
            'document': """Khi trả lời về hồ sơ, hãy:
1. Liệt kê đầy đủ các giấy tờ
2. Phân loại: bản chính/bản sao
3. Nói rõ deadline nộp
4. Ghi chú nếu có (nếu có)""",
            
            'procedure': """Khi trả lời về thủ tục, hãy:
1. Liệt kê các bước theo thứ tự
2. Mỗi bước mô tả ngắn gọn
3. Highlight deadline quan trọng
4. Link/URL nếu có"""
        }
        
        return templates.get(intent, "Trả lời một cách rõ ràng và chính xác.")


def main():
    """Test prompt engineering"""
    print("=" * 70)
    print("PHASE 4: Prompt Engineering")
    print("=" * 70)
    print()
    
    # Initialize
    engineer = PromptEngineer()
    
    # Test system prompt
    print("📝 System Prompt:")
    print("-" * 70)
    print(engineer.system_prompt[:500] + "...")
    print()
    
    # Test context prompt với sample chunks
    sample_chunks = [
        {
            'chunk_id': 'admission_2025_fees',
            'content': """Chi tiết các khoản phí cần nộp:
1. Tiền làm hồ sơ, tài liệu: 50.000đ
2. Hồ sơ sức khỏe, khám sức khỏe: 180.000đ
3. Bảo hiểm Y tế (bắt buộc): 789.750đ
4. Tạm thu học phí học kì 1 năm 2025-2026: 6.000.000đ
Tổng cộng: 7.019.750đ""",
            'metadata': {
                'type': 'fee_info',
                'year': 2025,
                'title': 'Chi tiết học phí và các khoản phí',
                'section_number': 3
            }
        }
    ]
    
    # Create full prompt
    query = "Học phí năm 2025 là bao nhiêu?"
    full_prompt = engineer.create_full_prompt(query, sample_chunks)
    
    print("📄 Full Prompt Example:")
    print("-" * 70)
    print(full_prompt)
    print()
    
    # Generation config
    config = engineer.get_generation_config()
    print("⚙️ Generation Config:")
    print("-" * 70)
    for key, value in config.items():
        print(f"   {key}: {value}")
    print()
    
    print("✅ PHASE 4 completed!")


if __name__ == '__main__':
    main()
