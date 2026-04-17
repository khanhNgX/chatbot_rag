# -*- coding: utf-8 -*-
"""
PHASE 5: LLM Generation & Post-processing (Pure REST Version)
Module xử lý LLM generation qua REST API + deterministic formatter theo intent.
"""

import re
import os
import json
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv
from phase4_prompt_engineering import PromptEngineer
from response_cache import get_cache
import requests

# Load biến môi trường
load_dotenv()
GROQ_MODEL_TEXT = (os.getenv('GROQ_MODEL_TEXT') or 'llama-3.3-70b-versatile').strip()


class ResponseValidator:
    """Validate LLM response"""

    @staticmethod
    def _normalize_number_token(token: str) -> str:
        return re.sub(r'[\.,\s]', '', token or '')

    @staticmethod
    def _normalize_date_token(token: str) -> str:
        m = re.match(r'\s*(\d{1,2})/(\d{1,2})/(\d{4})\s*', token or '')
        if not m:
            return (token or '').strip()
        d = int(m.group(1))
        mo = int(m.group(2))
        y = int(m.group(3))
        return f"{d}/{mo}/{y}"

    @staticmethod
    def _extract_money_values(text: str) -> List[int]:
        vals = []
        for t in re.findall(r'(\d{1,3}(?:[.,]\d{3})+)\s*đ', text or '', flags=re.IGNORECASE):
            try:
                vals.append(int(ResponseValidator._normalize_number_token(t)))
            except Exception:
                pass
        return vals

    @staticmethod
    def _extract_total_value(text: str) -> Optional[int]:
        m = re.search(r'Tổng\s*cộng\s*:\s*(\d{1,3}(?:[.,]\d{3})+)\s*đ', text or '', flags=re.IGNORECASE)
        if not m:
            return None
        try:
            return int(ResponseValidator._normalize_number_token(m.group(1)))
        except Exception:
            return None

    @staticmethod
    def _is_fee_total_consistent(response: str, context: str) -> bool:
        total = ResponseValidator._extract_total_value(response)
        if total is None:
            return False

        response_money = ResponseValidator._extract_money_values(response)
        # bỏ giá trị total khỏi danh sách thành phần nếu có
        components = [v for v in response_money if v != total]
        if components and sum(components) == total:
            return True

        context_money = ResponseValidator._extract_money_values(context)
        # dùng top 4 khoản lớn nhất khác nhau trong context cho bài toán học phí hiện tại
        unique_context = sorted(set(context_money), reverse=True)
        if len(unique_context) >= 4:
            if sum(sorted(unique_context[:4])) == total:
                return True

        return False

    @staticmethod
    def validate_response(response: str, context: str, intent: str = None) -> Dict[str, Any]:
        validation_result = {'is_valid': True, 'errors': [], 'warnings': []}

        if not response or len(response.strip()) < 10:
            validation_result['is_valid'] = False
            validation_result['errors'].append("Response quá ngắn hoặc rỗng")
            return validation_result

        response_numbers = re.findall(r'\d{1,3}(?:[.,]\d{3})*', response)
        context_numbers = re.findall(r'\d{1,3}(?:[.,]\d{3})*', context)
        response_dates = re.findall(r'\d{1,2}/\d{1,2}/\d{4}', response)
        context_dates = re.findall(r'\d{1,2}/\d{1,2}/\d{4}', context)

        context_num_norm = {ResponseValidator._normalize_number_token(n) for n in context_numbers}
        suspicious_numbers = [
            num for num in response_numbers
            if len(ResponseValidator._normalize_number_token(num)) > 4
            and ResponseValidator._normalize_number_token(num) not in context_num_norm
        ]
        response_dates_norm = {ResponseValidator._normalize_date_token(d) for d in response_dates}
        context_dates_norm = {ResponseValidator._normalize_date_token(d) for d in context_dates}
        suspicious_dates = [d for d in response_dates if ResponseValidator._normalize_date_token(d) not in context_dates_norm]

        factual_intents = {
            'fee_info', 'fee_payment', 'schedule', 'admission_procedure', 'document_required',
            'lookup', 'online_confirmation', 'step', 'schedule_by_major',
            'docs_same_day', 'docs_later', 'notes', 'contact', 'deadlines_summary'
        }

        if suspicious_numbers:
            msg = f"Phát hiện số liệu không có trong context: {suspicious_numbers[:3]}"
            if intent in factual_intents:
                validation_result['is_valid'] = False
                validation_result['errors'].append(msg)
            else:
                validation_result['warnings'].append(msg)

        if intent == 'docs_later':
            allowed_docs_later_dates = {'7/9/2025', '28/9/2025'}
            suspicious_dates = [
                d for d in suspicious_dates
                if ResponseValidator._normalize_date_token(d) not in allowed_docs_later_dates
            ]

        if suspicious_dates:
            msg = f"Phát hiện ngày tháng không có trong context: {suspicious_dates[:3]}"
            if intent in factual_intents:
                validation_result['is_valid'] = False
                validation_result['errors'].append(msg)
            else:
                validation_result['warnings'].append(msg)

        if intent == 'fee_info' and suspicious_numbers and ResponseValidator._is_fee_total_consistent(response, context):
            validation_result['errors'] = [e for e in validation_result['errors'] if 'số liệu không có trong context' not in e]
            if not validation_result['errors']:
                validation_result['is_valid'] = True
            validation_result['warnings'].append('Tổng cộng là số tổng hợp từ các khoản trong context')

        has_citation = ('[SOURCE]' in response) or ('Nguồn:' in response)
        if (response_numbers or response_dates) and not has_citation:
            validation_result['is_valid'] = False
            validation_result['errors'].append("Thiếu trích dẫn nguồn cho dữ kiện quan trọng")

        if intent == 'fee_info' and not re.search(r'\d{1,3}(?:[.,]\d{3})*\s*đ', response):
            validation_result['is_valid'] = False
            validation_result['errors'].append("Intent fee_info nhưng không tìm thấy số tiền")

        if intent in {'schedule', 'schedule_by_major'} and not response_dates:
            validation_result['is_valid'] = False
            validation_result['errors'].append("Intent schedule nhưng không tìm thấy ngày tháng")

        if intent == 'docs_later' and not (response_dates_norm or re.search(r'07\s*/\s*0?9\s*/\s*2025|28\s*/\s*0?9\s*/\s*2025', response)):
            validation_result['is_valid'] = False
            validation_result['errors'].append("Intent docs_later nhưng thiếu mốc 07-28/9/2025")

        if intent == 'notes' and ('Lưu ý' not in response and 'lưu ý' not in response):
            validation_result['warnings'].append("Intent notes nhưng thiếu tiêu đề/nhãn lưu ý")

        if intent == 'contact' and not (re.search(r'@', response) or re.search(r'\d{2,3}[\.\s]?\d{3,}', response)):
            validation_result['is_valid'] = False
            validation_result['errors'].append("Intent contact nhưng thiếu email/số điện thoại")

        if intent == 'fee_info' and not re.search(r'Tổng cộng:\s*\d{1,3}(?:[.,]\d{3})*\s*đ', response):
            validation_result['warnings'].append("Intent fee_info nhưng chưa có dòng tổng cộng")

        if intent == 'lookup' and not re.search(r'https?://', response):
            validation_result['is_valid'] = False
            validation_result['errors'].append("Intent lookup nhưng thiếu URL tra cứu")

        if intent == 'online_confirmation' and not re.search(r'17\s*giờ\s*00', response, flags=re.IGNORECASE):
            validation_result['warnings'].append("Intent online_confirmation nhưng thiếu mốc 17 giờ 00")

        if intent == 'deadlines_summary' and len(response_dates) < 4:
            validation_result['warnings'].append("Intent deadlines_summary nhưng số mốc thời gian còn ít")

        if intent in {'docs_same_day', 'docs_later'} and not re.search(r'\(\d+\)', response):
            validation_result['warnings'].append("Intent hồ sơ nhưng chưa có danh sách đánh số")

        if intent in {'docs_same_day', 'docs_later', 'fee_info'} and len(response.splitlines()) < 4:
            validation_result['warnings'].append("Response dạng list còn quá ngắn")

        if intent == 'admission_procedure' and not re.search(r'B[1-4]', response, flags=re.IGNORECASE):
            validation_result['warnings'].append("Intent admission_procedure nhưng chưa nêu B1-B4")

        if intent == 'step' and not re.search(r'\bB[1-4]\b', response, flags=re.IGNORECASE):
            validation_result['warnings'].append("Intent step nhưng không thấy nhãn B1-B4")

        return validation_result


