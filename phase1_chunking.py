"""
PHASE 1: Document Processing & Chunking
Module để parse document và tạo chunks thông minh với metadata
"""

import re
import json
from typing import List, Dict, Any
from datetime import datetime


class DocumentProcessor:
    """Xử lý và parse document thủ tục nhập học"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.raw_content = self._load_file()
        
    def _load_file(self) -> str:
        """Đọc file txt"""
        with open(self.file_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def parse_document(self) -> Dict[str, Any]:
        """Parse document và trích xuất metadata"""
        content = self.raw_content
        
        # Extract year
        year_match = re.search(r'năm (\d{4})', content)
        year = int(year_match.group(1)) if year_match else 2025
        
        # Extract sections
        sections = self._parse_sections(content)
        
        # Extract metadata
        metadata = self._extract_metadata(content)
        
        return {
            'year': year,
            'sections': sections,
            'metadata': metadata,
            'raw_content': content
        }
    
    def _parse_sections(self, content: str) -> List[Dict]:
        """Parse các PHẦN trong document"""
        sections = []
        
        # Tách các PHẦN
        section_pattern = r'PHẦN (\d+):(.*?)(?=PHẦN \d+:|$)'
        matches = re.finditer(section_pattern, content, re.DOTALL)
        
        for match in matches:
            section_num = int(match.group(1))
            section_content = match.group(2).strip()
            
            sections.append({
                'section_number': section_num,
                'content': section_content,
                'title': self._extract_section_title(section_content)
            })
        
        return sections
    
    def _extract_section_title(self, content: str) -> str:
        """Trích xuất tiêu đề từ nội dung section"""
        lines = content.split('\n')
        if lines:
            return lines[0].strip()
        return ""
    
    def _extract_metadata(self, content: str) -> Dict[str, Any]:
        """Trích xuất metadata từ document"""
        metadata = {
            'deadlines': [],
            'urls': [],
            'fees': {},
            'contacts': {},
            'schedules': []
        }
        
        # Extract deadlines
        deadline_patterns = [
            r'trước (\d{1,2})\s+giờ.*?ngày\s+(\d{1,2}/\d{1,2}/\d{4})',
            r'sau ngày\s+(\d{1,2}/\d{1,2}/\d{4})',
            r'từ ngày\s+(\d{1,2}/\d{1,2}/\d{4})\s+đến.*?ngày\s+(\d{1,2}/\d{1,2}/\d{4})'
        ]
        
        for pattern in deadline_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                metadata['deadlines'].append(match.group(0))
        
        # Extract URLs
        url_pattern = r'https?://[^\s\)]+'
        metadata['urls'] = re.findall(url_pattern, content)
        
        # Extract fees
        fee_pattern = r'([^:]+?):\s*\.+\s*([\d.,]+)đ'
        fee_matches = re.finditer(fee_pattern, content)
        for match in fee_matches:
            fee_name = match.group(1).strip()
            fee_amount = match.group(2).replace('.', '').replace(',', '')
            try:
                metadata['fees'][fee_name] = int(fee_amount)
            except:
                pass
        
        # Extract contacts
        email_match = re.search(r'email:\s*([^\s;]+)', content, re.IGNORECASE)
        if email_match:
            metadata['contacts']['email'] = email_match.group(1)
        
        phone_match = re.search(r'điện thoại:\s*([\d.]+)', content, re.IGNORECASE)
        if phone_match:
            metadata['contacts']['phone'] = phone_match.group(1)
        
        # Extract schedules
        metadata['schedules'] = self._extract_schedules(content)
        
        return metadata
    
    def _extract_schedules(self, content: str) -> List[Dict]:
        """Trích xuất lịch nhập học theo ngành"""
        schedules = []
        
        # Pattern cho lịch nhập học
        schedule_pattern = r'(Sáng|Chiều)\s+(thứ\s+\w+),\s+ngày\s+(\d{1,2}/\d{1,2}/\d{4})\s*(.*?)(?=Sáng|Chiều|\+|Thí sinh|$)'
        
        matches = re.finditer(schedule_pattern, content, re.DOTALL)
        
        for match in matches:
            time_slot = match.group(1)  # Sáng/Chiều
            day = match.group(2)  # thứ ...
            date = match.group(3)  # dd/mm/yyyy
            majors_text = match.group(4)  # Các ngành
            
            # Parse majors
            majors = [m.strip() for m in majors_text.split(';') if m.strip() and len(m.strip()) > 5]
            
            for major in majors:
                schedules.append({
                    'time_slot': time_slot,
                    'day': day,
                    'date': date,
                    'major': major
                })
        
        return schedules


class ChunkGenerator:
    """Tạo các chunks theo 4 levels"""
    
    def __init__(self, parsed_data: Dict[str, Any]):
        self.data = parsed_data
        self.chunks = []
    
    def generate_all_chunks(self) -> List[Dict[str, Any]]:
        """Tạo tất cả các chunks theo 4 levels"""
        # Level 1: Overview
        self.chunks.append(self._create_overview_chunk())
        
        # Level 2: Section chunks
        for section in self.data['sections']:
            self.chunks.append(self._create_section_chunk(section))
        
        # Level 3: Step chunks (cho PHẦN 4)
        section_4 = next((s for s in self.data['sections'] if s['section_number'] == 4), None)
        if section_4:
            step_chunks = self._create_step_chunks(section_4)
            self.chunks.extend(step_chunks)
        
        # Level 4: Detail chunks
        self.chunks.append(self._create_fee_chunk())
        self.chunks.extend(self._create_schedule_chunks())
        self.chunks.extend(self._create_document_chunks())
        
        return self.chunks
    
    def _create_overview_chunk(self) -> Dict[str, Any]:
        """Tạo overview chunk (Level 1)"""
        year = self.data['year']
        total_sections = len(self.data['sections'])
        
        # Tính tổng học phí
        total_fee = sum(self.data['metadata']['fees'].values())
        
        # Key deadlines
        key_deadlines = self.data['metadata']['deadlines'][:3] if self.data['metadata']['deadlines'] else []
        
        content = f"""Thủ tục nhập học năm {year} gồm {total_sections} phần chính:
