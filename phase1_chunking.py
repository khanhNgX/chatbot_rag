"""
PHASE 1: Document Processing & Chunking
Module để parse document (TXT, DOCX, PDF) và tạo chunks thông minh
"""

import re
import json
import os
import glob
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

class DocxProcessor:
    """Trích xuất text từ file Word (.docx)"""
    @staticmethod
    def extract_text(file_path: str) -> str:
        try:
            import docx
            doc = docx.Document(file_path)
            return "\n".join([para.text for para in doc.paragraphs])
        except Exception as e:
            print(f"[ERROR] Lỗi đọc file Word {file_path}: {e}")
            return ""

class PdfProcessor:
    """Trích xuất text từ file PDF (.pdf)"""
    @staticmethod
    def extract_text(file_path: str) -> str:
        try:
            import fitz  # PyMuPDF
            text = ""
            with fitz.open(file_path) as doc:
                for page in doc:
                    text += page.get_text()
            return text
        except Exception as e:
            print(f"[ERROR] Lỗi đọc file PDF {file_path}: {e}")
            return ""

class TextExtractor:
    """Trích xuất text từ các định dạng file khác nhau"""
    
    @staticmethod
    def extract(file_path: str) -> str:
        ext = Path(file_path).suffix.lower()
        if ext == '.txt':
            return TextExtractor._read_txt(file_path)
        elif ext == '.docx':
            return DocxProcessor.extract_text(file_path)
        elif ext == '.pdf':
            return PdfProcessor.extract_text(file_path)
        else:
            print(f"[WARNING] Định dạng file {ext} chưa được hỗ trợ: {file_path}")
            return ""

    @staticmethod
    def _read_txt(file_path: str) -> str:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()


class EnrollmentProcessor:
    """Xử lý và parse document thủ tục nhập học (Legacy Logic)"""
    
    def __init__(self, content: str, file_name: str):
        self.raw_content = content
        self.file_name = file_name
    
    def parse_document(self) -> Dict[str, Any]:
        """Parse document và trích xuất metadata"""
        content = self.raw_content
        
        # Extract year từ file name hoặc content
        year_match = re.search(r'(\d{4})', self.file_name)
        if not year_match:
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
            'raw_content': content,
            'source': self.file_name
        }
    
    def _parse_sections(self, content: str) -> List[Dict]:
        """Parse các PHẦN trong document"""
        sections = []
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
        lines = content.split('\n')
        return lines[0].strip() if lines else ""
    
    def _extract_metadata(self, content: str) -> Dict[str, Any]:
        metadata = {'deadlines': [], 'urls': [], 'fees': {}, 'contacts': {}, 'schedules': []}
        
        # Deadlines
        deadline_patterns = [
            r'trước (\d{1,2})\s+giờ.*?ngày\s+(\d{1,2}/\d{1,2}/\d{4})',
            r'sau ngày\s+(\d{1,2}/\d{1,2}/\d{4})',
            r'từ ngày\s+(\d{1,2}/\d{1,2}/\d{4})\s+đến.*?ngày\s+(\d{1,2}/\d{1,2}/\d{4})'
        ]
        for pattern in deadline_patterns:
            for match in re.finditer(pattern, content):
                metadata['deadlines'].append(match.group(0))
        
        # URLs
        metadata['urls'] = re.findall(r'https?://[^\s\)]+', content)
        
        # Fees
        fee_pattern = r'([^:]+?):\s*\.+\s*([\d.,]+)đ'
        for match in re.finditer(fee_pattern, content):
            fee_name = match.group(1).strip()
            fee_amount = match.group(2).replace('.', '').replace(',', '')
            try:
                metadata['fees'][fee_name] = int(fee_amount)
            except: pass
        
        # Contacts
        email = re.search(r'email:\s*([^\s;]+)', content, re.IGNORECASE)
        if email: metadata['contacts']['email'] = email.group(1)
        phone = re.search(r'điện thoại:\s*([\d.]+)', content, re.IGNORECASE)
        if phone: metadata['contacts']['phone'] = phone.group(1)
        
        # Schedules
        metadata['schedules'] = self._extract_schedules(content)
        return metadata

    def _extract_schedules(self, content: str) -> List[Dict]:
        schedules = []
        schedule_pattern = r'(Sáng|Chiều)\s+(thứ\s+\w+),\s+ngày\s+(\d{1,2}/\d{1,2}/\d{4})\s*(.*?)(?=Sáng|Chiều|\+|Thí sinh|$)'
        for match in re.finditer(schedule_pattern, content, re.DOTALL):
            majors = [m.strip() for m in match.group(4).split(';') if m.strip() and len(m.strip()) > 5]
            for major in majors:
                schedules.append({
                    'time_slot': match.group(1),
                    'day': match.group(2),
                    'date': match.group(3),
                    'major': major
                })
        return schedules


