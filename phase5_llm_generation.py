# -*- coding: utf-8 -*-
"""
PHASE 5: LLM Generation & Post-processing (Pure REST Version)
Module xử lý LLM generation qua REST API + deterministic formatter theo intent.
"""

import re
import os
import requests
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from phase4_prompt_engineering import PromptEngineer
from response_cache import get_cache

# Load biến môi trường
load_dotenv()


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
        source = main_chunk.get('source', '') or metadata.get('source', 'Tài liệu tuyển sinh')

        citation_parts = ["\n\n---"]
        if section and year:
            citation_parts.append(f"[SOURCE] Nguồn: {source} (PHẦN {section}, Năm {year})")
        elif section:
            citation_parts.append(f"[SOURCE] Nguồn: {source} (PHẦN {section})")
        elif year:
            citation_parts.append(f"[SOURCE] Nguồn: {source} (Năm {year})")
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
        if year:
            return f"[SOURCE] Nguồn: {source} (Năm {year})"
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

    def format_admission_procedure(self, chunks: List[Dict[str, Any]]) -> Optional[str]:
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
        if analysis:
            step_no = ((analysis.get('entities') or {}).get('step_number'))
        if not step_no:
            return None
        target = [c for c in chunks if (c.get('metadata', {}) or {}).get('subtype') == f'step_b{step_no}']
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
            'admission_procedure': lambda: self.format_admission_procedure(chunks),
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
    """LLM Generation sử dụng Gemini API qua REST CALL (Pure Python)"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.prompt_engineer = PromptEngineer()
        self.validator = ResponseValidator()
        self.formatter = ResponseFormatter()

    def _call_llm(self, unified_prompt: str) -> Dict[str, Any]:
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": unified_prompt}]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "topP": 0.9,
                "maxOutputTokens": 1500,
            }
        }

        headers = {"Content-Type": "application/json"}
        url_flash = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-lite:generateContent?key={self.api_key}"
        url_pro = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro-latest:generateContent?key={self.api_key}"

        try:
            print("[CALL] Calling Gemini API (Flash Lite)...")
            response = requests.post(url_flash, headers=headers, json=payload, timeout=30)

            if response.status_code == 429:
                return {'status': 'quota'}

            if response.status_code != 200:
                print(f"[WARNING] Flash failed ({response.status_code}), falling back to Pro...")
                response = requests.post(url_pro, headers=headers, json=payload, timeout=30)

            if response.status_code == 429:
                return {'status': 'quota'}

            if response.status_code != 200:
                print(f"[ERROR] API Error {response.status_code}: {response.text[:200]}")
                return {'status': 'error', 'error': f"API {response.status_code}"}

            result = response.json()
            if 'candidates' in result and result['candidates']:
                text = result['candidates'][0]['content']['parts'][0]['text']
                return {'status': 'ok', 'text': text}

            return {'status': 'error', 'error': 'Không có phản hồi từ Gemini'}
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

    def generate(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        intent: str = None,
        chat_history: Optional[List[Dict[str, str]]] = None,
        analysis: Optional[Dict[str, Any]] = None,
        session_id: str = 'default',
        user_id: str = 'anonymous',
        style_id: str = 'formal'
    ) -> Dict[str, Any]:
        """Main generation pipeline qua deterministic formatter -> LLM fallback"""
        cache = get_cache()
        style_id = (style_id or 'formal').strip().lower()

        cached_response = cache.get(
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

        # 1) deterministic formatter trước
        deterministic = self.formatter.deterministic_answer(query, chunks, intent=intent, analysis=analysis)
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

        # 2) fallback LLM
        full_prompt = self.prompt_engineer.create_full_prompt(query, chunks)
        history_context = self._build_history_context(chat_history)
        if history_context:
            full_prompt = history_context + "\n" + full_prompt

        system_instruction = self.prompt_engineer.system_prompt
        unified_prompt = f"SYSTEM: {system_instruction}\n\nCONTEXT:\n{full_prompt}\n\nTRẢ LỜI CÂU HỎI TRÊN:"
        context_text = self.prompt_engineer.create_context_prompt(chunks)

        llm_result = self._call_llm(unified_prompt)

        if llm_result.get('status') == 'quota':
            grounded_fallback = self.formatter.create_grounded_fallback(query, chunks)
            return {
                'query': query,
                'answer': grounded_fallback,
                'success': True,
                'source': 'grounded_fallback',
                'warning': 'API quota exceeded - using grounded context fallback'
            }

        if llm_result.get('status') != 'ok':
            grounded_fallback = self.formatter.create_grounded_fallback(query, chunks)
            return {
                'query': query,
                'answer': grounded_fallback,
                'success': True,
                'source': 'grounded_fallback',
                'error': llm_result.get('error', 'unknown')
            }

        response_text = llm_result['text']

        validation = self.validator.validate_response(response_text, context_text, intent)
        if not validation['is_valid']:
            stricter_prompt = unified_prompt + "\n\n[STRICT MODE] Chỉ được trả lời bằng dữ kiện có trong CONTEXT. Mọi dữ kiện quan trọng phải kèm [SOURCE]. Nếu thiếu dữ kiện, ghi: 'Không tìm thấy trong tài liệu hiện có'."
            retry = self._call_llm(stricter_prompt)
            if retry.get('status') == 'ok':
                response_text = retry['text']
                validation = self.validator.validate_response(response_text, context_text, intent)

        if not validation['is_valid']:
            grounded_fallback = self.formatter.create_grounded_fallback(query, chunks)
            return {
                'query': query,
                'answer': grounded_fallback,
                'success': True,
                'source': 'grounded_fallback',
                'errors': validation['errors']
            }

        final_answer = self.formatter.format_markdown(
            self.formatter.add_citations(response_text, chunks)
        )
        final_answer = self._safe_style_variation(final_answer, style_id=style_id)

        final_validation = self.validator.validate_response(final_answer, context_text, intent)
        if not final_validation['is_valid']:
            safe_fallback = self.formatter.create_fallback_response(query, reason='post_format_validation_failed')
            return {
                'query': query,
                'answer': safe_fallback,
                'success': True,
                'source': 'fallback',
                'errors': final_validation['errors']
            }

        cache.save(
            query=query,
            response=final_answer,
            intent=intent,
            source_type='api',
            quality='high',
            session_id=session_id,
            user_id=user_id,
            style_id=style_id
        )

        return {
            'query': query,
            'answer': final_answer,
            'success': True,
            'chunks_used': len(chunks),
            'source': 'api'
        }


def main():
    print("=" * 70)
    print("PHASE 5: LLM Generation (REST + Deterministic)")
    print("=" * 70)

    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    if not GEMINI_API_KEY:
        print("[ERROR] Lỗi: Thiếu GEMINI_API_KEY")
        return

    cache = get_cache()
    cache.cleanup()

    generator = LLMGenerator(GEMINI_API_KEY)
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