1. Tra cứu danh sách trúng tuyển
2. Xác nhận nhập học trực tuyến
3. Nộp học phí tạm thu
4. Chuẩn bị và nộp hồ sơ

Tổng học phí cần nộp: {total_fee:,}đ
Các mốc thời gian quan trọng: {', '.join(key_deadlines[:2]) if key_deadlines else 'Xem chi tiết trong tài liệu'}
"""
        
        return {
            'chunk_id': f'admission_{year}_overview',
            'type': 'overview',
            'year': year,
            'title': f'Thủ tục nhập học {year} - Tổng quan',
            'content': content,
            'total_sections': total_sections,
            'key_deadlines': key_deadlines,
            'total_fee': total_fee,
            'metadata': {
                'keywords': ['thủ tục', 'nhập học', 'tổng quan', str(year)]
            }
        }
    
    def _create_section_chunk(self, section: Dict) -> Dict[str, Any]:
        """Tạo section chunk (Level 2)"""
        year = self.data['year']
        section_num = section['section_number']
        
        chunk = {
            'chunk_id': f'admission_{year}_section_{section_num}',
            'type': 'section',
            'year': year,
            'section_number': section_num,
            'title': f"PHẦN {section_num}: {section['title']}",
            'content': section['content'],
            'parent_id': f'admission_{year}_overview',
            'metadata': {
                'keywords': self._extract_keywords(section['content'])
            }
        }
        
        # Extract URL nếu có
        urls = [url for url in self.data['metadata']['urls'] if url in section['content']]
        if urls:
            chunk['url'] = urls[0]
        
        return chunk
    
    def _create_step_chunks(self, section_4: Dict) -> List[Dict[str, Any]]:
        """Tạo step chunks cho PHẦN 4 (Level 3)"""
        year = self.data['year']
        step_chunks = []
        
        # Parse các bước B1, B2, B3, B4
        step_pattern = r'B(\d+):(.*?)(?=B\d+:|Sáng|Chiều|\+|$)'
        matches = re.finditer(step_pattern, section_4['content'], re.DOTALL)
        
        for match in matches:
            step_num = int(match.group(1))
            step_content = match.group(2).strip()
            
            chunk = {
                'chunk_id': f'admission_{year}_section_4_step_{step_num}',
                'type': 'step',
                'year': year,
                'section_number': 4,
                'step_number': step_num,
                'title': f'B{step_num}: {step_content[:50]}...',
                'content': step_content,
                'parent_id': f'admission_{year}_section_4',
                'metadata': {
                    'keywords': self._extract_keywords(step_content)
                }
            }
            
            step_chunks.append(chunk)
        
        return step_chunks
    
    def _create_fee_chunk(self) -> Dict[str, Any]:
        """Tạo fee information chunk (Level 4)"""
        year = self.data['year']
        fees = self.data['metadata']['fees']
        
        # Tạo content text
        content_lines = ["Chi tiết các khoản phí cần nộp:"]
        for idx, (name, amount) in enumerate(fees.items(), 1):
            content_lines.append(f"{idx}. {name}: {amount:,}đ")
        
        total = sum(fees.values())
        content_lines.append(f"\nTổng cộng: {total:,}đ")
        
        # Extract payment period
        payment_period = {}
        for deadline in self.data['metadata']['deadlines']:
            if 'từ ngày' in deadline and 'đến' in deadline:
                dates = re.findall(r'\d{1,2}/\d{1,2}/\d{4}', deadline)
                if len(dates) >= 2:
                    payment_period = {'start': dates[0], 'end': dates[1]}
                    break
        
        return {
            'chunk_id': f'admission_{year}_fees',
            'type': 'fee_info',
            'year': year,
            'title': 'Chi tiết học phí và các khoản phí',
            'content': '\n'.join(content_lines),
            'fees': fees,
            'total_required': total,
            'payment_period': payment_period,
            'parent_id': f'admission_{year}_section_3',
            'metadata': {
                'keywords': ['học phí', 'tiền', 'phí', 'nộp', str(year)]
            }
        }
    
    def _create_schedule_chunks(self) -> List[Dict[str, Any]]:
        """Tạo schedule chunks (Level 4)"""
        year = self.data['year']
        schedules = self.data['metadata']['schedules']
        chunks = []
        
        for idx, schedule in enumerate(schedules):
            chunk = {
                'chunk_id': f'admission_{year}_schedule_{idx}',
                'type': 'schedule',
                'year': year,
                'date': schedule['date'],
                'day': schedule['day'],
                'time_slot': schedule['time_slot'],
                'major': schedule['major'],
                'title': f"Lịch nhập học - {schedule['major']}",
                'content': f"{schedule['time_slot']} {schedule['day']}, ngày {schedule['date']}: {schedule['major']}",
                'parent_id': f'admission_{year}_section_4',
                'metadata': {
                    'keywords': ['lịch', 'nhập học', schedule['major'], schedule['date']]
                }
            }
            chunks.append(chunk)
        
        return chunks
    
    def _create_document_chunks(self) -> List[Dict[str, Any]]:
        """Tạo document list chunks (Level 4)"""
        year = self.data['year']
        chunks = []
        
        # Tìm section 4
        section_4 = next((s for s in self.data['sections'] if s['section_number'] == 4), None)
        if not section_4:
            return chunks
        
        # Parse documents từ section 4
        content = section_4['content']
        
        # Documents cần nộp trong ngày nhập học
        immediate_docs_pattern = r'\+ Nộp trong\s+ngày nhập học:(.*?)(?=\+ Nộp|Lưu ý:|$)'
        immediate_match = re.search(immediate_docs_pattern, content, re.DOTALL)
        
        if immediate_match:
            docs_text = immediate_match.group(1)
            doc_lines = [line.strip() for line in docs_text.split('\n') if re.match(r'^\d+\.', line.strip())]
            
            chunk = {
                'chunk_id': f'admission_{year}_docs_immediate',
                'type': 'document_list',
                'year': year,
                'submission_timing': 'ngày nhập học',
                'title': 'Hồ sơ nộp trong ngày nhập học',
                'content': '\n'.join(doc_lines),
                'documents': doc_lines,
                'parent_id': f'admission_{year}_section_4',
                'metadata': {
                    'keywords': ['hồ sơ', 'giấy tờ', 'nộp', 'ngày nhập học']
                }
            }
            chunks.append(chunk)
        
        return chunks
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Trích xuất keywords từ text"""
        # Danh sách keywords quan trọng
        important_keywords = [
            'tra cứu', 'xác nhận', 'học phí', 'hồ sơ', 'nộp', 'lịch', 'deadline',
            'giấy tờ', 'chuyển khoản', 'trực tuyến', 'trực tiếp', 'bảo hiểm',
            'thi tốt nghiệp', 'học bạ', 'ngành', 'khoa'
        ]
        
        found_keywords = []
        text_lower = text.lower()
        
        for keyword in important_keywords:
            if keyword in text_lower:
                found_keywords.append(keyword)
        
        return found_keywords[:10]  # Lấy tối đa 10 keywords
    
    def save_chunks_to_file(self, output_file: str = 'chunks.json'):
        """Lưu chunks ra file JSON"""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.chunks, f, ensure_ascii=False, indent=2)
        print(f"✅ Đã lưu {len(self.chunks)} chunks vào {output_file}")