class GenericDocumentProcessor:
    """Xử lý document chung (không theo format nhập học) với chiến lược chunking cố định"""
    
    def __init__(self, content: str, file_name: str):
        self.content = content
        self.file_name = file_name
        
    def generate_chunks(self, chunk_size: int = 1000, overlap: int = 200) -> List[Dict[str, Any]]:
        """Tạo chunks theo kích thước cố định"""
        chunks = []
        content = self.content
        base_name = Path(self.file_name).stem
        
        # Trích xuất metadata sơ bộ
        # Tìm năm trong tên file hoặc 1000 ký tự đầu của content
        year_search_text = self.file_name + " " + content[:1000]
        year_match = re.search(r'(\d{4})', year_search_text)
        year = int(year_match.group(1)) if year_match else datetime.now().year
        
        i = 0
        chunk_idx = 0
        # Đảm bảo bước nhảy > 0
        step = max(1, chunk_size - overlap)
        
        while i < len(content):
            end = min(i + chunk_size, len(content))
            chunk_text = content[i:end]
            
            chunks.append({
                'chunk_id': f"gen_{base_name}_{chunk_idx}",
                'type': 'generic',
                'year': year,
                'title': f"Tài liệu: {base_name} (Phần {chunk_idx + 1})",
                'content': chunk_text,
                'source': self.file_name,
                'metadata': {
                    'keywords': self._extract_keywords(chunk_text)
                }
            })
            
            i += step
            chunk_idx += 1
            if i >= len(content) and len(content) > 0 and chunk_idx == 1:
                # Tránh lặp vô tận nếu i không tiến (dù step đã > 0)
                break
            
        return chunks

    def _extract_keywords(self, text: str) -> List[str]:
        # Simple keywords extraction
        words = re.findall(r'\w{4,}', text.lower())
        stopwords = {'trong', 'không', 'những', 'chúng', 'người', 'nhưng', 'được', 'của', 'với'}
        keywords = [w for w in words if w not in stopwords]
        # Trả về 10 từ xuất hiện nhiều nhất (unique)
        unique_keywords = []
        for w in keywords:
            if w not in unique_keywords:
                unique_keywords.append(w)
            if len(unique_keywords) >= 10:
                break
        return unique_keywords


