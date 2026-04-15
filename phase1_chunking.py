"""
PHASE 1: Document Processing & Chunking
Module để parse document (TXT, DOCX, PDF) và tạo chunks theo hierarchy 4 level (top-down)
"""

import re
import json
import os
import glob
import unicodedata
from typing import List, Dict, Any, Optional, Tuple
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
        if ext == '.docx':
            return DocxProcessor.extract_text(file_path)
        if ext == '.pdf':
            return PdfProcessor.extract_text(file_path)
        print(f"[WARNING] Định dạng file {ext} chưa được hỗ trợ: {file_path}")
        return ""

    @staticmethod
    def _read_txt(file_path: str) -> str:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()


def _normalize_text(s: str) -> str:
    s = unicodedata.normalize('NFKC', s or '')
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def _normalize_key(s: str) -> str:
    s = _normalize_text(s).lower()
    s = ''.join(ch for ch in unicodedata.normalize('NFD', s) if unicodedata.category(ch) != 'Mn')
    s = s.replace('đ', 'd')
    s = re.sub(r'[^a-z0-9\s]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s


class EnrollmentProcessor:
    """Xử lý và parse document thủ tục nhập học theo hierarchy 4 level"""

    def __init__(self, content: str, file_name: str):
        self.raw_content = content
        self.file_name = file_name
        self.year = self._extract_year()

    def _extract_year(self) -> int:
        year_match = re.search(r'(\d{4})', self.file_name)
        if not year_match:
            year_match = re.search(r'năm\s+(\d{4})', self.raw_content, flags=re.IGNORECASE)
        return int(year_match.group(1)) if year_match else 2025

    def _parse_level1_sections(self) -> List[Dict[str, Any]]:
        """Top-down step 1: tách Level 1 theo PHẦN 1..4"""
        content = self.raw_content
        pattern = r'PHẦN\s+(\d+)\s*:\s*(.*?)(?=\n\s*PHẦN\s+\d+\s*:|\Z)'
        sections = []
        for m in re.finditer(pattern, content, re.DOTALL | re.IGNORECASE):
            num = int(m.group(1))
            sec_content = m.group(2).strip()
            first_line = sec_content.split('\n', 1)[0].strip()
            sections.append({
                'section_number': num,
                'title': first_line[:200],
                'content': sec_content
            })
        return sections

    def _extract_links(self, text: str) -> List[str]:
        return re.findall(r'https?://[^\s\)]+', text)

    def _extract_all_dates(self, text: str) -> List[str]:
        raw = re.findall(r'\d{1,2}[/-]\d{1,2}[/-]\d{4}', text)
        return list(dict.fromkeys(raw))

    def _extract_contacts(self, text: str) -> Dict[str, str]:
        out = {}
        phone = re.search(r'điện thoại\s*:\s*([0-9\.\s]+)', text, re.IGNORECASE)
        if phone:
            out['phone'] = _normalize_text(phone.group(1))
        email = re.search(r'email\s*:\s*([^\s;\)]+)', text, re.IGNORECASE)
        if email:
            out['email'] = email.group(1).strip()
        fanpage = re.search(r'fanpage\s*:\s*(https?://[^\s\)]+)', text, re.IGNORECASE)
        if fanpage:
            out['fanpage'] = fanpage.group(1).strip()
        return out

    def _extract_fee_items(self, section3_text: str) -> List[Dict[str, Any]]:
        items = []
        line_pattern = r'^\s*(\d+)\.\s*(.+?)\s*[:：]\s*[^0-9]*([\d\.,]+)\s*đ(.*)$'
        for line in section3_text.splitlines():
            m = re.match(line_pattern, line.strip(), flags=re.IGNORECASE)
            if not m:
                continue
            idx = int(m.group(1))
            name = _normalize_text(m.group(2))
            amount_raw = m.group(3).replace('.', '').replace(',', '')
            note = _normalize_text(m.group(4))
            try:
                amount = int(amount_raw)
            except Exception:
                continue
            items.append({
                'item_no': idx,
                'name': name,
                'amount': amount,
                'note': note
            })
        return sorted(items, key=lambda x: x['item_no'])

    def _extract_steps(self, section4_text: str) -> List[Dict[str, str]]:
        steps = []
        pattern = r'(B([1-4])\s*:\s*)(.*?)(?=\n\s*B[1-4]\s*:|\n\s*Sáng\s+từ|\n\s*Thí\s+sinh\s+nộp\s+các\s+hồ\s+sơ|\n\s*Lưu\s+ý\s*:|\Z)'
        for m in re.finditer(pattern, section4_text, re.DOTALL | re.IGNORECASE):
            step_no = int(m.group(2))
            content = _normalize_text(m.group(3))
            steps.append({'step_number': step_no, 'content': content})
        return steps

    def _extract_schedule_sessions(self, section4_text: str) -> List[Dict[str, Any]]:
        sessions = []
        header_pat = r'(Sáng|Chiều)\s+thứ\s+[^\n,]+,\s*ngày\s*(\d{1,2}/\d{1,2}/\d{4})'
        headers = list(re.finditer(header_pat, section4_text, re.IGNORECASE))
        for i, h in enumerate(headers):
            start = h.end()
            end = headers[i + 1].start() if i + 1 < len(headers) else len(section4_text)
            block = section4_text[start:end]
            block = re.split(r'\n\s*Thí\s+sinh\s+nộp\s+các\s+hồ\s+sơ', block, maxsplit=1, flags=re.IGNORECASE)[0]
            majors = []
            for seg in re.split(r'[;\n]', block):
                item = _normalize_text(seg)
                if not item:
                    continue
                if len(item) < 4:
                    continue
                if item.lower().startswith('sáng từ') or item.lower().startswith('chiều từ'):
                    continue
                majors.append(item.rstrip('.'))
            sessions.append({
                'time_slot': h.group(1).capitalize(),
                'date': h.group(2),
                'majors': majors
            })
        return sessions

    def _extract_doc_groups(self, section4_text: str) -> Dict[str, List[Dict[str, str]]]:
        same_day = []
        later = []

        same_day_match = re.search(
            r'\+\s*Nộp\s+trong\s+ngày\s+nhập\s+học\s*:\s*(.*?)(?=\n\s*\+\s*Nộp\s*\(\s*từ\s*ngày\s*07\s*đến\s*28/9/2025\)|\Z)',
            section4_text,
            re.DOTALL | re.IGNORECASE
        )
        if same_day_match:
            for m in re.finditer(r'\n?\s*(\d+)\.\s*(.+?)(?=\n\s*\d+\.|\Z)', same_day_match.group(1), re.DOTALL):
                same_day.append({'item_no': m.group(1), 'content': _normalize_text(m.group(2))})

        later_match = re.search(
            r'\+\s*Nộp\s*\(\s*từ\s*ngày\s*07\s*đến\s*28/9/2025\)\s*theo\s+lớp\s+khi\s+đi\s+học\s+chính\s+thức\s*:\s*(.*?)(?=\n\s*Lưu\s+ý\s*:|\Z)',
            section4_text,
            re.DOTALL | re.IGNORECASE
        )
        if later_match:
            for m in re.finditer(r'\n?\s*(\d+)\.\s*(.+?)(?=\n\s*\d+\.|\Z)', later_match.group(1), re.DOTALL):
                later.append({'item_no': m.group(1), 'content': _normalize_text(m.group(2))})

        return {'same_day': same_day, 'later': later}

    def _extract_notes_and_contact(self, section4_text: str) -> Dict[str, str]:
        notes = ''
        contact = ''
        m_notes = re.search(r'Lưu\s+ý\s*:\s*(.*?)(?=\n\s*Thông\s+tin\s+về\s+nhập\s+học\s+xin\s+liên\s+hệ\s*:|\Z)', section4_text, re.DOTALL | re.IGNORECASE)
        if m_notes:
            notes = _normalize_text(m_notes.group(1))
        m_contact = re.search(r'Thông\s+tin\s+về\s+nhập\s+học\s+xin\s+liên\s+hệ\s*:\s*(.*)$', section4_text, re.DOTALL | re.IGNORECASE)
        if m_contact:
            contact = _normalize_text(m_contact.group(1))
        return {'notes': notes, 'contact': contact}

    def _chunk(self,
               chunk_id: str,
               level: int,
               parent_id: Optional[str],
               chunk_type: str,
               subtype: str,
               intent_key: str,
               title: str,
               content: str,
               extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        base = {
            'chunk_id': chunk_id,
            'level': level,
            'parent_id': parent_id,
            'type': chunk_type,
            'subtype': subtype,
            'intent_key': intent_key,
            'topic': intent_key,
            'year': self.year,
            'title': title,
            'content': _normalize_text(content),
            'source': self.file_name,
            'metadata': {
                'level': level,
                'parent_id': parent_id,
                'type': chunk_type,
                'subtype': subtype,
                'intent_key': intent_key,
                'source': self.file_name,
                'year': self.year
            }
        }
        if extra:
            for k, v in extra.items():
                base[k] = v
                base['metadata'][k] = v
        return base

    def generate_chunks(self) -> List[Dict[str, Any]]:
        sections = self._parse_level1_sections()
        src_prefix = Path(self.file_name).stem
        chunks: List[Dict[str, Any]] = []

        # LEVEL 0: full summary
        all_dates = self._extract_all_dates(self.raw_content)
        all_links = self._extract_links(self.raw_content)
        overview_text = (
            f"Tổng quan thủ tục nhập học năm {self.year}. "
            f"Tài liệu có {len(sections)} phần chính (PHẦN 1-4), bao gồm tra cứu trúng tuyển, "
            "xác nhận trực tuyến, nộp học phí/lệ phí, quy trình B1-B4, lịch theo ngành, hồ sơ và lưu ý."
        )
        chunks.append(self._chunk(
            chunk_id=f"{src_prefix}_l0_overview",
            level=0,
            parent_id=None,
            chunk_type='overview',
            subtype='full_summary',
            intent_key='deadlines_summary',
            title=f"Tổng quan nhập học {self.year}",
            content=overview_text,
            extra={
                'dates': all_dates,
                'links': all_links
            }
        ))

        # LEVEL 1: PHẦN lớn (top-down step 2)
        level1_ids: Dict[int, str] = {}
        section_map: Dict[int, Dict[str, Any]] = {}
        for sec in sections:
            sn = sec['section_number']
            section_map[sn] = sec
            intent_map = {
                1: 'lookup',
                2: 'online_confirmation',
                3: 'fee_info',
                4: 'admission_procedure'
            }
            c_id = f"{src_prefix}_l1_section_{sn}"
            level1_ids[sn] = c_id
            chunks.append(self._chunk(
                chunk_id=c_id,
                level=1,
                parent_id=f"{src_prefix}_l0_overview",
                chunk_type='section',
                subtype=f'section_{sn}',
                intent_key=intent_map.get(sn, 'admission_procedure'),
                title=f"PHẦN {sn}",
                content=sec['content'],
                extra={
                    'section_number': sn,
                    'links': self._extract_links(sec['content']),
                    'dates': self._extract_all_dates(sec['content'])
                }
            ))

        # LEVEL 2 + LEVEL 3 theo từng PHẦN
        # PHẦN 1: lookup
        sec1 = section_map.get(1, {})
        if sec1:
            c2 = self._chunk(
                chunk_id=f"{src_prefix}_l2_lookup",
                level=2,
                parent_id=level1_ids[1],
                chunk_type='subsection',
                subtype='lookup_main',
                intent_key='lookup',
                title='Tra cứu danh sách trúng tuyển',
                content=sec1['content'],
                extra={
                    'links': self._extract_links(sec1['content']),
                    'dates': self._extract_all_dates(sec1['content'])
                }
            )
            chunks.append(c2)
            m_after = re.search(r'sau\s+ngày\s+(\d{1,2}/\d{1,2}/\d{4})', sec1['content'], re.IGNORECASE)
            chunks.append(self._chunk(
                chunk_id=f"{src_prefix}_l3_lookup_detail",
                level=3,
                parent_id=c2['chunk_id'],
                chunk_type='detail',
                subtype='lookup_detail',
                intent_key='lookup',
                title='Mốc tra cứu và cổng thông tin',
                content=sec1['content'],
                extra={
                    'deadline_start': m_after.group(1) if m_after else None,
                    'url': self._extract_links(sec1['content'])[0] if self._extract_links(sec1['content']) else None
                }
            ))

        # PHẦN 2: online confirmation
        sec2 = section_map.get(2, {})
        if sec2:
            c2 = self._chunk(
                chunk_id=f"{src_prefix}_l2_online_confirmation",
                level=2,
                parent_id=level1_ids[2],
                chunk_type='subsection',
                subtype='online_confirmation_main',
                intent_key='online_confirmation',
                title='Xác nhận nhập học trực tuyến',
                content=sec2['content'],
                extra={
                    'dates': self._extract_all_dates(sec2['content'])
                }
            )
            chunks.append(c2)
            m_deadline = re.search(r'trước\s*17\s*giờ\s*00.*?ngày\s*(\d{1,2}/\d{1,2}/\d{4})', sec2['content'], re.IGNORECASE)
            chunks.append(self._chunk(
                chunk_id=f"{src_prefix}_l3_online_confirmation_deadline",
                level=3,
                parent_id=c2['chunk_id'],
                chunk_type='detail',
                subtype='online_confirmation_deadline',
                intent_key='online_confirmation',
                title='Hạn xác nhận trực tuyến',
                content=sec2['content'],
                extra={
                    'deadline_end': m_deadline.group(1) if m_deadline else None,
                    'time_slot': 'trước 17 giờ 00'
                }
            ))

        # PHẦN 3: fee_info
        sec3 = section_map.get(3, {})
        if sec3:
            c2 = self._chunk(
                chunk_id=f"{src_prefix}_l2_fees",
                level=2,
                parent_id=level1_ids[3],
                chunk_type='subsection',
                subtype='fee_overview',
                intent_key='fee_info',
                title='Nộp học phí tạm thu, lệ phí nhập học',
                content=sec3['content'],
                extra={
                    'dates': self._extract_all_dates(sec3['content'])
                }
            )
            chunks.append(c2)

            fee_items = self._extract_fee_items(sec3['content'])
            total_fee = sum(i['amount'] for i in fee_items)
            chunks.append(self._chunk(
                chunk_id=f"{src_prefix}_l3_fee_total",
                level=3,
                parent_id=c2['chunk_id'],
                chunk_type='detail',
                subtype='fee_total',
                intent_key='fee_info',
                title='Tổng các khoản tiền',
                content='; '.join([f"{it['item_no']}. {it['name']}: {it['amount']:,}đ" for it in fee_items]),
                extra={
                    'total_required': total_fee,
                    'fee_count': len(fee_items)
                }
            ))

            # Bổ sung chunk payment window để câu hỏi "hình thức/khung ngày nộp học phí" có mốc thời gian
            m_window = re.search(
                r'thực hiện\s+từ\s+ngày\s*(\d{1,2}/\d{1,2}/\d{4})\s+đến(?:\s+hết)?\s+ngày\s*(\d{1,2}/\d{1,2}/\d{4})',
                sec3['content'],
                re.IGNORECASE
            )
            if m_window:
                chunks.append(self._chunk(
                    chunk_id=f"{src_prefix}_l3_fee_payment_window",
                    level=3,
                    parent_id=c2['chunk_id'],
                    chunk_type='detail',
                    subtype='payment_window',
                    intent_key='fee_payment',
                    title='Khung thời gian nộp học phí',
                    content=f"Nộp học phí thực hiện từ ngày {m_window.group(1)} đến hết ngày {m_window.group(2)}.",
                    extra={
                        'deadline_start': m_window.group(1),
                        'deadline_end': m_window.group(2)
                    }
                ))

            m_method = re.search(r'(theo\s+hình\s+thức\s+chuyển\s+khoản)', sec3['content'], re.IGNORECASE)
            if m_method:
                chunks.append(self._chunk(
                    chunk_id=f"{src_prefix}_l3_fee_payment_method",
                    level=3,
                    parent_id=c2['chunk_id'],
                    chunk_type='detail',
                    subtype='payment_method',
                    intent_key='fee_payment',
                    title='Hình thức nộp học phí',
                    content='Nộp học phí theo hình thức chuyển khoản.',
                    extra={'payment_method': 'chuyển khoản'}
                ))

            for item in fee_items:
                chunks.append(self._chunk(
                    chunk_id=f"{src_prefix}_l3_fee_item_{item['item_no']}",
                    level=3,
                    parent_id=c2['chunk_id'],
                    chunk_type='detail',
                    subtype='fee_item',
                    intent_key='fee_info',
                    title=f"Khoản phí {item['item_no']}",
                    content=f"{item['name']}: {item['amount']:,}đ {item['note']}".strip(),
                    extra={
                        'item_no': item['item_no'],
                        'amount': item['amount']
                    }
                ))

        # PHẦN 4: procedure, step, schedule, docs, notes, contact
        sec4 = section_map.get(4, {})
        if sec4:
            sec4_text = sec4['content']

            # split level2 blocks under section 4
            idx_steps = re.search(r'\n\s*B1\s*:', sec4_text, re.IGNORECASE)
            idx_docs = re.search(r'\n\s*Thí\s+sinh\s+nộp\s+các\s+hồ\s+sơ\s+dưới\s+đây\s*:', sec4_text, re.IGNORECASE)
            idx_notes = re.search(r'\n\s*Lưu\s+ý\s*:', sec4_text, re.IGNORECASE)
            idx_contact = re.search(r'\n\s*Thông\s+tin\s+về\s+nhập\s+học\s+xin\s+liên\s+hệ\s*:', sec4_text, re.IGNORECASE)

            steps_block = ''
            schedule_block = ''
            docs_block = ''
            notes_block = ''
            contact_block = ''

            if idx_steps:
                start = idx_steps.start()
                end = idx_docs.start() if idx_docs else (idx_notes.start() if idx_notes else len(sec4_text))
                steps_and_schedule = sec4_text[start:end]
                schedule_anchor = re.search(r'\n\s*Sáng\s+từ\s+\d', steps_and_schedule, re.IGNORECASE)
                if schedule_anchor:
                    steps_block = steps_and_schedule[:schedule_anchor.start()]
                    schedule_block = steps_and_schedule[schedule_anchor.start():]
                else:
                    steps_block = steps_and_schedule

            if idx_docs:
                start = idx_docs.start()
                end = idx_notes.start() if idx_notes else len(sec4_text)
                docs_block = sec4_text[start:end]
            if idx_notes:
                start = idx_notes.start()
                end = idx_contact.start() if idx_contact else len(sec4_text)
                notes_block = sec4_text[start:end]
            if idx_contact:
                contact_block = sec4_text[idx_contact.start():]

            # Level2 procedure header
            c2_proc = self._chunk(
                chunk_id=f"{src_prefix}_l2_procedure",
                level=2,
                parent_id=level1_ids[4],
                chunk_type='subsection',
                subtype='procedure_overview',
                intent_key='admission_procedure',
                title='Quy trình chuẩn bị và nộp hồ sơ',
                content=sec4_text,
                extra={'dates': self._extract_all_dates(sec4_text)}
            )
            chunks.append(c2_proc)

            # Level2 steps
            c2_steps = self._chunk(
                chunk_id=f"{src_prefix}_l2_steps",
                level=2,
                parent_id=level1_ids[4],
                chunk_type='subsection',
                subtype='steps_group',
                intent_key='admission_procedure',
                title='Các bước B1-B4',
                content=steps_block or sec4_text,
                extra={}
            )
            chunks.append(c2_steps)
            for step in self._extract_steps(steps_block or sec4_text):
                chunks.append(self._chunk(
                    chunk_id=f"{src_prefix}_l3_step_b{step['step_number']}",
                    level=3,
                    parent_id=c2_steps['chunk_id'],
                    chunk_type='detail',
                    subtype=f"step_b{step['step_number']}",
                    intent_key='step',
                    title=f"Bước B{step['step_number']}",
                    content=step['content'],
                    extra={'step_number': step['step_number']}
                ))

            # Level2 schedule
            c2_schedule = self._chunk(
                chunk_id=f"{src_prefix}_l2_schedule",
                level=2,
                parent_id=level1_ids[4],
                chunk_type='subsection',
                subtype='schedule_group',
                intent_key='schedule_by_major',
                title='Lịch nộp hồ sơ bản giấy theo ngành',
                content=schedule_block or sec4_text,
                extra={}
            )
            chunks.append(c2_schedule)

            # session-level chunk cho câu hỏi "buổi sáng/buổi chiều mấy giờ"
            session_time_match = re.search(
                r'Sáng\s+từ\s*(\d{1,2}\s*giờ\s*\d{1,2})\s*÷\s*(\d{1,2}\s*giờ\s*\d{1,2})\s*;\s*Chiều\s+từ\s*(\d{1,2}\s*giờ\s*\d{1,2})\s*÷\s*(\d{1,2}\s*giờ\s*\d{1,2})',
                schedule_block or sec4_text,
                flags=re.IGNORECASE
            )
            if session_time_match:
                chunks.append(self._chunk(
                    chunk_id=f"{src_prefix}_l3_schedule_session_morning",
                    level=3,
                    parent_id=c2_schedule['chunk_id'],
                    chunk_type='detail',
                    subtype='schedule_session',
                    intent_key='schedule_session',
                    title='Khung giờ buổi sáng',
                    content=f"Buổi sáng: từ {session_time_match.group(1)} đến {session_time_match.group(2)}",
                    extra={'time_slot': 'Sáng', 'session_start': session_time_match.group(1), 'session_end': session_time_match.group(2)}
                ))
                chunks.append(self._chunk(
                    chunk_id=f"{src_prefix}_l3_schedule_session_afternoon",
                    level=3,
                    parent_id=c2_schedule['chunk_id'],
                    chunk_type='detail',
                    subtype='schedule_session',
                    intent_key='schedule_session',
                    title='Khung giờ buổi chiều',
                    content=f"Buổi chiều: từ {session_time_match.group(3)} đến {session_time_match.group(4)}",
                    extra={'time_slot': 'Chiều', 'session_start': session_time_match.group(3), 'session_end': session_time_match.group(4)}
                ))

            sch_idx = 0
            for sess in self._extract_schedule_sessions(schedule_block or sec4_text):
                for major in sess['majors']:
                    sch_idx += 1
                    chunks.append(self._chunk(
                        chunk_id=f"{src_prefix}_l3_schedule_{sch_idx}",
                        level=3,
                        parent_id=c2_schedule['chunk_id'],
                        chunk_type='detail',
                        subtype='schedule_major',
                        intent_key='schedule_by_major',
                        title=f"Lịch ngành {major}",
                        content=f"{sess['time_slot']} ngày {sess['date']}: {major}",
                        extra={
                            'major': major,
                            'major_norm': _normalize_key(major),
                            'date': sess['date'],
                            'time_slot': sess['time_slot']
                        }
                    ))

            # tổng hợp steps B1-B4 để trả lời câu hỏi chung "các bước"
            step_chunks = [c for c in chunks if c.get('parent_id') == c2_steps['chunk_id'] and (c.get('metadata', {}) or {}).get('intent_key') == 'step']
            if step_chunks:
                step_chunks = sorted(step_chunks, key=lambda c: (c.get('metadata', {}) or {}).get('step_number', 99))
                combined_steps = []
                for sc in step_chunks:
                    md = sc.get('metadata', {}) or {}
                    combined_steps.append(f"B{md.get('step_number')}: {sc.get('content', '')}")
                chunks.append(self._chunk(
                    chunk_id=f"{src_prefix}_l3_steps_overview",
                    level=3,
                    parent_id=c2_steps['chunk_id'],
                    chunk_type='detail',
                    subtype='steps_overview',
                    intent_key='admission_procedure',
                    title='Tổng hợp các bước B1-B4',
                    content='\n'.join(combined_steps),
                    extra={}
                ))

            # Level2 docs
            c2_docs = self._chunk(
                chunk_id=f"{src_prefix}_l2_docs",
                level=2,
                parent_id=level1_ids[4],
                chunk_type='subsection',
                subtype='docs_group',
                intent_key='document_required',
                title='Danh mục hồ sơ cần nộp',
                content=docs_block,
                extra={}
            )
            chunks.append(c2_docs)
            doc_groups = self._extract_doc_groups(docs_block)

            c2_docs_same = self._chunk(
                chunk_id=f"{src_prefix}_l2_docs_same_day",
                level=2,
                parent_id=c2_docs['chunk_id'],
                chunk_type='subsection',
                subtype='docs_same_day_group',
                intent_key='docs_same_day',
                title='Hồ sơ nộp trong ngày nhập học',
                content=' '.join([f"{d['item_no']}. {d['content']}" for d in doc_groups['same_day']]) or docs_block,
                extra={}
            )
            chunks.append(c2_docs_same)
            for d in doc_groups['same_day']:
                chunks.append(self._chunk(
                    chunk_id=f"{src_prefix}_l3_docs_same_day_{d['item_no']}",
                    level=3,
                    parent_id=c2_docs_same['chunk_id'],
                    chunk_type='detail',
                    subtype='docs_same_day_item',
                    intent_key='docs_same_day',
                    title=f"Hồ sơ trong ngày mục {d['item_no']}",
                    content=d['content'],
                    extra={'item_no': int(d['item_no'])}
                ))

            c2_docs_later = self._chunk(
                chunk_id=f"{src_prefix}_l2_docs_later",
                level=2,
                parent_id=c2_docs['chunk_id'],
                chunk_type='subsection',
                subtype='docs_later_group',
                intent_key='docs_later',
                title='Hồ sơ nộp theo lớp sau nhập học',
                content=' '.join([f"{d['item_no']}. {d['content']}" for d in doc_groups['later']]) or docs_block,
                extra={
                    'deadline_start': '07/09/2025',
                    'deadline_end': '28/09/2025'
                }
            )
            chunks.append(c2_docs_later)
            for d in doc_groups['later']:
                chunks.append(self._chunk(
                    chunk_id=f"{src_prefix}_l3_docs_later_{d['item_no']}",
                    level=3,
                    parent_id=c2_docs_later['chunk_id'],
                    chunk_type='detail',
                    subtype='docs_later_item',
                    intent_key='docs_later',
                    title=f"Hồ sơ nộp sau mục {d['item_no']}",
                    content=d['content'],
                    extra={'item_no': int(d['item_no'])}
                ))

            # docs group as admission_procedure để câu hỏi tổng quát vẫn deterministic
            if doc_groups['same_day']:
                chunks.append(self._chunk(
                    chunk_id=f"{src_prefix}_l3_docs_same_day_overview",
                    level=3,
                    parent_id=c2_docs['chunk_id'],
                    chunk_type='detail',
                    subtype='docs_same_day_overview',
                    intent_key='admission_procedure',
                    title='Hồ sơ nộp trong ngày nhập học (tóm tắt)',
                    content='; '.join([f"({d['item_no']}) {d['content']}" for d in doc_groups['same_day']]),
                    extra={}
                ))
            if doc_groups['later']:
                chunks.append(self._chunk(
                    chunk_id=f"{src_prefix}_l3_docs_later_overview",
                    level=3,
                    parent_id=c2_docs['chunk_id'],
                    chunk_type='detail',
                    subtype='docs_later_overview',
                    intent_key='admission_procedure',
                    title='Hồ sơ nộp theo lớp (tóm tắt)',
                    content='; '.join([f"({d['item_no']}) {d['content']}" for d in doc_groups['later']]),
                    extra={'deadline_start': '07/09/2025', 'deadline_end': '28/09/2025'}
                ))

            # Level2 notes + level3 note item lines
            notes_contact = self._extract_notes_and_contact(sec4_text)
            if notes_block or notes_contact['notes']:
                c2_notes = self._chunk(
                    chunk_id=f"{src_prefix}_l2_notes",
                    level=2,
                    parent_id=level1_ids[4],
                    chunk_type='subsection',
                    subtype='notes_group',
                    intent_key='notes',
                    title='Lưu ý cho tân sinh viên',
                    content=notes_contact['notes'] or notes_block,
                    extra={}
                )
                chunks.append(c2_notes)
                idx = 0
                for m in re.finditer(r'(\d+)\.\s*(.+?)(?=\s+\d+\.|$)', notes_contact['notes'] or notes_block):
                    idx += 1
                    chunks.append(self._chunk(
                        chunk_id=f"{src_prefix}_l3_note_{idx}",
                        level=3,
                        parent_id=c2_notes['chunk_id'],
                        chunk_type='detail',
                        subtype='note_item',
                        intent_key='notes',
                        title=f"Lưu ý {m.group(1)}",
                        content=m.group(2),
                        extra={'item_no': int(m.group(1))}
                    ))

            # Level2 contact + level3 fields
            if contact_block or notes_contact['contact']:
                c2_contact = self._chunk(
                    chunk_id=f"{src_prefix}_l2_contact",
                    level=2,
                    parent_id=level1_ids[4],
                    chunk_type='subsection',
                    subtype='contact_group',
                    intent_key='contact',
                    title='Thông tin liên hệ',
                    content=notes_contact['contact'] or contact_block,
                    extra=self._extract_contacts(notes_contact['contact'] or contact_block)
                )
                chunks.append(c2_contact)

            # deadlines summary level2+3
            deadline_entries = []
            for d in all_dates:
                deadline_entries.append(f"- {d}")
            c2_deadline = self._chunk(
                chunk_id=f"{src_prefix}_l2_deadlines",
                level=2,
                parent_id=f"{src_prefix}_l0_overview",
                chunk_type='subsection',
                subtype='deadlines_group',
                intent_key='deadlines_summary',
                title='Tổng hợp mốc thời gian',
                content='\n'.join(deadline_entries) if deadline_entries else self.raw_content[:500],
                extra={'dates': all_dates}
            )
            chunks.append(c2_deadline)
            for idx, d in enumerate(all_dates, 1):
                chunks.append(self._chunk(
                    chunk_id=f"{src_prefix}_l3_deadline_{idx}",
                    level=3,
                    parent_id=c2_deadline['chunk_id'],
                    chunk_type='detail',
                    subtype='deadline_item',
                    intent_key='deadlines_summary',
                    title=f"Mốc thời gian {idx}",
                    content=d,
                    extra={'date': d}
                ))

        return chunks


class GenericDocumentProcessor:
    """Xử lý document chung (không theo format nhập học)"""

    def __init__(self, content: str, file_name: str):
        self.content = content
        self.file_name = file_name

    def generate_chunks(self, chunk_size: int = 1000, overlap: int = 200) -> List[Dict[str, Any]]:
        chunks = []
        content = self.content
        base_name = Path(self.file_name).stem
        year_search_text = self.file_name + " " + content[:1500]
        year = self._extract_valid_year(year_search_text)
        if year is None:
            year = datetime.now().year

        doc_intent, doc_subtype = self._infer_intent_subtype(content)

        i = 0
        chunk_idx = 0
        step = max(1, chunk_size - overlap)

        while i < len(content):
            end = min(i + chunk_size, len(content))
            chunk_text = content[i:end]
            chunks.append({
                'chunk_id': f"gen_{base_name}_{chunk_idx}",
                'level': 1,
                'parent_id': None,
                'type': 'generic',
                'subtype': doc_subtype,
                'intent_key': doc_intent,
                'topic': doc_intent,
                'year': year,
                'title': f"Tài liệu: {base_name} (Phần {chunk_idx + 1})",
                'content': chunk_text,
                'source': self.file_name,
                'metadata': {
                    'keywords': self._extract_keywords(chunk_text),
                    'level': 1,
                    'parent_id': None,
                    'intent_key': doc_intent,
                    'subtype': doc_subtype,
                    'source': self.file_name,
                    'year': year
                }
            })
            i += step
            chunk_idx += 1
            if i >= len(content) and len(content) > 0 and chunk_idx == 1:
                break

        return chunks

    def _extract_keywords(self, text: str) -> List[str]:
        words = re.findall(r'\w{4,}', text.lower())
        stopwords = {'trong', 'không', 'những', 'chúng', 'người', 'nhưng', 'được', 'của', 'với'}
        keywords = [w for w in words if w not in stopwords]
        unique_keywords = []
        for w in keywords:
            if w not in unique_keywords:
                unique_keywords.append(w)
            if len(unique_keywords) >= 10:
                break
        return unique_keywords

    def _extract_valid_year(self, text: str) -> Optional[int]:
        candidates = re.findall(r'\b(20\d{2})\b', text or '')
        for y in candidates:
            yi = int(y)
            if 2010 <= yi <= 2100:
                return yi
        return None

    def _infer_intent_subtype(self, text: str) -> Tuple[str, str]:
        normalized = _normalize_key(text)
        if (
            'nop hoc phi' in normalized
            or 'thanh toan' in normalized
            or 'chuyen tien' in normalized
            or 'bidv' in normalized
            or 'ma dinh danh' in normalized
        ):
            return 'fee_payment', 'payment_method'
        if 'hoc phi' in normalized or 'le phi' in normalized:
            return 'fee_info', 'generic_fee'
        return 'general', 'generic_part'

    def _extract_payment_method_lines(self, text: str) -> List[str]:
        lines = []
        for line in (text or '').splitlines():
            l = _normalize_text(line)
            if not l:
                continue
            ln = _normalize_key(l)
            if any(k in ln for k in ['chuyen tien', 'internet banking', 'mobile banking', '24 7', 'bidv', 'nop tien mat', 'tai quay']):
                lines.append(l)
        dedup = []
        for x in lines:
            if x not in dedup:
                dedup.append(x)
        return dedup[:12]

    def _extract_payment_windows(self, text: str) -> List[Dict[str, str]]:
        windows = []
        patterns = [
            r'từ\s+ngày\s*(\d{1,2}/\d{1,2}/\d{4})\s+đến(?:\s+hết)?\s+ngày\s*(\d{1,2}/\d{1,2}/\d{4})',
            r'trước\s*(\d{1,2}\s*giờ\s*\d{0,2})?.*?ngày\s*(\d{1,2}/\d{1,2}/\d{4})'
        ]
        for p in patterns:
            for m in re.finditer(p, text or '', flags=re.IGNORECASE):
                if len(m.groups()) == 2 and '/' in (m.group(1) or ''):
                    windows.append({'deadline_start': m.group(1), 'deadline_end': m.group(2)})
                elif len(m.groups()) == 2:
                    windows.append({'deadline_start': None, 'deadline_end': m.group(2), 'time_slot': _normalize_text(m.group(1) or '')})
        dedup = []
        seen = set()
        for w in windows:
            key = f"{w.get('deadline_start')}::{w.get('deadline_end')}::{w.get('time_slot')}"
            if key in seen:
                continue
            seen.add(key)
            dedup.append(w)
        return dedup

    def _create_payment_chunks(self, base_name: str) -> List[Dict[str, Any]]:
        """Tạo chunk chuyên biệt cho tài liệu hướng dẫn nộp học phí."""
        chunks = []
        text = self.content
        methods = self._extract_payment_method_lines(text)
        windows = self._extract_payment_windows(text)

        overview = {
            'chunk_id': f"pay_{base_name}_overview",
            'level': 1,
            'parent_id': None,
            'type': 'payment',
            'subtype': 'payment_overview',
            'intent_key': 'fee_payment',
            'topic': 'fee_payment',
            'year': self._extract_valid_year(self.file_name + ' ' + text[:1500]) or datetime.now().year,
            'title': f"Hướng dẫn nộp học phí: {base_name}",
            'content': _normalize_text(text[:2200]),
            'source': self.file_name,
            'metadata': {
                'level': 1,
                'parent_id': None,
                'intent_key': 'fee_payment',
                'subtype': 'payment_overview',
                'source': self.file_name,
                'year': self._extract_valid_year(self.file_name + ' ' + text[:1500]) or datetime.now().year,
                'keywords': self._extract_keywords(text[:1200])
            }
        }
        chunks.append(overview)

        if methods:
            chunks.append({
                'chunk_id': f"pay_{base_name}_methods",
                'level': 2,
                'parent_id': overview['chunk_id'],
                'type': 'payment',
                'subtype': 'payment_method',
                'intent_key': 'fee_payment',
                'topic': 'fee_payment',
                'year': overview['year'],
                'title': 'Các kênh/hình thức nộp học phí',
                'content': '\n'.join([f"- {m}" for m in methods]),
                'source': self.file_name,
                'metadata': {
                    'level': 2,
                    'parent_id': overview['chunk_id'],
                    'intent_key': 'fee_payment',
                    'subtype': 'payment_method',
                    'payment_method': True,
                    'source': self.file_name,
                    'year': overview['year']
                }
            })

        for i, w in enumerate(windows, 1):
            start = w.get('deadline_start')
            end = w.get('deadline_end')
            label = f"Khoảng thời gian nộp: {start or '?'} -> {end or '?'}"
            chunks.append({
                'chunk_id': f"pay_{base_name}_window_{i}",
                'level': 2,
                'parent_id': overview['chunk_id'],
                'type': 'payment',
                'subtype': 'payment_window',
                'intent_key': 'fee_payment',
                'topic': 'fee_payment',
                'year': overview['year'],
                'title': 'Mốc thời gian nộp học phí',
                'content': label,
                'source': self.file_name,
                'metadata': {
                    'level': 2,
                    'parent_id': overview['chunk_id'],
                    'intent_key': 'fee_payment',
                    'subtype': 'payment_window',
                    'deadline_start': start,
                    'deadline_end': end,
                    'time_slot': w.get('time_slot'),
                    'source': self.file_name,
                    'year': overview['year']
                }
            })

        return chunks

    def generate_chunks(self, chunk_size: int = 1000, overlap: int = 200) -> List[Dict[str, Any]]:
        # Nếu nhận diện là tài liệu hướng dẫn nộp học phí, tạo chunk chuyên biệt
        doc_intent, _ = self._infer_intent_subtype(self.content)
        base_name = Path(self.file_name).stem
        if doc_intent == 'fee_payment':
            payment_chunks = self._create_payment_chunks(base_name)
            if payment_chunks:
                return payment_chunks

        chunks = []
        content = self.content
        year_search_text = self.file_name + " " + content[:1500]
        year = self._extract_valid_year(year_search_text)
        if year is None:
            year = datetime.now().year

        doc_intent, doc_subtype = self._infer_intent_subtype(content)

        i = 0
        chunk_idx = 0
        step = max(1, chunk_size - overlap)

        while i < len(content):
            end = min(i + chunk_size, len(content))
            chunk_text = content[i:end]
            chunks.append({
                'chunk_id': f"gen_{base_name}_{chunk_idx}",
                'level': 1,
                'parent_id': None,
                'type': 'generic',
                'subtype': doc_subtype,
                'intent_key': doc_intent,
                'topic': doc_intent,
                'year': year,
                'title': f"Tài liệu: {base_name} (Phần {chunk_idx + 1})",
                'content': chunk_text,
                'source': self.file_name,
                'metadata': {
                    'keywords': self._extract_keywords(chunk_text),
                    'level': 1,
                    'parent_id': None,
                    'intent_key': doc_intent,
                    'subtype': doc_subtype,
                    'source': self.file_name,
                    'year': year
                }
            })
            i += step
            chunk_idx += 1
            if i >= len(content) and len(content) > 0 and chunk_idx == 1:
                break

        return chunks


def _is_enrollment_procedure_doc(file_name: str, content: str) -> bool:
    """Nhận diện tài liệu thủ tục nhập học lõi theo nội dung (không phụ thuộc tên file)."""
    name_norm = _normalize_key(file_name)
    text_norm = _normalize_key((content or '')[:12000])

    has_sections = all(k in text_norm for k in ['phan 1', 'phan 2', 'phan 3', 'phan 4'])
    has_steps = all(k in text_norm for k in ['b1', 'b2', 'b3', 'b4'])
    has_admission_terms = ('nhap hoc' in text_norm and 'trung tuyen' in text_norm)

    if has_sections and has_steps and has_admission_terms:
        return True

    # fallback mềm theo tên + nội dung tối thiểu
    if 'thu tuc nhap hoc' in name_norm and has_admission_terms:
        return True

    return False


def process_all_data(data_dir: str = 'data') -> List[Dict[str, Any]]:
    """Xử lý tất cả các file trong thư mục data"""
    all_chunks = []
    files = []
    for ext in ['*.txt', '*.docx', '*.pdf']:
        files.extend(glob.glob(os.path.join(data_dir, ext)))

    print(f"[DATA] Tìm thấy {len(files)} file tài liệu.")

    for file_path in files:
        file_name = os.path.basename(file_path)
        print(f"[DOCUMENT] Đang xử lý: {file_name}...")

        content = TextExtractor.extract(file_path)
        if not content:
            continue

        if _is_enrollment_procedure_doc(file_name, content):
            print(f"   [MODE] Enrollment hierarchy 4-level (content-based)")
            processor = EnrollmentProcessor(content, file_name)
            chunks = processor.generate_chunks()
            all_chunks.extend(chunks)
        else:
            print(f"   [MODE] Generic/focused chunking")
            processor = GenericDocumentProcessor(content, file_path)
            chunks = processor.generate_chunks()
            all_chunks.extend(chunks)

    return all_chunks


def main():
    """Main pipeline Phase 1"""
    print("=" * 70)
    print("PHASE 1: Universal Document Processing & Chunking (4-level)")
    print("=" * 70)
    print()

    chunks = process_all_data('data')

    print(f"\n[OK] Hoàn thành! Tổng số chunks đã tạo: {len(chunks)}")

    output_file = 'all_chunks.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
    print(f"[SAVE] Đã lưu vào {output_file}")

    stats = {}
    intent_stats = {}
    level_stats = {}
    for c in chunks:
        t = c.get('type', 'unknown')
        stats[t] = stats.get(t, 0) + 1
        i = c.get('intent_key', 'general')
        intent_stats[i] = intent_stats.get(i, 0) + 1
        l = c.get('level', -1)
        level_stats[l] = level_stats.get(l, 0) + 1

    print("\n[STATS] Thống kê loại chunks:")
    for t, count in stats.items():
        print(f"   - {t}: {count}")

    print("\n[STATS] Thống kê intent_key:")
    for t, count in sorted(intent_stats.items(), key=lambda x: x[0]):
        print(f"   - {t}: {count}")

    print("\n[STATS] Thống kê level:")
    for l, count in sorted(level_stats.items(), key=lambda x: x[0]):
        print(f"   - level {l}: {count}")


if __name__ == '__main__':
    main()