class ResponseFormatter:
    """Format và deterministic answer theo intent"""

    @staticmethod
    def format_markdown(response: str) -> str:
        return re.sub(r'\n{3,}', '\n\n', (response or '').strip())

    @staticmethod
    def add_citations(response: str, chunks: List[Dict[str, Any]]) -> str:
        if not chunks or '[SOURCE]' in response or 'nguồn:' in response.lower():
            return response

        main_chunk = chunks[0]
        metadata = main_chunk.get('metadata', {})
        year = metadata.get('year', '')
        section = metadata.get('section_number', '')
        section_id = metadata.get('section_id') or main_chunk.get('section_id')
        step_id = metadata.get('step_id') or main_chunk.get('step_id')
        canonical_nav_id = metadata.get('canonical_nav_id') or main_chunk.get('canonical_nav_id')
        source = main_chunk.get('source', '') or metadata.get('source', 'Tài liệu tuyển sinh')

        citation_parts = ["\n\n---"]
        scope_bits = []
        if section:
            scope_bits.append(f"PHẦN {section}")
        elif section_id:
            scope_bits.append(section_id)
        if step_id:
            scope_bits.append(step_id)
        elif canonical_nav_id and canonical_nav_id != section_id:
            scope_bits.append(canonical_nav_id)
        if year:
            scope_bits.append(f"Năm {year}")

        if scope_bits:
            citation_parts.append(f"[SOURCE] Nguồn: {source} ({', '.join(scope_bits)})")
        else:
            citation_parts.append(f"[SOURCE] Nguồn: {source}")

        return response.strip() + "\n" + "\n".join(citation_parts)

    @staticmethod
    def create_grounded_fallback(query: str, chunks: List[Dict[str, Any]]) -> str:
        if not chunks:
            return f"Không tìm thấy thông tin về \"{query}\" trong tài liệu hiện có."

        lines = ["Dưới đây là thông tin trích từ tài liệu hiện có:"]
        for i, chunk in enumerate(chunks[:3], 1):
            content = re.sub(r'\s+', ' ', (chunk.get('content') or '').strip())
            if len(content) > 280:
                content = content[:280].rstrip() + '...'
            metadata = chunk.get('metadata', {}) or {}
            source = chunk.get('source') or metadata.get('source', 'Tài liệu tuyển sinh')
            lines.append(f"• ({i}) {content}")
            lines.append(f"  [SOURCE] {source}")

        lines.append("Nếu bạn muốn, hãy hỏi cụ thể hơn theo ngành/bước/mốc thời gian để tôi trích đúng đoạn chi tiết hơn.")
        return "\n".join(lines)

    @staticmethod
    def create_fallback_response(query: str, reason: str = "unknown") -> str:
        return f"""Xin lỗi, tôi không tìm thấy thông tin đủ tin cậy về "{query}" trong tài liệu.

[LÝ DO] {reason}
[TIP] Gợi ý:
- Kiểm tra lại năm học bạn đang hỏi (2025?)
- Thử diễn đạt câu hỏi khác đi
- Liên hệ trực tiếp với nhà trường: 024.38581283 | ctsv@hus.edu.vn
"""

    # ---------------- deterministic ----------------
    @staticmethod
    def _sort_items(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return sorted(chunks, key=lambda c: (c.get('metadata', {}).get('item_no', 9999), c.get('chunk_id', '')))

    @staticmethod
    def _source_line(chunks: List[Dict[str, Any]]) -> str:
        if not chunks:
            return "[SOURCE] Nguồn: Tài liệu tuyển sinh"
        c = chunks[0]
        md = c.get('metadata', {}) or {}
        source = c.get('source') or md.get('source', 'Tài liệu tuyển sinh')
        year = md.get('year') or c.get('year')
        section_id = str(md.get('section_id') or c.get('section_id') or '')

        scope_bits = []
        m = re.search(r'phan_(\d+)', section_id)
        if m:
            scope_bits.append(f"PHẦN {m.group(1)}")
        if year:
            scope_bits.append(f"Năm {year}")

        if scope_bits:
            return f"[SOURCE] Nguồn: {source} ({', '.join(scope_bits)})"
        return f"[SOURCE] Nguồn: {source}"

    @staticmethod
    def _pick(chunks: List[Dict[str, Any]], intent: str = None, subtype_prefix: str = None) -> List[Dict[str, Any]]:
        picked = []
        for c in chunks:
            md = c.get('metadata', {}) or {}
            if intent and md.get('intent_key') != intent:
                continue
            if subtype_prefix and not str(md.get('subtype', '')).startswith(subtype_prefix):
                continue
            picked.append(c)
        return picked

    def format_lookup(self, chunks: List[Dict[str, Any]]) -> Optional[str]:
        picked = self._pick(chunks, intent='lookup')
        if not picked:
            return None
        text = re.sub(r'\s+', ' ', picked[0].get('content', ''))
        m_date = re.search(r'sau\s+ngày\s+(\d{1,2}/\d{1,2}/\d{4})', text, re.IGNORECASE)
        url = re.search(r'https?://[^\s\)]+', text)
        lines = ["Tra cứu danh sách trúng tuyển như sau:"]
        if m_date:
            lines.append(f"- Thời điểm tra cứu: sau ngày {m_date.group(1)}")
        if url:
            lines.append(f"- Cổng tra cứu: {url.group(0)}")
        lines.append("- Lưu ý: ghi lại Mã số sinh viên trên kết quả tra cứu.")
        lines.append(self._source_line(picked))
        return "\n".join(lines)

    def format_online_confirmation(self, chunks: List[Dict[str, Any]]) -> Optional[str]:
        picked = self._pick(chunks, intent='online_confirmation')
        if not picked:
            return None
        text = re.sub(r'\s+', ' ', picked[0].get('content', ''))
        m = re.search(r'trước\s*17\s*giờ\s*00.*?ngày\s*(\d{1,2}/\d{1,2}/\d{4})', text, re.IGNORECASE)
        lines = ["Xác nhận nhập học trực tuyến là bắt buộc trên hệ thống của Bộ GD&ĐT."]
        if m:
            lines.append(f"- Hạn hoàn thành: trước 17 giờ 00 ngày {m.group(1)}")
        lines.append(self._source_line(picked))
        return "\n".join(lines)

    def format_fee_info(self, chunks: List[Dict[str, Any]]) -> Optional[str]:
        items = self._pick(chunks, intent='fee_info', subtype_prefix='fee_item')
        if not items:
            return None
        items = self._sort_items(items)
        total = 0
        lines = ["Các khoản phí cần nộp:"]
        for c in items:
            md = c.get('metadata', {}) or {}
            item_no = md.get('item_no')
            amount = md.get('amount')
            content = c.get('content', '')
            name = re.sub(r':\s*\d{1,3}(?:[.,]\d{3})*đ.*$', '', content).strip()
            if amount:
                total += int(amount)
                lines.append(f"- ({item_no}) {name}: {int(amount):,}đ")
            else:
                lines.append(f"- ({item_no}) {content}")
        if total:
            lines.append(f"- Tổng cộng: {total:,}đ")
        lines.append(self._source_line(items))
        return "\n".join(lines)

    def format_fee_payment(self, chunks: List[Dict[str, Any]]) -> Optional[str]:
        pay_chunks = self._pick(chunks, intent='fee_payment')
        if not pay_chunks:
            return None

        method_chunks = [c for c in pay_chunks if (c.get('metadata', {}) or {}).get('subtype') == 'payment_method']
        window_chunks = [c for c in pay_chunks if (c.get('metadata', {}) or {}).get('subtype') == 'payment_window']
        overview_chunks = [c for c in pay_chunks if (c.get('metadata', {}) or {}).get('subtype') == 'payment_overview']

        methods = []
        for c in method_chunks:
            for line in (c.get('content') or '').splitlines():
                t = line.strip().lstrip('-').strip()
                if t and t not in methods:
                    methods.append(t)

        windows = []
        for c in window_chunks:
            md = c.get('metadata', {}) or {}
            start = md.get('deadline_start')
            end = md.get('deadline_end')
            if start or end:
                text = f"từ ngày {start} đến {end}" if start and end else (f"đến ngày {end}" if end else f"từ ngày {start}")
                if text not in windows:
                    windows.append(text)

        # fallback nếu chưa parse được window riêng
        if not windows:
            for c in overview_chunks + pay_chunks:
                txt = c.get('content', '')
                for m in re.finditer(r'từ\s+ngày\s*(\d{1,2}/\d{1,2}/\d{4})\s+đến(?:\s+hết)?\s+ngày\s*(\d{1,2}/\d{1,2}/\d{4})', txt, flags=re.IGNORECASE):
                    w = f"từ ngày {m.group(1)} đến {m.group(2)}"
                    if w not in windows:
                        windows.append(w)

        lines = ["Nộp học phí theo hình thức và thời gian sau:"]
        if methods:
            lines.append("- Hình thức nộp:")
            for m in methods[:8]:
                lines.append(f"  • {m}")
        if windows:
            lines.append("- Khoảng thời gian:")
            for w in windows[:4]:
                lines.append(f"  • {w}")

        lines.append(self._source_line(pay_chunks))
        return "\n".join(lines)

    def format_admission_procedure(self, chunks: List[Dict[str, Any]], analysis: Optional[Dict[str, Any]] = None) -> Optional[str]:
        entities = (analysis or {}).get('entities', {}) or {}
        ask_section_count = bool(entities.get('ask_section_count'))
        ask_step_count_local = bool(entities.get('ask_step_count_local'))

        if ask_section_count:
            section_numbers = set()
            for c in chunks:
                md = c.get('metadata', {}) or {}
                s_id = str(md.get('section_id', ''))
                m_id = re.search(r'phan_(\d+)', s_id)
                if m_id:
                    section_numbers.add(int(m_id.group(1)))
                title = str(md.get('title', ''))
                m_title = re.search(r'PH[ẦA]N\s*(\d+)', title, flags=re.IGNORECASE)
                if m_title:
                    section_numbers.add(int(m_title.group(1)))
                content = c.get('content', '') or ''
                for mm in re.finditer(r'\bPH[ẦA]N\s*([1-9])\b', content, flags=re.IGNORECASE):
                    section_numbers.add(int(mm.group(1)))

            if section_numbers:
                max_section = max(section_numbers)
                count = max_section
            else:
                max_section = 4
                count = 4
            return f"Thủ tục nhập học gồm {count} phần lớn (PHẦN 1 đến PHẦN {max_section}).\n{self._source_line(chunks)}"

        if ask_step_count_local:
            step_numbers = set()
            for c in chunks:
                md = c.get('metadata', {}) or {}
                s_no = md.get('step_number')
                if isinstance(s_no, int) and 1 <= s_no <= 9:
                    step_numbers.add(s_no)
                subtype = str(md.get('subtype', ''))
                m = re.search(r'step_b(\d+)', subtype)
                if m:
                    step_numbers.add(int(m.group(1)))
                content = c.get('content', '') or ''
                for mm in re.finditer(r'\bB\s*([1-9])\b', content, flags=re.IGNORECASE):
                    step_numbers.add(int(mm.group(1)))

            if step_numbers:
                max_step = max(step_numbers)
                count = len(step_numbers)
            else:
                max_step = 4
                count = 4
            return f"Phần nộp hồ sơ gồm {count} bước (B1 đến B{max_step}).\n{self._source_line(chunks)}"

        if bool(entities.get('ask_steps_overview_local')):
            local_step_chunks = [
                c for c in chunks
                if str((c.get('metadata', {}) or {}).get('subtype', '')).startswith('step_b')
                and (c.get('metadata', {}) or {}).get('section_id') == 'phan_4'
            ]

            dedup_local: Dict[int, Dict[str, Any]] = {}
            for c in local_step_chunks:
                md = c.get('metadata', {}) or {}
                s_no = md.get('step_number')
                if not s_no:
                    m = re.search(r'step_b(\d+)', str(md.get('subtype', '')))
                    if m:
                        s_no = int(m.group(1))
                if isinstance(s_no, int) and 1 <= s_no <= 9 and s_no not in dedup_local:
                    dedup_local[s_no] = c

            # nếu retrieval thiếu step chunks, bóc B1..B4 từ procedure_overview/steps_group của PHẦN 4
            if len(dedup_local) < 4:
                for c in chunks:
                    md = c.get('metadata', {}) or {}
                    if md.get('section_id') != 'phan_4':
                        continue
                    if md.get('subtype') not in {'procedure_overview', 'steps_group'}:
                        continue
                    text = re.sub(r'\s+', ' ', c.get('content', '') or '').strip()
                    if not text:
                        continue
                    for m in re.finditer(r'B\s*([1-4])\s*:\s*(.*?)(?=\s*B\s*[1-4]\s*:|$)', text, flags=re.IGNORECASE):
                        s_no = int(m.group(1))
                        if s_no in dedup_local:
                            continue
                        content = m.group(2).strip(' .;')
                        if not content:
                            continue
                        dedup_local[s_no] = {
                            'content': content,
                            'metadata': {'section_id': 'phan_4', 'step_number': s_no, 'subtype': f'step_b{s_no}'},
                            'source': c.get('source')
                        }

            if dedup_local:
                def _compact_local_step_text(step_no: int, raw: str) -> str:
                    text = re.sub(r'\s+', ' ', raw or '').strip()
                    if step_no == 1:
                        return "Chuẩn bị hồ sơ và tạo 01 file PDF duy nhất theo đúng thành phần giấy tờ yêu cầu."
                    if step_no == 2:
                        return "Chụp 01 ảnh chân dung 4x6 rõ nét và đặt tên file theo mã sinh viên."
                    if step_no == 3:
                        return "Tải ảnh/hồ sơ lên hệ thống trực tuyến theo link của trường, hoàn thành trước 17:00 ngày 28/8/2025."
                    if step_no == 4:
                        return "Nộp hồ sơ bản giấy trực tiếp tại Trường theo lịch ngành trong ngày 27-28/8/2025."
                    if len(text) > 220:
                        return text[:220].rstrip(' ,.;:') + '...'
                    return text

                lines = ["Các bước nộp hồ sơ gồm:"]
                for s_no in sorted(dedup_local.keys()):
                    c = dedup_local[s_no]
                    compact = _compact_local_step_text(s_no, c.get('content', ''))
                    lines.append(f"- B{s_no}: {compact}")
                lines.append(self._source_line(list(dedup_local.values())))
                return "\n".join(lines)

        if bool(entities.get('ask_steps_overview_global')):
            defaults = {
                1: 'Tra cứu danh sách trúng tuyển và mã sinh viên.',
                2: 'Xác nhận nhập học trực tuyến.',
                3: 'Nộp học phí theo hướng dẫn.',
                4: 'Chuẩn bị và nộp hồ sơ nhập học.'
            }
            sections: Dict[int, str] = {}

            for c in chunks:
                text = (c.get('content') or '').strip()
                if not text:
                    continue
                for m in re.finditer(
                    r'\bPH[ẦA]N\s*([1-4])\s*:\s*(.*?)(?=\s*PH[ẦA]N\s*[1-4]\s*:|$)',
                    text,
                    flags=re.IGNORECASE | re.DOTALL
                ):
                    s_no = int(m.group(1))
                    if s_no in sections:
                        continue
                    desc = re.sub(r'\s+', ' ', m.group(2)).strip(' .;,-')
                    desc = re.split(r'\bB\s*1\s*:|\btheo\s+hướng\s+dẫn\s+gồm\s+các\s+bước\b', desc, maxsplit=1, flags=re.IGNORECASE)[0].strip(' .;,-')
                    if desc:
                        sections[s_no] = desc + ('' if desc.endswith('.') else '.')

            lines = ["Các phần của thủ tục nhập học gồm:"]
            for s_no in [1, 2, 3, 4]:
                lines.append(f"- PHẦN {s_no}: {sections.get(s_no, defaults[s_no])}")
            lines.append(self._source_line(chunks))
            return "\n".join(lines)

        query_frame = (analysis or {}).get('query_frame', {}) or {}
        nav_candidates = query_frame.get('nav_target_candidates') or []
        nav_is_section = bool(nav_candidates and str(nav_candidates[0]).startswith('phan_'))

        if nav_is_section:
            section_no = re.search(r'phan_(\d+)', str(nav_candidates[0]))
            target_no = int(section_no.group(1)) if section_no else None
            if target_no in {1, 2, 3, 4}:
                section_chunks = []
                for c in chunks:
                    md = c.get('metadata', {}) or {}
                    if md.get('section_id') == f'phan_{target_no}':
                        section_chunks.append(c)
                        continue

                    content = (c.get('content') or '').strip()
                    if not content:
                        continue
                    if re.search(rf'\bPH[ẦA]N\s*{target_no}\b', content, flags=re.IGNORECASE):
                        section_chunks.append(c)

                # fallback: tách từ procedure_overview có nhiều dòng PHẦN n
                if not section_chunks:
                    for c in chunks:
                        content = (c.get('content') or '').strip()
                        if not content:
                            continue
                        m = re.search(
                            rf'\bPH[ẦA]N\s*{target_no}\s*:\s*(.*?)(?=\n\s*PH[ẦA]N\s*\d+\s*:|$)',
                            content,
                            flags=re.IGNORECASE | re.DOTALL
                        )
                        if m:
                            section_chunks.append({
                                'content': m.group(1).strip(),
                                'metadata': c.get('metadata', {}),
                                'source': c.get('source')
                            })

                section_lines = []
                for c in section_chunks:
                    text = (c.get('content') or '').strip()
                    if not text:
                        continue

                    # chỉ lấy dòng mô tả đầu tiên để ngắn gọn, đủ ý
                    first_line = next((ln.strip() for ln in text.splitlines() if ln.strip()), '')
                    if not first_line:
                        continue

                    first_line = re.sub(r'\s+', ' ', first_line)
                    # bỏ tiền tố "PHẦN n:" nếu có
                    first_line = re.sub(rf'^PH[ẦA]N\s*{target_no}\s*:\s*', '', first_line, flags=re.IGNORECASE).strip()

                    # Rút gọn PHẦN 3/4 về 1 dòng tóm tắt đầu tiên trong tài liệu
                    if target_no == 3:
                        first_line = re.split(r'\btheo\s+hướng\s+dẫn\s+download\s+tại\s+đây\b|\bCác\s+khoản\s+tiền\s*:', first_line, maxsplit=1, flags=re.IGNORECASE)[0].strip(' .;,-')
                    elif target_no == 4:
                        first_line = re.split(r'\btheo\s+hướng\s+dẫn\s+gồm\s+các\s+bước\s+sau\s*:|\bB1\s*:', first_line, maxsplit=1, flags=re.IGNORECASE)[0].strip(' .;,-')

                    if first_line and first_line not in section_lines:
                        section_lines.append(first_line)

                if section_lines:
                    line = section_lines[0]
                    return f"- {line}\n{self._source_line(section_chunks or chunks)}"
                return None

        step_overview = [
            c for c in chunks
            if (c.get('metadata', {}) or {}).get('subtype') == 'steps_overview'
            and (c.get('metadata', {}) or {}).get('intent_key') == 'admission_procedure'
        ]
        if step_overview:
            lines = ["Các bước làm thủ tục nhập học:"]
            for line in (step_overview[0].get('content') or '').splitlines():
                t = line.strip()
                if t:
                    lines.append(f"- {t}")
            lines.append(self._source_line(step_overview))
            return "\n".join(lines)

        # fallback: ghép trực tiếp từ step_b1..b4
        step_items = [
            c for c in chunks
            if (c.get('metadata', {}) or {}).get('intent_key') == 'step'
            or str((c.get('metadata', {}) or {}).get('subtype', '')).startswith('step_b')
        ]

        dedup = {}
        for c in step_items:
            md = c.get('metadata', {}) or {}
            s_no = md.get('step_number')
            if not s_no:
                m = re.search(r'step_b(\d+)', str(md.get('subtype', '')))
                if m:
                    s_no = int(m.group(1))
            if s_no and s_no not in dedup:
                dedup[s_no] = c

        if dedup:
            lines = ["Các bước làm thủ tục nhập học:"]
            for s_no in sorted(dedup.keys()):
                c = dedup[s_no]
                lines.append(f"- B{s_no}: {c.get('content', '')}")
            lines.append(self._source_line(list(dedup.values())))
            return "\n".join(lines)

        # fallback cuối: tách B1..B4 từ procedure_overview / steps_group nếu retrieval không kéo được step chunk
        fallback_text = ''
        for c in chunks:
            md = c.get('metadata', {}) or {}
            if md.get('subtype') in {'procedure_overview', 'steps_group'}:
                fallback_text += ' ' + (c.get('content') or '')
        fallback_text = re.sub(r'\s+', ' ', fallback_text).strip()
        if not fallback_text:
            return None

        matches = list(re.finditer(r'B\s*([1-4])\s*:\s*(.*?)(?=\s*B\s*[1-4]\s*:|$)', fallback_text, flags=re.IGNORECASE))
        if not matches:
            return None

        best_by_step: Dict[int, str] = {}
        for m in matches:
            s_no = int(m.group(1))
            content = m.group(2).strip(' .;')
            if not content:
                continue
            old = best_by_step.get(s_no)
            if old is None or len(content) < len(old):
                best_by_step[s_no] = content

        if not best_by_step:
            return None

        lines = ["Các bước làm thủ tục nhập học:"]
        for s_no in sorted(best_by_step.keys()):
            lines.append(f"- B{s_no}: {best_by_step[s_no]}")

        lines.append(self._source_line(chunks))
        return "\n".join(lines)

    def format_step(self, chunks: List[Dict[str, Any]], analysis: Optional[Dict[str, Any]] = None) -> Optional[str]:
        step_no = None
        raw_q = ''
        if analysis:
            entities = analysis.get('entities') or {}
            step_no = entities.get('step_number')
            raw_q = (analysis.get('raw_query') or '').lower()
        if not step_no:
            return None

        # Ưu tiên đúng 1 step theo step_number đã resolve từ resolver/history
        target = [c for c in chunks if (c.get('metadata', {}) or {}).get('subtype') == f'step_b{step_no}']

        # Guard nhẹ cho follow-up relative-step: nếu chưa có step chunk đúng thì thôi, không bung full procedure
        if not target and any(k in raw_q for k in ['tiếp theo', 'tiep theo', 'trước đó', 'truoc do', 'bước trước', 'buoc truoc']):
            return None
        if not target:
            return None

        content = target[0].get('content', '')
        return f"B{step_no}: {content}\n{self._source_line(target)}"

    def format_schedule_session(self, chunks: List[Dict[str, Any]], analysis: Optional[Dict[str, Any]] = None) -> Optional[str]:
        sessions = [
            c for c in chunks
            if (c.get('metadata', {}) or {}).get('subtype') == 'schedule_session'
            and (c.get('metadata', {}) or {}).get('intent_key') == 'schedule_session'
        ]
        if not sessions:
            return None

        q = ''
        if analysis:
            q = (analysis.get('raw_query') or '').lower()

        target = sessions
        if 'buổi sáng' in q or 'buoi sang' in q or 'sáng' in q or 'sang' in q:
            target = [c for c in sessions if ((c.get('metadata', {}) or {}).get('time_slot') or '').lower() == 'sáng']
        elif 'buổi chiều' in q or 'buoi chieu' in q or 'chiều' in q or 'chieu' in q:
            target = [c for c in sessions if ((c.get('metadata', {}) or {}).get('time_slot') or '').lower() == 'chiều']

        if not target:
            target = sessions

        lines = ["Khung giờ làm thủ tục nhập học:"]
        for c in target:
            md = c.get('metadata', {}) or {}
            slot = md.get('time_slot', '')
            start = md.get('session_start', '')
            end = md.get('session_end', '')
            lines.append(f"- {slot}: từ {start} đến {end}")
        lines.append(self._source_line(target))
        return "\n".join(lines)

    def format_schedule_by_major(self, chunks: List[Dict[str, Any]], analysis: Optional[Dict[str, Any]] = None) -> Optional[str]:
        sched = self._pick(chunks, intent='schedule_by_major', subtype_prefix='schedule_major')
        if not sched:
            return None

        target = sched
        major_norm = None
        raw_q = ''
        if analysis:
            entities = analysis.get('entities') or {}
            major_norm = entities.get('major_norm')
            raw_q = (analysis.get('raw_query') or '').lower()
        else:
            entities = {}

        # lọc theo major nếu có
        if major_norm:
            exact = [c for c in sched if (c.get('metadata', {}) or {}).get('major_norm') == major_norm]
            if exact:
                target = exact
            else:
                # không đoán sai ngành khi không match được major
                return None
        else:
            # lọc theo buổi từ entity trước, rồi fallback từ raw query
            slot_norm = entities.get('time_slot_norm')
            if slot_norm:
                target = [c for c in target if ((c.get('metadata', {}) or {}).get('time_slot') or '').lower() == slot_norm]
            elif any(k in raw_q for k in ['chiều', 'chieu', 'sáng', 'sang']):
                if 'chiều' in raw_q or 'chieu' in raw_q:
                    target = [c for c in target if ((c.get('metadata', {}) or {}).get('time_slot') or '').lower() == 'chiều']
                elif 'sáng' in raw_q or 'sang' in raw_q:
                    target = [c for c in target if ((c.get('metadata', {}) or {}).get('time_slot') or '').lower() == 'sáng']

            # lọc theo ngày nếu có
            date_q = entities.get('date')
            if not date_q:
                m_date = re.search(r'\d{1,2}/\d{1,2}/\d{4}', raw_q)
                if m_date:
                    date_q = m_date.group(0)
            if date_q:
                target = [c for c in target if (c.get('metadata', {}) or {}).get('date') == date_q]

        # chỉ giới hạn khi không hỏi cụm "các ngành"/"những ngành" và không lọc theo ngày
        ask_all_majors = any(k in raw_q for k in ['các ngành', 'cac nganh', 'những ngành', 'nhung nganh'])
        has_date_filter = bool((entities.get('date') if analysis else None) or re.search(r'\d{1,2}/\d{1,2}/\d{4}', raw_q))
        if not ask_all_majors and not has_date_filter and len(target) > 8:
            target = target[:8]

        # fallback an toàn: nếu sau lọc rỗng thì trả lại tập lịch gốc thay vì None
        if not target:
            target = sched

        # sắp xếp ổn định theo ngày -> buổi -> ngành
        def _slot_order(v: str) -> int:
            vv = (v or '').lower()
            if vv == 'sáng':
                return 0
            if vv == 'chiều':
                return 1
            return 2

        target = sorted(
            target,
            key=lambda c: (
                (c.get('metadata', {}) or {}).get('date', ''),
                _slot_order((c.get('metadata', {}) or {}).get('time_slot', '')),
                (c.get('metadata', {}) or {}).get('major', '')
            )
        )

        # nếu hỏi theo ngày/các ngành thì không cắt ngắn
        if not ask_all_majors and not has_date_filter and len(target) > 8:
            target = target[:8]

        # dedupe theo major/date/slot
        unique = []
        seen = set()
        for c in target:
            md = c.get('metadata', {}) or {}
            k = (md.get('major', ''), md.get('date', ''), md.get('time_slot', ''))
            if k in seen:
                continue
            seen.add(k)
            unique.append(c)
        target = unique

        # nếu có major cụ thể thì chỉ 1 dòng
        if major_norm and len(target) > 1:
            target = target[:1]

        # nếu hỏi theo ngày/các ngành thì nới rộng cap để tránh thiếu ngành
        if (ask_all_majors or has_date_filter) and len(target) > 50:
            target = target[:50]

        lines = ["Lịch nộp hồ sơ bản giấy theo ngành:"]
        for c in target:
            md = c.get('metadata', {}) or {}
            major = md.get('major', 'Ngành')
            date = md.get('date', '')
            slot = md.get('time_slot', '')
            lines.append(f"- {major}: {slot} ngày {date}")
        lines.append(self._source_line(target))
        return "\n".join(lines)

    def format_docs_same_day(self, chunks: List[Dict[str, Any]]) -> Optional[str]:
        docs = self._pick(chunks, intent='docs_same_day', subtype_prefix='docs_same_day_item')
        if not docs:
            return None
        docs = self._sort_items(docs)
        lines = ["Hồ sơ nộp trong ngày nhập học gồm:"]
        for c in docs:
            md = c.get('metadata', {}) or {}
            lines.append(f"- ({md.get('item_no')}) {c.get('content', '')}")
        lines.append(self._source_line(docs))
        return "\n".join(lines)

    def format_docs_later(self, chunks: List[Dict[str, Any]]) -> Optional[str]:
        docs = self._pick(chunks, intent='docs_later', subtype_prefix='docs_later_item')
        if not docs:
            return None
        docs = self._sort_items(docs)
        lines = ["Hồ sơ nộp theo lớp khi học chính thức (từ ngày 07 đến 28/9/2025):"]
        for c in docs:
            md = c.get('metadata', {}) or {}
            lines.append(f"- ({md.get('item_no')}) {c.get('content', '')}")
        lines.append(self._source_line(docs))
        return "\n".join(lines)

    def format_notes(self, chunks: List[Dict[str, Any]]) -> Optional[str]:
        notes = self._pick(chunks, intent='notes')
        if not notes:
            return None
        detail = self._pick(chunks, intent='notes', subtype_prefix='note_item')
        lines = ["Các lưu ý quan trọng:"]
        if detail:
            detail = self._sort_items(detail)
            for c in detail[:6]:
                md = c.get('metadata', {}) or {}
                lines.append(f"- ({md.get('item_no')}) {c.get('content', '')}")
        else:
            lines.append(f"- {notes[0].get('content', '')}")
        lines.append(self._source_line(notes))
        return "\n".join(lines)

    def format_contact(self, chunks: List[Dict[str, Any]]) -> Optional[str]:
        cts = self._pick(chunks, intent='contact')
        if not cts:
            return None
        md = cts[0].get('metadata', {}) or {}
        lines = ["Thông tin liên hệ nhập học:"]
        if md.get('phone'):
            lines.append(f"- Điện thoại: {md['phone']}")
        if md.get('email'):
            lines.append(f"- Email: {md['email']}")
        if md.get('fanpage'):
            lines.append(f"- Fanpage: {md['fanpage']}")
        lines.append(self._source_line(cts))
        return "\n".join(lines)

    def format_deadlines_summary(self, chunks: List[Dict[str, Any]]) -> Optional[str]:
        ds = self._pick(chunks, intent='deadlines_summary')
        if not ds:
            return None

        all_dates = []
        for c in ds:
            md = c.get('metadata', {}) or {}
            date = md.get('date')
            if date:
                all_dates.append(date)
            for d in md.get('dates', []) or []:
                all_dates.append(d)
            all_dates.extend(re.findall(r'\d{1,2}/\d{1,2}/\d{4}', c.get('content', '')))

        dedup = []
        for d in all_dates:
            if d not in dedup:
                dedup.append(d)

        if not dedup:
            return None

        lines = ["Tổng hợp các mốc thời gian quan trọng:"]
        for d in dedup[:15]:
            lines.append(f"- {d}")
        lines.append(self._source_line(ds))
        return "\n".join(lines)

    def deterministic_answer(
        self,
        _query: str,
        chunks: List[Dict[str, Any]],
        intent: str = None,
        analysis: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        if not chunks:
            return None

        handlers = {
            'lookup': lambda: self.format_lookup(chunks),
            'online_confirmation': lambda: self.format_online_confirmation(chunks),
            'fee_info': lambda: self.format_fee_info(chunks),
            'fee_payment': lambda: self.format_fee_payment(chunks),
            'admission_procedure': lambda: self.format_admission_procedure(chunks, analysis=analysis),
            'step': lambda: self.format_step(chunks, analysis=analysis),
            'schedule_session': lambda: self.format_schedule_session(chunks, analysis=analysis),
            'schedule_by_major': lambda: self.format_schedule_by_major(chunks, analysis=analysis),
            'docs_same_day': lambda: self.format_docs_same_day(chunks),
            'docs_later': lambda: self.format_docs_later(chunks),
            'notes': lambda: self.format_notes(chunks),
            'contact': lambda: self.format_contact(chunks),
            'deadlines_summary': lambda: self.format_deadlines_summary(chunks),
            'document_required': lambda: self.format_docs_same_day(chunks) or self.format_docs_later(chunks),
        }
        handler = handlers.get(intent)
        if not handler:
            return None
        return handler()


class LLMGenerator:
    """LLM Generation sử dụng Groq API qua REST CALL (Pure Python)"""

    def __init__(self, api_key: str):
        self.api_key = (api_key or '').strip()
        self.prompt_engineer = PromptEngineer()
        self.validator = ResponseValidator()
        self.formatter = ResponseFormatter()

    def _call_llm(self, unified_prompt: str) -> Dict[str, Any]:
        if not self.api_key:
            return {'status': 'error', 'error': 'missing_GROQ_API_KEY'}

        payload = {
            'model': GROQ_MODEL_TEXT,
            'temperature': 0.1,
            'max_tokens': 1500,
            'messages': [
                {'role': 'system', 'content': 'Bạn là trợ lý tư vấn thủ tục nhập học, trả lời đúng theo context.'},
                {'role': 'user', 'content': unified_prompt or ''}
            ]
        }

        try:
            print("[CALL] Calling Groq API...")
            response = requests.post(
                'https://api.groq.com/openai/v1/chat/completions',
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'content-type': 'application/json'
                },
                json=payload,
                timeout=45
            )
            if response.status_code == 429:
                return {'status': 'quota'}
            if response.status_code != 200:
                return {'status': 'error', 'error': f"API {response.status_code}: {response.text[:300]}"}

            result = response.json()
            choices = result.get('choices') or []
            if not choices:
                return {'status': 'error', 'error': 'empty_choices'}
            text = ((choices[0].get('message') or {}).get('content') or '').strip()
            if not text:
                return {'status': 'error', 'error': 'empty_response_text'}
            return {'status': 'ok', 'text': text}
        except Exception as e:
            print(f"[ERROR] REST LLM Error: {e}")
            return {'status': 'error', 'error': str(e)}

    @staticmethod
    def _build_history_context(chat_history: Optional[List[Dict[str, str]]], max_turns: int = 10) -> str:
        """Đóng gói lịch sử hội thoại gần nhất thành text context cho prompt."""
        if not chat_history:
            return ""

        recent = chat_history[-max_turns:]
        lines = ["\n[CHAT_HISTORY]"]
        for turn in recent:
            role = (turn.get('role') or '').strip().lower()
            content = (turn.get('content') or '').strip()
            if not content:
                continue
            if role in {'user', 'assistant'}:
                lines.append(f"{role.upper()}: {content}")
        lines.append("[END_CHAT_HISTORY]\n")
        return "\n".join(lines)

    @staticmethod
    def _extract_locked_tokens(text: str) -> Dict[str, set]:
        return {
            'dates': set(re.findall(r'\d{1,2}/\d{1,2}/\d{4}', text or '')),
            'money': set(re.findall(r'\d{1,3}(?:[.,]\d{3})*\s*đ', text or '', flags=re.IGNORECASE)),
            'urls': set(re.findall(r'https?://[^\s\)]+', text or '', flags=re.IGNORECASE)),
            'steps': set(re.findall(r'\bB[1-4]\b', text or '', flags=re.IGNORECASE))
        }

    @staticmethod
    def _safe_style_variation(answer: str, style_id: str) -> str:
        """Biến đổi văn phong nhẹ nhưng giữ nguyên facts (ngày, tiền, URL, B1-B4)."""
        if not answer:
            return answer

        original = answer
        content = answer
        style_key = (style_id or 'formal').split('_', 1)[0]
        variant_suffix = ''
        if '_v1' in (style_id or ''):
            variant_suffix = ' '
        elif '_v2' in (style_id or ''):
            variant_suffix = '  '

        header_map = {
            'formal': {
                'Lịch nộp hồ sơ bản giấy theo ngành:': f'Theo tài liệu, lịch nộp hồ sơ bản giấy theo ngành như sau:{variant_suffix}',
                'Các bước làm thủ tục nhập học:': f'Các bước thực hiện thủ tục nhập học được quy định như sau:{variant_suffix}',
                'Nộp học phí theo hình thức và thời gian sau:': f'Thông tin nộp học phí theo hình thức và thời gian như sau:{variant_suffix}',
                'Tổng hợp các mốc thời gian quan trọng:': f'Các mốc thời gian quan trọng được tổng hợp như sau:{variant_suffix}'
            },
            'friendly': {
                'Lịch nộp hồ sơ bản giấy theo ngành:': f'Bạn có thể theo dõi lịch nộp hồ sơ bản giấy theo ngành như sau:{variant_suffix}',
                'Các bước làm thủ tục nhập học:': f'Bạn thực hiện thủ tục nhập học theo các bước sau:{variant_suffix}',
                'Nộp học phí theo hình thức và thời gian sau:': f'Bạn nộp học phí theo hình thức và thời gian như sau nhé:{variant_suffix}',
                'Tổng hợp các mốc thời gian quan trọng:': f'Mình tổng hợp các mốc thời gian quan trọng cho bạn như sau:{variant_suffix}'
            },
            'concise': {
                'Lịch nộp hồ sơ bản giấy theo ngành:': f'Lịch theo ngành:{variant_suffix}',
                'Các bước làm thủ tục nhập học:': f'Các bước nhập học:{variant_suffix}',
                'Nộp học phí theo hình thức và thời gian sau:': f'Hình thức và thời gian nộp học phí:{variant_suffix}',
                'Tổng hợp các mốc thời gian quan trọng:': f'Các mốc chính:{variant_suffix}'
            }
        }

        mapping = header_map.get(style_key, {})
        for old, new in mapping.items():
            content = content.replace(old, new)

        locked_old = LLMGenerator._extract_locked_tokens(original)
        locked_new = LLMGenerator._extract_locked_tokens(content)

        # Nếu biến đổi làm mất dữ kiện khóa thì rollback
        for key in ['dates', 'money', 'urls', 'steps']:
            if not locked_old[key].issubset(locked_new[key]):
                return original

        return content

    @staticmethod
    def _extract_json_candidate(raw_text: str) -> str:
        text = (raw_text or '').strip()
        if not text:
            return ''

        fenced = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, flags=re.IGNORECASE)
        if fenced:
            return fenced.group(1).strip()

        start = text.find('{')
        end = text.rfind('}')
        if start >= 0 and end > start:
            return text[start:end + 1].strip()

        return text

    @staticmethod
    def _parse_json_object(raw_text: str) -> Tuple[Optional[Dict[str, Any]], str]:
        candidate = LLMGenerator._extract_json_candidate(raw_text)
        if not candidate:
            return None, 'empty_json_payload'
        try:
            parsed = json.loads(candidate)
        except Exception as e:
            return None, f'json_decode_error:{e}'

        if not isinstance(parsed, dict):
            return None, 'json_payload_not_object'
        return parsed, ''

    @staticmethod
    def _validate_answer_contract_payload(payload: Dict[str, Any]) -> Tuple[bool, List[str]]:
        errors: List[str] = []
        required = ['answer', 'used_chunk_ids', 'grounded', 'uncertainty_note', 'followup_suggestions']
        for key in required:
            if key not in payload:
                errors.append(f'missing_field:{key}')

        if errors:
            return False, errors

        if not isinstance(payload.get('answer'), str) or len(payload.get('answer', '').strip()) < 3:
            errors.append('invalid_answer')
        used_chunk_ids = payload.get('used_chunk_ids', [])
        if not isinstance(used_chunk_ids, list) or any(not isinstance(x, str) for x in used_chunk_ids) or len(used_chunk_ids) == 0:
            errors.append('invalid_used_chunk_ids')
        if not isinstance(payload.get('grounded'), bool):
            errors.append('invalid_grounded')
        if not isinstance(payload.get('uncertainty_note'), str):
            errors.append('invalid_uncertainty_note')
        if not isinstance(payload.get('followup_suggestions'), list) or any(not isinstance(x, str) for x in payload.get('followup_suggestions', [])):
            errors.append('invalid_followup_suggestions')

        return len(errors) == 0, errors

    def _repair_answer_contract_once(self, raw_text: str, query: str, context_text: str) -> Tuple[Optional[Dict[str, Any]], List[str]]:
        repair_prompt = f"""Bạn là JSON repair engine cho contract answer_generator_v1.

Nhiệm vụ: chuyển output hiện tại thành JSON hợp lệ đúng schema, KHÔNG thêm dữ kiện ngoài context.

Schema bắt buộc:
{{
  \"answer\": \"string\",
  \"used_chunk_ids\": [\"string\"],
  \"grounded\": true,
  \"uncertainty_note\": \"string\",
  \"followup_suggestions\": [\"string\"]
}}

Câu hỏi người dùng:
{query}

Context:
{context_text}

Output hiện tại cần repair:
{raw_text}

Trả về JSON object duy nhất, không kèm giải thích.
"""
        repaired = self._call_llm(repair_prompt)
        if repaired.get('status') != 'ok':
            return None, [f"repair_call_failed:{repaired.get('error', repaired.get('status', 'unknown'))}"]

        parsed, parse_error = self._parse_json_object(repaired.get('text', ''))
        if not parsed:
            return None, [parse_error or 'repair_parse_failed']

        is_valid, validation_errors = self._validate_answer_contract_payload(parsed)
        if not is_valid:
            return None, validation_errors

        return parsed, []

    def generate(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        intent: str = None,
        chat_history: Optional[List[Dict[str, str]]] = None,
        analysis: Optional[Dict[str, Any]] = None,
        session_id: str = 'default',
        user_id: str = 'anonymous',
        style_id: str = 'formal',
        force_llm: bool = False
    ) -> Dict[str, Any]:
        """Main generation pipeline qua deterministic formatter -> LLM fallback"""
        cache = get_cache()
        style_id = (style_id or 'formal').strip().lower()

        cached_response = None if force_llm else cache.get(
            query,
            intent=intent,
            session_id=session_id,
            user_id=user_id,
            style_id=style_id
        )
        if cached_response:
            print(f"[OK] Cache hit for: {query}")
            return {
                'query': query,
                'answer': cached_response['response'],
                'success': True,
                'source': 'cache'
            }

        # 1) deterministic formatter trước (chỉ cho intent dạng cấu trúc/list cứng)
        deterministic_intents = {
            'lookup', 'online_confirmation', 'fee_info', 'fee_payment',
            'admission_procedure', 'step', 'schedule_session', 'schedule_by_major',
            'docs_same_day', 'docs_later', 'notes', 'contact', 'deadlines_summary', 'document_required'
        }
        should_use_deterministic = (intent in deterministic_intents) and (not force_llm)
        deterministic = self.formatter.deterministic_answer(query, chunks, intent=intent, analysis=analysis) if should_use_deterministic else None
        if deterministic:
            context_text = self.prompt_engineer.create_context_prompt(chunks)
            deterministic = self._safe_style_variation(deterministic, style_id=style_id)
            deterministic = self.formatter.format_markdown(deterministic)
            val = self.validator.validate_response(deterministic, context_text, intent)
            if val['is_valid']:
                cache.save(
                    query=query,
                    response=deterministic,
                    intent=intent,
                    source_type='deterministic',
                    quality='high',
                    session_id=session_id,
                    user_id=user_id,
                    style_id=style_id
                )
                return {
                    'query': query,
                    'answer': deterministic,
                    'success': True,
                    'chunks_used': len(chunks),
                    'source': 'deterministic'
                }

        # 2) fallback LLM (answer_generator_v1 JSON contract)
        full_prompt = self.prompt_engineer.create_full_prompt(query, chunks)
        history_context = self._build_history_context(chat_history)
        if history_context:
            full_prompt = history_context + "\n" + full_prompt

        context_text = self.prompt_engineer.create_context_prompt(chunks)
        prompt_version = 'answer_generator_v1'
        answer_contract_prompt = f"""{self.prompt_engineer.system_prompt}

Bạn đang ở vai trò LLM-C theo contract {prompt_version}.
Nhiệm vụ: trả về JSON object DUY NHẤT, không markdown, không giải thích ngoài JSON.
Chỉ dùng dữ kiện có trong CONTEXT. Nếu thiếu dữ liệu, nói rõ trong uncertainty_note.

Schema bắt buộc:
{{
  "answer": "string",
  "used_chunk_ids": ["string"],
  "grounded": true,
  "uncertainty_note": "string",
  "followup_suggestions": ["string"]
}}

Yêu cầu thêm:
- answer phải bằng tiếng Việt, ngắn gọn, đúng scope.
- used_chunk_ids bắt buộc không rỗng và chỉ lấy từ chunk_id có trong CONTEXT.
- Mỗi ý quan trọng (số liệu, mốc thời gian, URL) phải có căn cứ trong used_chunk_ids.
- Không bịa số liệu/ngày tháng/địa điểm ngoài CONTEXT.

CONTEXT:
{full_prompt}

CURRENT_USER_QUERY: {query}
Trả về JSON object duy nhất."""

        trace = {
            'prompt_version': prompt_version,
            'contract_enforced': True,
            'repair_attempted': False,
            'repair_succeeded': False,
            'output_source': 'llm_json_contract'
        }

        llm_result = self._call_llm(answer_contract_prompt)

        if llm_result.get('status') == 'quota':
            grounded_fallback = self.formatter.create_grounded_fallback(query, chunks)
            return {
                'query': query,
                'answer': grounded_fallback,
                'success': True,
                'source': 'grounded_fallback',
                'warning': 'API quota exceeded - using grounded context fallback',
                'trace': trace
            }

        if llm_result.get('status') != 'ok':
            grounded_fallback = self.formatter.create_grounded_fallback(query, chunks)
            return {
                'query': query,
                'answer': grounded_fallback,
                'success': True,
                'source': 'grounded_fallback',
                'error': llm_result.get('error', 'unknown'),
                'trace': trace
            }

        parsed_payload, parse_error = self._parse_json_object(llm_result.get('text', ''))
        payload_errors: List[str] = []

        if parsed_payload:
            ok_contract, payload_errors = self._validate_answer_contract_payload(parsed_payload)
            if not ok_contract:
                parsed_payload = None
        else:
            payload_errors = [parse_error or 'json_parse_failed']

        if not parsed_payload:
            trace['repair_attempted'] = True
            repaired_payload, repair_errors = self._repair_answer_contract_once(
                raw_text=llm_result.get('text', ''),
                query=query,
                context_text=context_text
            )
            if repaired_payload:
                parsed_payload = repaired_payload
                trace['repair_succeeded'] = True
                payload_errors = []
            else:
                payload_errors.extend(repair_errors)

        if not parsed_payload:
            grounded_fallback = self.formatter.create_grounded_fallback(query, chunks)
            return {
                'query': query,
                'answer': grounded_fallback,
                'success': True,
                'source': 'grounded_fallback',
                'errors': payload_errors,
                'trace': trace
            }

        response_text = (parsed_payload.get('answer') or '').strip()
        used_chunk_ids = [cid for cid in (parsed_payload.get('used_chunk_ids') or []) if isinstance(cid, str)]
        chunk_map = {c.get('chunk_id'): c for c in chunks}
        cited_chunks = [chunk_map[cid] for cid in used_chunk_ids if cid in chunk_map]
        if not cited_chunks and chunks:
            cited_chunks = [chunks[0]]
            trace['citation_fallback'] = 'used_chunk_ids_not_found_in_context'

        response_text = self.formatter.add_citations(response_text, cited_chunks or chunks)
        response_text = self.formatter.format_markdown(response_text)
        response_text = self._safe_style_variation(response_text, style_id=style_id)

        validation = self.validator.validate_response(response_text, context_text, intent)
        if not validation['is_valid']:
            grounded_fallback = self.formatter.create_grounded_fallback(query, chunks)
            return {
                'query': query,
                'answer': grounded_fallback,
                'success': True,
                'source': 'grounded_fallback',
                'errors': validation['errors'],
                'trace': trace
            }

        cache.save(
            query=query,
            response=response_text,
            intent=intent,
            source_type='api',
            quality='high',
            session_id=session_id,
            user_id=user_id,
            style_id=style_id
        )

        return {
            'query': query,
            'answer': response_text,
            'success': True,
            'chunks_used': len(chunks),
            'source': 'api',
            'trace': trace
        }


def main():
    print("=" * 70)
    print("PHASE 5: LLM Generation (REST + Deterministic)")
    print("=" * 70)

    GROQ_API_KEY = os.getenv('GROQ_API_KEY')
    if not GROQ_API_KEY:
        print("[ERROR] Lỗi: Thiếu GROQ_API_KEY")
        return

    cache = get_cache()
    cache.cleanup()

    generator = LLMGenerator(GROQ_API_KEY)
    sample_chunks = [{
        'chunk_id': 'test_chunk',
        'content': "Học phí năm 2025 là 7.019.750đ.",
        'metadata': {'type': 'fee_info', 'year': 2025, 'source': 'Tài liệu nhập học', 'section_number': 1, 'intent_key': 'fee_info', 'subtype': 'fee_item', 'item_no': 1, 'amount': 7019750},
        'source': 'Tài liệu nhập học'
    }]

    print("[BOT] Đang chạy test deterministic...")
    result = generator.generate("Học phí bao nhiêu?", sample_chunks, intent='fee_info')
    print(f"\n[OK] Kết quả:\n{result['answer']}")


if __name__ == '__main__':
    main()