class ChunkGenerator:
    """Điều phối việc tạo chunks từ dữ liệu đã parse (Enrollment)"""
    
    def __init__(self, parsed_data: Dict[str, Any]):
        self.data = parsed_data
        self.chunks = []
    
    def generate_all_chunks(self) -> List[Dict[str, Any]]:
        year = self.data['year']
        src = Path(self.data['source']).stem
        
        # Level 1: Overview
        self.chunks.append(self._create_overview_chunk())
        
        # Level 2: Section chunks
        for section in self.data['sections']:
            self.chunks.append(self._create_section_chunk(section))
        
        # Level 3: Step chunks & Document list chunks
        sec4 = next((s for s in self.data['sections'] if s['section_number'] == 4), None)
        if sec4:
            self.chunks.extend(self._create_step_chunks(sec4))
            self.chunks.extend(self._create_document_list_chunks(sec4))
        
        # Level 4: Details
        self.chunks.append(self._create_fee_chunk())
        self.chunks.extend(self._create_schedule_chunks())
        
        # Thêm source info vào tất cả chunks
        for chunk in self.chunks:
            chunk['source'] = self.data['source']
            # Re-key chunk_id để tránh trùng nếu có nhiều file
            chunk['chunk_id'] = f"{src}_{chunk['chunk_id']}"
            
        return self.chunks

    def _create_overview_chunk(self) -> Dict[str, Any]:
        year = self.data['year']
        total_fee = sum(self.data['metadata']['fees'].values())
        content = f"Tổng quan thủ tục nhập học năm {year} (từ {self.data['source']}).\n"
        content += f"Gồm {len(self.data['sections'])} phần chính. Tổng học phí: {total_fee:,}đ"
        
        return {
            'chunk_id': f'admission_{year}_overview',
            'type': 'overview',
            'year': year,
            'title': f'Thủ tục nhập học {year} - Tổng quan ({Path(self.data["source"]).name})',
            'content': content,
            'metadata': {'keywords': ['nhập học', str(year)]}
        }

    def _create_section_chunk(self, section: Dict) -> Dict[str, Any]:
        return {
            'chunk_id': f"section_{section['section_number']}",
            'type': 'section',
            'year': self.data['year'],
            'title': f"PHẦN {section['section_number']}: {section['title']}",
            'content': section['content'],
            'metadata': {'keywords': []}
        }

    def _create_step_chunks(self, section_4: Dict) -> List[Dict]:
        """Tạo chunks cho các bước B1, B2, B3, B4"""
        steps = []
        # Regex tìm B1, B2... và nội dung đến bước tiếp theo hoặc phần nộp hồ sơ
        matches = re.finditer(r'B(\d+):(.*?)(?=B\d+:|Thí sinh nộp các hồ sơ dưới đây|$)', section_4['content'], re.DOTALL)
        for match in matches:
            num = match.group(1)
            steps.append({
                'chunk_id': f"section_4_step_{num}",
                'type': 'step',
                'year': self.data['year'],
                'title': f"Bước {num}",
                'content': f"Bước {num}: " + match.group(2).strip(),
                'metadata': {'keywords': ['bước', num]}
            })
        return steps

    def _create_document_list_chunks(self, section_4: Dict) -> List[Dict]:
        """Tạo chunks cho danh sách hồ sơ (1-13)"""
        chunks = []
        content = section_4['content']
        
        # Tìm phần danh sách hồ sơ
        doc_list_match = re.search(r'(Thí sinh nộp các hồ sơ dưới đây:.*)', content, re.DOTALL)
        if doc_list_match:
            doc_content = doc_list_match.group(1).strip()
            # Tách thành 2 phần: Nộp trong hồ sơ và Nộp theo lớp nế muốn chi tiết hơn, 
            # nhưng để đảm bảo đầy đủ, ta tạo 1 chunk lớn cho document_list trước
            chunks.append({
                'chunk_id': "document_list_full",
                'type': 'document_list',
                'year': self.data['year'],
                'title': "Danh sách hồ sơ cần nộp (Bản cứng và bản sao công chứng)",
                'content': doc_content,
                'metadata': {'keywords': ['hồ sơ', 'giấy tờ', 'nộp']}
            })
            
            # Tách nhỏ hơn: Nộp trong ngày nhập học
            immediate_docs = re.search(r'(\+ Nộp trong.*?)(?=\+ Nộp|$)', doc_content, re.DOTALL)
            if immediate_docs:
                chunks.append({
                    'chunk_id': "document_list_immediate",
                    'type': 'document_list',
                    'year': self.data['year'],
                    'title': "Hồ sơ nộp trực tiếp trong ngày nhập học",
                    'content': immediate_docs.group(1).strip(),
                    'metadata': {'keywords': ['nộp ngay', 'nhập học']}
                })
            
            # Tách nhỏ hơn: Nộp theo lớp
            later_docs = re.search(r'(\+ Nộp.*?theo lớp.*)', doc_content, re.DOTALL)
            if later_docs:
                chunks.append({
                    'chunk_id': "document_list_later",
                    'type': 'document_list',
                    'year': self.data['year'],
                    'title': "Hồ sơ nộp bổ sung theo lớp sau khi nhập học",
                    'content': later_docs.group(1).strip(),
                    'metadata': {'keywords': ['nộp sau', 'theo lớp']}
                })
                
        return chunks

    def _create_fee_chunk(self) -> Dict[str, Any]:
        fees = self.data['metadata']['fees']
        content = "Chi tiết học phí:\n" + "\n".join([f"- {k}: {v:,}đ" for k,v in fees.items()])
        return {
            'chunk_id': f"fees",
            'type': 'fee_info',
            'year': self.data['year'],
            'title': 'Chi tiết học phí',
            'content': content,
            'total_required': sum(fees.values()),
            'metadata': {'keywords': ['học phí']}
        }

    def _create_schedule_chunks(self) -> List[Dict]:
        chunks = []
        for idx, s in enumerate(self.data['metadata']['schedules']):
            chunks.append({
                'chunk_id': f"schedule_{idx}",
                'type': 'schedule',
                'year': self.data['year'],
                'title': f"Lịch nhập học - {s['major']}",
                'content': f"{s['time_slot']} {s['day']}, ngày {s['date']}: {s['major']}",
                'metadata': {'keywords': [s['major'], s['date']]}
            })
        return chunks


