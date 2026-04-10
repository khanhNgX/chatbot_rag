"""
PHASE 4: Prompt Engineering
Module xây dựng prompts tối ưu cho RAG
"""

from typing import List, Dict, Any


class PromptEngineer:
    """Xây dựng các prompts tối ưu cho RAG chatbot"""
    
    def __init__(self, mode: str = 'standard'):
        self.mode = mode # 'standard' hoặc 'compact' (tiết kiệm quota)
        self.system_prompt = self._create_system_prompt() if mode == 'standard' else self._create_compact_system_prompt()
    
    def _create_system_prompt(self) -> str:
        """Tạo system prompt đầy đủ"""
        return """Bạn là trợ lý tư vấn thủ tục nhập học của Trường Đại học Khoa học Tự nhiên - ĐHQG Hà Nội.

NHIỆM VỤ:
- Trả lời câu hỏi của sinh viên dựa HOÀN TOÀN trên ngữ cảnh được cung cấp.
- Trả lời ĐẦY ĐỦ Ý - KHÔNG ĐƯỢC bỏ sót thông tin quan trọng.
- [QUAN TRỌNG] TÍNH TOÁN CHÍNH XÁC: Khi gặp các con số (học phí, lệ phí), hãy liệt kê từng mục và THỰC HIỆN PHÉP CỘNG BƯỚC-THEO-BƯỚC. Tuyệt đối không được sai sót số liệu tài chính.
- Kiểm tra lại: Tổng số tiền = Khoản 1 + Khoản 2 + ...

NGUYÊN TẮC TRẢ LỜI:
[OK] CHÍNH XÁC SỐ LIỆU:
- Luôn đối chiếu các con số trong câu trả lời với văn bản gốc.
- Nếu phải tính tổng, hãy viết rõ: "Tổng cộng (Mục A + Mục B + Mục C) = [Kết quả]".
- Định dạng tiền tệ: dùng dấu chấm phân cách hàng nghìn (ví dụ: 7.019.750đ).

[OK] ĐẦY ĐỦ VÀ CHI TIẾT:
- LIỆT KÊ TẤT CẢ các loại hồ sơ, giấy tờ.
- LIỆT KÊ ĐỦ các bước thủ tục.
- Nhóm thông tin liên quan lại với nhau.

[OK] FORMAT THÔNG MINH:
- Sử dụng emoji: 💰 (tiền), 📅 (lịch), 📋 (hồ sơ), 📍 (địa điểm).
- Highlight deadline với [TIME].
- Trích dẫn nguồn [SOURCE] rõ ràng.

VÍ DỤ TÍNH TOÁN SAI LẦM CẦN TRÁNH:
- Tránh việc cộng nhẩm nhanh rồi đưa ra con số sai.

VÍ DỤ TÍNH TOÁN ĐÚNG:
Câu hỏi: "Tổng phí nhập học?"
Context: "Phí A 50.000, Phí B 150.000, Phí C 800.000"
Trả lời:
Để tính tổng học phí, chúng ta thực hiện phép cộng chi tiết:
1. Phí A: 50.000đ
2. Phí B: 150.000đ
3. Phí C: 800.000đ
-----------------------
Phép tính: 50.000 + 150.000 + 800.000 = 1.000.000đ
=> Tổng học phí cần nộp là: 1.000.000đ

VÍ DỤ FORMAT TRẢ LỜI:
Câu hỏi về học phí:
"💰 Chi tiết các khoản phí cần nộp (năm 2025):
• Khoản 1: [Số tiền]
• Khoản 2: [Số tiền]
-----------------------
[TÍNH TOÁN]: [Khoản 1] + [Khoản 2] + ... = [TỔNG]
=> Tổng cộng: [TỔNG]

[TIME] Hạn nộp: [Ngày] | 📍 Địa điểm: [Địa điểm]"
Câu hỏi về hồ sơ:
"[FORM] Các loại hồ sơ bạn cần chuẩn bị (2025):

BẮT BUỘC:
• Giấy báo kết quả thi THPT (Bản chính)
• Giấy chứng nhận tốt nghiệp tạm thời (Bản chính)
• Học bạ THPT (Công chứng)
• Giấy khai sinh (Bản sao)
• CCCD (2 mặt photo)
• [Tiếp tục liệt kê TẤT CẢ các giấy tờ khác có trong context...]

[TIME] Hạn nộp: [Ngày tháng năm]
📍 Địa điểm: 334 Nguyễn Trãi, Thanh Xuân"

Khi trả lời về lịch:
"Lịch nhập học cho ngành [tên ngành]:
📅 Ngày: [ngày tháng năm]
🕐 Thời gian: [giờ]
📍 Địa điểm: [địa chỉ]
[SOURCE] Nguồn: PHẦN 4, Thủ tục nhập học năm 2025"

LƯU Ý CUỐI:
- Ưu tiên sự đầy đủ (Full content) đối với danh sách hồ sơ và các bước thực hiện.
- Trình bày mạch lạc, dễ hiểu.
"""

    def _create_compact_system_prompt(self) -> str:
        """
        Compact system prompt để tiết kiệm quota (giảm ~60% tokens so với bản full)
        """
        return """Bạn là trợ lý tư vấn nhập học HUS - ĐHQG Hà Nội.
QUY TẮC: 
1. Chỉ dùng context được cung cấp. Không tự chế thông tin.
2. Trả lời đầy đủ danh sách, giấy tờ, bước thực hiện. KHÔNG tóm tắt lược bỏ.
3. Nếu không có thông tin, nói "Không tìm thấy trong tài liệu".
4. Format: Dùng bullet points (•), highlight [TIME], format tiền (đ).
5. Luôn trích dẫn nguồn [SOURCE] (Phần, Năm) cuối câu trả lời."""
    
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
        
        # Header gọn nhẹ hơn
        context_parts = ["\n[CONTEXT]"]
        
        for i, chunk in enumerate(chunks, 1):
            metadata = chunk.get('metadata', {})
            content = chunk.get('content', '')
            
            # Metadata rút gọn
            year = metadata.get('year', '')
            section = metadata.get('section_number', '')
            source = metadata.get('source', '')
            
            # Format tối ưu: i) [Phần, Năm] Content
            meta_str = f"(PHẦN {section}, {year})" if section and year else (f"(PHẦN {section})" if section else (f"({year})" if year else ""))
            
            context_parts.append(f"C{i} {meta_str}: {content.strip()}")
        
        context_parts.append("[END CONTEXT]\n")
        
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
    
    def display_prompt_pipeline(self, query: str, chunks: List[Dict[str, Any]], 
                               verbose: bool = True) -> Dict[str, Any]:
        """
        Hiển thị toàn bộ pipeline xử lý prompt
        
        Args:
            query: Câu hỏi của user
            chunks: Retrieved chunks từ retrieval
            verbose: Có hiển thị chi tiết hay không
            
        Returns:
            Dict chứa tất cả thông tin về prompt
        """
        context_prompt = self.create_context_prompt(chunks)
        user_prompt = self.create_user_prompt(query)
        full_prompt = context_prompt + "\n" + user_prompt
        
        result = {
            'query': query,
            'num_chunks': len(chunks),
            'context_prompt': context_prompt,
            'user_prompt': user_prompt,
            'full_prompt': full_prompt,
            'system_prompt': self.system_prompt,
            'context_length': len(context_prompt),
            'full_length': len(full_prompt),
            'estimated_tokens': (len(self.system_prompt) + len(full_prompt)) // 4
        }
        
        if verbose:
            print("=" * 80)
            print("[FORM] PROMPT PIPELINE DISPLAY")
            print("=" * 80)
            print(f"Query: {query}")
            print(f"Chunks: {len(chunks)}")
            print(f"Context Length: {len(context_prompt)} chars")
            print(f"Full Prompt Length: {len(full_prompt)} chars")
            print(f"Est. Tokens: ~{result['estimated_tokens']}")
            print()
            
            print("─" * 80)
            print("SYSTEM PROMPT:")
            print("─" * 80)
            print(self.system_prompt)
            print()
            
            print("─" * 80)
            print("CONTEXT + USER PROMPT:")
            print("─" * 80)
            print(full_prompt)
            print()
            print("=" * 80)
        
        return result


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
    print("[FORM] System Prompt:")
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
    
    print("[DOCUMENT] Full Prompt Example:")
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
    
    print("[OK] PHASE 4 completed!")


if __name__ == '__main__':
    main()