def main():
    """Test document processing"""
    print("=" * 70)
    print("PHASE 1: Document Processing & Chunking")
    print("=" * 70)
    print()
    
    # Load and parse document
    print("📄 Đang load và parse document...")
    processor = DocumentProcessor('data/Thủ tục nhập học 2025.txt')
    parsed_data = processor.parse_document()
    
    print(f"✅ Parsed thành công!")
    print(f"   - Năm: {parsed_data['year']}")
    print(f"   - Số sections: {len(parsed_data['sections'])}")
    print(f"   - Deadlines: {len(parsed_data['metadata']['deadlines'])}")
    print(f"   - URLs: {len(parsed_data['metadata']['urls'])}")
    print(f"   - Fees: {len(parsed_data['metadata']['fees'])}")
    print(f"   - Schedules: {len(parsed_data['metadata']['schedules'])}")
    print()
    
    # Generate chunks
    print("🔨 Đang tạo chunks...")
    chunk_gen = ChunkGenerator(parsed_data)
    chunks = chunk_gen.generate_all_chunks()
    
    print(f"✅ Đã tạo {len(chunks)} chunks!")
    print()
    
    # Print chunk statistics
    chunk_types = {}
    for chunk in chunks:
        chunk_type = chunk['type']
        chunk_types[chunk_type] = chunk_types.get(chunk_type, 0) + 1
    
    print("📊 Thống kê chunks:")
    for chunk_type, count in chunk_types.items():
        print(f"   - {chunk_type}: {count}")
    print()
    
    # Save to file
    chunk_gen.save_chunks_to_file('chunks.json')
    
    # Print sample chunks
    print("\n📋 Sample chunks:")
    for chunk in chunks[:3]:
        print(f"\n   [{chunk['type']}] {chunk['title']}")
        print(f"   Content: {chunk['content'][:100]}...")


if __name__ == '__main__':
    main()