def process_all_data(data_dir: str = 'data') -> List[Dict[str, Any]]:
    """Xử lý tất cả các file trong thư mục data"""
    all_chunks = []
    
    # Tìm các file hỗ trợ
    files = []
    for ext in ['*.txt', '*.docx', '*.pdf']:
        files.extend(glob.glob(os.path.join(data_dir, ext)))
    
    print(f"📂 Tìm thấy {len(files)} file tài liệu.")
    
    for file_path in files:
        file_name = os.path.basename(file_path)
        print(f"[DOCUMENT] Đang xử lý: {file_name}...")
        
        # 1. Trích xuất text
        content = TextExtractor.extract(file_path)
        if not content:
            continue
            
        # 2. Quyết định dùng processor nào
        # Nếu tên file có "Thủ tục nhập học" thì dùng EnrollmentProcessor, nếu không dùng Generic
        if "thủ tục nhập học" in file_name.lower():
            print(f"   ✨ Sử dụng EnrollmentProcessor cho {file_name}")
            processor = EnrollmentProcessor(content, file_name)
            parsed_data = processor.parse_document()
            gen = ChunkGenerator(parsed_data)
            chunks = gen.generate_all_chunks()
            all_chunks.extend(chunks)
        else:
            print(f"   📦 Sử dụng GenericDocumentProcessor cho {file_name}")
            processor = GenericDocumentProcessor(content, file_path)
            chunks = processor.generate_chunks()
            all_chunks.extend(chunks)
            
    return all_chunks


def main():
    """Main pipeline Phase 1"""
    print("=" * 70)
    print("PHASE 1: Universal Document Processing & Chunking")
    print("=" * 70)
    print()
    
    chunks = process_all_data('data')
    
    print(f"\n[OK] Hoàn thành! Tổng số chunks đã tạo: {len(chunks)}")
    
    # Lưu ra file
    output_file = 'all_chunks.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
    print(f"💾 Đã lưu vào {output_file}")
    
    # Thống kê
    stats = {}
    for c in chunks:
        t = c['type']
        stats[t] = stats.get(t, 0) + 1
    
    print("\n[STATS] Thống kê loại chunks:")
    for t, count in stats.items():
        print(f"   - {t}: {count}")


if __name__ == '__main__':
    main()
