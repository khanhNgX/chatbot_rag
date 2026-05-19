# -*- coding: utf-8 -*-
"""
AUTOMATION RETRIEVER
Retriever theo intent/entity để giảm nhiễu và bám sát chunk hierarchy.
"""

import re
import unicodedata
from typing import List, Dict, Any, Set, Optional
from automation_ai_rag import AIAutomation
from phase2_embedding import EmbeddingGenerator, VectorStorage


class AutomationRetriever:
    def __init__(self):
        self.ai = AIAutomation()
        self.embedding_gen = EmbeddingGenerator()
        self.vector_db = VectorStorage()
        # Tương thích app.py
        self.query_analyzer = self

    def analyze(self, query: str, chat_history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """Trả về intent + entities + query_frame để app.py/generator dùng chung."""
        processed = self._safe_ai_process(query)
        refined = processed.get('refined_query', query)
        topic = processed.get('detected_topic', 'general')

        entities_raw = self._extract_entities(query)
        entities_refined = self._extract_entities(refined) if refined else {}
        entities = self._merge_entities(entities_raw, entities_refined, raw_query=query)
        query_frame = self._build_query_frame(query=query, refined_query=refined, entities=entities, chat_history=chat_history)
        intent = self._canonical_intent(
            query=query,
            refined_query=refined,
            ai_topic=topic,
            entities=entities,
            query_frame=query_frame
        )
        entities['intent'] = intent

        return {
            'raw_query': query,
            'refined_query': refined,
            'detected_topic': topic,
            'intent': intent,
            'entities': entities,
            'query_frame': query_frame,
            'reason': query_frame.get('debug_reason') or processed.get('reason', '')
        }

    def retrieve(self, query: str, top_k: int = 10, chat_history: Optional[List[Dict[str, str]]] = None) -> List[Dict[str, Any]]:
        """Retrieve theo intent/entity: analyze -> filter -> search -> rerank -> enrich."""
        print(f"\n[USER QUERY] Gốc: {query}")

        analysis = self.analyze(query, chat_history=chat_history)
        refined_query = analysis.get('refined_query', query)
        intent = analysis.get('intent', 'general')
        entities = analysis.get('entities', {}) or {}
        query_frame = analysis.get('query_frame', {}) or {}

        print(f"[AI REWRITE] Mới: {refined_query}")
        print(f"[INTENT] Canonical: {intent}")
        if query_frame:
            print(f"[FRAME] scope={query_frame.get('scope')} nav_target={query_frame.get('nav_target_candidates', [])} reason={query_frame.get('debug_reason', '')}")

        query_embedding = self.embedding_gen.generate_embedding(refined_query)

        where_filter = self._build_where_filter(intent, entities, query_frame=query_frame)
        if where_filter:
            print(f"[FILTERING] where={where_filter}")

        filtered_results = self.vector_db.query(
            query_embedding=query_embedding,
            n_results=max(top_k * 3, 12),
            where=where_filter
        )

        broad_results = self.vector_db.query(
            query_embedding=query_embedding,
            n_results=max(top_k * 3, 12),
            where=None
        )

        filtered_chunks = self._format_results(filtered_results)
        broad_chunks = self._format_results(broad_results)

        # Ưu tiên chunks đúng năm tuyển sinh
        from config import get_admission_year
        target_year = get_admission_year()
        filtered_chunks = self._prefer_year(filtered_chunks, target_year)
        broad_chunks = self._prefer_year(broad_chunks, target_year)

        filtered_score = self._aggregate_quality(query, refined_query, filtered_chunks, intent, entities)
        broad_score = self._aggregate_quality(query, refined_query, broad_chunks, intent, entities)

        nav_target_type = (query_frame or {}).get('nav_target_type')
        strict_nav = nav_target_type in {'section', 'local_step'} and bool(where_filter)

        use_broad = (not filtered_chunks) or (broad_score > filtered_score + 0.10)
        if strict_nav and filtered_chunks:
            use_broad = False

        best_chunks = broad_chunks if use_broad else filtered_chunks
        if use_broad and where_filter:
            print("[FALLBACK] Dùng toàn văn do chất lượng cao hơn filtered")
        elif strict_nav and filtered_chunks:
            print("[FILTER LOCK] Giữ filtered theo nav_target để tránh lệch trục ngữ nghĩa")

        reranked = self._rerank_chunks(query, refined_query, best_chunks, intent, entities, query_frame=query_frame)
        enriched = self._enrich_with_hierarchy(reranked, intent=intent)
        final_chunks = self._dedupe_and_cap_context(enriched, top_k=top_k, intent=intent)

        if intent == 'admission_procedure' and entities.get('ask_steps_overview_global'):
            have_sections = {
                str((c.get('metadata', {}) or {}).get('section_id', ''))
                for c in final_chunks
                if (c.get('metadata', {}) or {}).get('section_id')
            }
            seen_ids = {c.get('chunk_id') for c in final_chunks}

            for sid in ['phan_1', 'phan_2', 'phan_3', 'phan_4']:
                if sid in have_sections:
                    continue
                candidate = None
                for c in broad_chunks:
                    md = c.get('metadata', {}) or {}
                    if md.get('section_id') == sid and md.get('intent_key') in {'admission_procedure', 'step'}:
                        candidate = c
                        break
                if candidate and candidate.get('chunk_id') not in seen_ids:
                    final_chunks.append(candidate)
                    seen_ids.add(candidate.get('chunk_id'))
                    have_sections.add(sid)

            final_chunks = self._dedupe_and_cap_context(enriched + final_chunks, top_k=max(top_k, 12), intent=intent)

        # Đảm bảo tất cả nav_candidates đều có ít nhất 1 chunk trong kết quả
        nav_targets = query_frame.get('nav_target_candidates') or []
        if len(nav_targets) > 1:
            seen_ids = {c.get('chunk_id') for c in final_chunks}
            have_navs = set()
            for c in final_chunks:
                md = c.get('metadata', {}) or {}
                sid = md.get('section_id') or c.get('section_id', '')
                nav = md.get('canonical_nav_id') or c.get('canonical_nav_id', '')
                if sid in nav_targets:
                    have_navs.add(sid)
                if nav in nav_targets:
                    have_navs.add(nav)

            extra = []
            for target in nav_targets:
                if target in have_navs:
                    continue
                for c in broad_chunks:
                    md = c.get('metadata', {}) or {}
                    sid = md.get('section_id') or c.get('section_id', '')
                    nav = md.get('canonical_nav_id') or c.get('canonical_nav_id', '')
                    if (sid == target or nav == target) and c.get('chunk_id') not in seen_ids:
                        extra.append(c)
                        seen_ids.add(c.get('chunk_id'))
                        have_navs.add(target)
                        break

            if extra:
                final_chunks = self._dedupe_and_cap_context(
                    extra + final_chunks, top_k=max(top_k, len(nav_targets) * 3), intent=intent
                )

        return final_chunks

    # --------------------------- Analyze helpers ---------------------------
    def _safe_ai_process(self, query: str) -> Dict[str, Any]:
        try:
            return self.ai.process_user_query(query) or {'refined_query': query, 'detected_topic': 'general'}
        except Exception:
            return {'refined_query': query, 'detected_topic': 'general'}

    def _normalize(self, text: str) -> str:
        text = unicodedata.normalize('NFKC', text or '')
        text = text.lower().strip()
        text = ''.join(ch for ch in unicodedata.normalize('NFD', text) if unicodedata.category(ch) != 'Mn')
        # chuẩn hóa ký tự tiếng Việt đặc thù
        text = text.replace('đ', 'd')
        text = re.sub(r'[^a-z0-9\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _merge_entities(self, entities_raw: Dict[str, Any], entities_refined: Dict[str, Any], raw_query: str) -> Dict[str, Any]:
        """Merge entities từ raw + refined. Ưu tiên tín hiệu explicit từ raw, dùng refined để sửa typo."""
        merged: Dict[str, Any] = dict(entities_refined or {})
        raw = entities_raw or {}

        # 1) explicit numeric/nav từ raw luôn ưu tiên
        for k in ['step_number', 'section_number', 'section_id']:
            if k in raw:
                merged[k] = raw[k]

        # 2) cờ followup/scope: chỉ bật thêm, không tắt
        for k in ['next_step', 'prev_step', 'relative_followup', 'local_step_scope', 'global_section_nav', 'fee_step_scope']:
            if raw.get(k):
                merged[k] = raw[k]

        # 3) overview/count flags: nếu raw không bắt được vì typo, cho phép lấy từ refined
        for k in ['ask_steps_overview_local', 'ask_steps_overview_global', 'ask_step_count_local', 'ask_section_count', 'ask_step_count']:
            if raw.get(k):
                merged[k] = raw[k]

        # 4) major/date/time slot: ưu tiên raw khi có
        for k in ['major_norm', 'date', 'time_slot_norm']:
            if raw.get(k):
                merged[k] = raw[k]

        # 5) Nếu raw rõ local (hồ sơ/PHẦN4) thì không cho global overview ghi đè
        qn = self._normalize(raw_query)
        raw_local_cue = any(k in qn for k in ['ho so', 'nop ho so', 'phan 4'])
        if raw_local_cue and merged.get('ask_steps_overview_global') and not merged.get('ask_steps_overview_local'):
            merged.pop('ask_steps_overview_global', None)
            merged['ask_steps_overview_local'] = True
            merged['local_step_scope'] = True
            merged['section_id'] = 'phan_4'
            merged['section_number'] = 4

        # 6) vệ sinh xung đột
        if merged.get('ask_steps_overview_local'):
            merged.pop('step_number', None)
            merged.pop('section_number', None)
        if merged.get('ask_steps_overview_global'):
            merged.pop('section_number', None)
            merged.pop('section_id', None)

        # local step rõ ràng trong PHẦN 4 vẫn giữ section_id để formatter/retriever biết trục hồ sơ.
        if merged.get('step_number') and merged.get('local_step_scope'):
            if raw.get('section_id') == 'phan_4' or merged.get('fee_step_scope'):
                merged['section_id'] = 'phan_4'
            elif merged.get('section_id') != 'phan_4':
                merged.pop('section_number', None)
                merged.pop('section_id', None)

        return merged

    def _extract_entities(self, query: str) -> Dict[str, Any]:
        qn = self._normalize(query)
        entities: Dict[str, Any] = {}

        local_step_scope = any(k in qn for k in ['phan 4', 'phần 4', 'ho so', 'hồ sơ', 'hso', 'nop ho so', 'nộp hồ sơ'])
        has_fee_words = any(k in qn for k in ['hoc phi', 'học phí', 'le phi', 'lệ phí', 'nop hoc phi', 'nộp học phí'])
        step_num_pattern = r'\bbuoc(?:\s*(?:thu|so|thu\s*tu))?\s*([1-4])\b'
        step_word_pattern = r'\bbuoc(?:\s*(?:thu|so|thu\s*tu))?\s*(mot|hai|ba|bon|tu)\b'

        # Với câu hỏi theo dạng "bước ... nộp học phí", người dùng đang hỏi quy trình thao tác (B1-B4)
        # nên map về local step flow của PHẦN 4 thay vì PHẦN 1/2/3 theo trục thủ tục tổng quát.
        if 'buoc' in qn and has_fee_words:
            local_step_scope = True
            entities['section_id'] = 'phan_4'
            entities['section_number'] = 4
            entities['fee_step_scope'] = True

        if any(k in qn for k in ['buoc tiep theo', 'bước tiếp theo', 'buoc sau', 'bước sau', 'tiep theo', 'tiếp theo', 'sau do', 'sau đó']):
            entities['next_step'] = True
        if any(k in qn for k in ['buoc truoc', 'bước trước', 'truoc do', 'trước đó']):
            entities['prev_step'] = True
        if entities.get('next_step') and entities.get('prev_step'):
            entities.pop('prev_step', None)

        m_sections = re.findall(r'\bphan\s*([1-4])\b|\bphần\s*([1-4])\b|\bmuc\s*([1-4])\b|\bmục\s*([1-4])\b', qn)
        found_sections = sorted(set(int(g) for groups in m_sections for g in groups if g))
        if found_sections:
            entities['section_number'] = found_sections[0]
            entities['section_id'] = f"phan_{found_sections[0]}"
            if len(found_sections) > 1:
                entities['section_numbers'] = found_sections
            if found_sections[0] == 4 and 'buoc' in qn:
                local_step_scope = True

        m_b_step = re.findall(r'\bb\s*([1-4])\b', qn)
        found_b_steps = sorted(set(int(x) for x in m_b_step))
        if found_b_steps:
            entities['step_number'] = found_b_steps[0]
            if len(found_b_steps) > 1:
                entities['step_numbers'] = found_b_steps
            local_step_scope = True

        if 'step_number' not in entities:
            m_word_steps = re.findall(step_num_pattern, qn)
            if m_word_steps:
                found_nums = [int(g) for g in m_word_steps if g]
                if found_nums:
                    n = found_nums[0]
                    if local_step_scope:
                        entities['step_number'] = n
                        if len(found_nums) > 1:
                            entities['step_numbers'] = sorted(set(found_nums))
                    elif 'section_number' not in entities:
                        entities['section_number'] = n
                        entities['section_id'] = f"phan_{n}"
                        if len(found_nums) > 1:
                            entities['section_numbers'] = sorted(set(found_nums))
        if 'step_number' not in entities and any(k in qn for k in ['buoc dau', 'buoc dau tien', 'bước đầu', 'bước đầu tiên']):
            if local_step_scope:
                entities['step_number'] = 1
            elif 'section_number' not in entities:
                entities['section_number'] = 1
                entities['section_id'] = 'phan_1'

        ask_count = any(k in qn for k in ['may', 'bao nhieu', 'tong'])
        ask_steps = 'buoc' in qn
        ask_sections = 'phan' in qn
        ask_all_steps = any(k in qn for k in ['cac buoc', 'ac buoc', 'nhung buoc', 'toan bo cac buoc', 'tat ca cac buoc'])
        ask_summary = any(k in qn for k in ['tom tat', 'tong quan', 'khai quat', 'tong the'])
        is_global_procedure_phrase = any(k in qn for k in ['thu tuc nhap hoc', 'quy trinh nhap hoc'])

        # câu hỏi tổng quan thủ tục nhập học => trả trục PHẦN 1..4 (không rơi vào B1..B4)
        if (
            ask_summary
            and is_global_procedure_phrase
            and not local_step_scope
            and 'step_number' not in entities
            and 'section_number' not in entities
        ):
            entities['ask_steps_overview_global'] = True
            entities['global_section_nav'] = True

        # map số bước dạng chữ: "bước thứ hai/ba/bốn..."
        if 'step_number' not in entities:
            m_word_step_text = re.search(step_word_pattern, qn)
            if m_word_step_text:
                w = m_word_step_text.group(1)
                n = {'mot': 1, 'hai': 2, 'ba': 3, 'bon': 4, 'tu': 4}.get(w)
                if n:
                    if local_step_scope:
                        entities['step_number'] = n
                        entities['section_id'] = 'phan_4'
                    elif 'section_number' not in entities:
                        entities['section_number'] = n
                        entities['section_id'] = f"phan_{n}"

        # "phần 3 của phần nộp hồ sơ" => local step B3 (không phải PHẦN 3 global)
        if (
            local_step_scope
            and 'step_number' not in entities
            and isinstance(entities.get('section_number'), int)
            and entities.get('section_number') in {1, 2, 3, 4}
            and re.search(r'\bphan\s*[1-4]\s*(cua|trong)\s*(phan\s*)?(nop\s*)?ho\s*so\b', qn)
        ):
            entities['step_number'] = int(entities['section_number'])
            entities.pop('section_number', None)
            entities.pop('section_id', None)

        if local_step_scope and ask_all_steps and 'step_number' not in entities:
            entities['ask_steps_overview_local'] = True
            entities['section_id'] = 'phan_4'
            entities['section_number'] = 4

        if (not local_step_scope) and ask_all_steps and 'section_number' not in entities:
            entities['ask_steps_overview_global'] = True

        if entities.get('ask_steps_overview_local'):
            entities.pop('step_number', None)
            entities.pop('section_number', None)
        if entities.get('ask_steps_overview_global'):
            entities.pop('section_number', None)
            entities.pop('section_id', None)

        ask_steps = 'buoc' in qn
        ask_sections = 'phan' in qn
        ask_count = any(k in qn for k in ['may', 'bao nhieu', 'tong'])

        if ask_count and (ask_steps or ask_sections) and 'step_number' not in entities:
            if local_step_scope and ask_steps:
                entities['ask_step_count_local'] = True
            else:
                entities['ask_section_count'] = True

        if entities.get('ask_step_count_local'):
            entities['ask_step_count'] = True

        if (
            ('buoc' in qn or re.search(r'\bb\s*$', qn))
            and not entities.get('next_step')
            and not entities.get('prev_step')
            and not ask_count
            and not entities.get('ask_steps_overview_local')
            and not entities.get('ask_steps_overview_global')
            and 'step_number' not in entities
            and 'section_number' not in entities
        ):
            if local_step_scope:
                entities['step_number'] = 1
            else:
                entities['section_number'] = 1
                entities['section_id'] = 'phan_1'

        if local_step_scope:
            entities['local_step_scope'] = True
        elif ('thu tuc' in qn or 'quy trinh' in qn) and 'buoc' in qn:
            entities['global_section_nav'] = True

        if entities.get('next_step') or entities.get('prev_step'):
            entities['relative_followup'] = True

        known_majors = [
            'toan hoc', 'toan tin', 'khoa hoc may tinh va thong tin', 'khoa hoc du lieu',
            'hoa hoc', 'cong nghe ky thuat hoa hoc', 'hoa duoc',
            'vat ly hoc', 'khoa hoc vat lieu', 'cong nghe ky thuat hat nhan',
            'ky thuat dien tu va tin hoc', 'cong nghe ban dan',
            'sinh hoc', 'cong nghe sinh hoc', 'sinh duoc hoc',
            'dia chat hoc', 'dia ly tu nhien', 'khoa hoc thong tin dia khong gian',
            'quan ly dat dai', 'quan ly phat trien do thi va bat dong san',
            'khoa hoc moi truong', 'cong nghe ki thuat moi truong',
            'khoa hoc va cong nghe thuc pham', 'moi truong suc khoe va an toan',
            'khi tuong va khi hau hoc', 'tai nguyen va moi truong nuoc', 'hai duong hoc'
        ]
        for m in known_majors:
            if m in qn:
                entities['major_norm'] = m
                break

        date_matches = re.findall(r'\b\d{1,2}/\d{1,2}/\d{4}\b', query)
        if date_matches:
            entities['date'] = date_matches[0]

        if any(k in qn for k in ['buoi sang', 'sang']):
            entities['time_slot_norm'] = 'sáng'
        elif any(k in qn for k in ['buoi chieu', 'chieu']):
            entities['time_slot_norm'] = 'chiều'

        return entities

    def _infer_relative_axis_from_history(self, chat_history: Optional[List[Dict[str, str]]]) -> str:
        """Trả về local/global/unknown theo tín hiệu gần nhất trong history."""
        if not chat_history:
            return 'unknown'

        for turn in reversed(chat_history[-8:]):
            raw = turn.get('content', '') or ''
            norm = self._normalize(raw)

            has_section_marker = (
                bool(re.search(r'\bphan\s*[1-4]\b', norm))
                or bool(re.search(r'\[source\].*?\bPH[ẦA]N\s*[1-4]\b', raw, flags=re.IGNORECASE))
            )
            has_local_doc_cue = ('ho so' in norm) or ('nop ho so' in norm)
            has_b_step_strict = bool(re.search(r'\bb\s*[1-4]\s*:', raw, flags=re.IGNORECASE))
            has_b_step_with_local_cue = bool(re.search(r'\bb\s*[1-4]\b', norm)) and has_local_doc_cue

            # Chỉ coi là local khi B-step đủ rõ (B1:...) hoặc có cue hồ sơ đi kèm
            if has_b_step_strict or has_b_step_with_local_cue:
                return 'local'

            # Tránh false-positive từ cụm tổng quát như "B1-B4"
            if bool(re.search(r'\bb\s*[1-4]\b', norm)) and not has_section_marker:
                return 'unknown'

            # Nếu chỉ thấy marker PHẦN n thì giữ global flow
            if has_section_marker:
                return 'global'

            # Không có PHẦN/B-step, nhưng có cue hồ sơ thì ưu tiên local
            if has_local_doc_cue:
                return 'local'

            if 'thu tuc nhap hoc' in norm or 'quy trinh nhap hoc' in norm:
                return 'global'

        return 'unknown'

    def _history_mentions_section4(self, chat_history: Optional[List[Dict[str, str]]]) -> bool:
        if not chat_history:
            return False
        for turn in reversed(chat_history[-6:]):
            text = self._normalize(turn.get('content', ''))
            if 'phan 4' in text:
                return True
            if ('ho so' in text and 'nhap hoc' in text) or ('b1' in text and 'ho so' in text):
                return True
        return False

    def _last_step_from_history(self, chat_history: Optional[List[Dict[str, str]]]) -> Optional[int]:
        if not chat_history:
            return None
        for turn in reversed(chat_history[-6:]):
            text_norm = self._normalize(turn.get('content', '') or '')
            m1 = re.search(r'\bb\s*([1-4])\b', text_norm)
            if m1:
                return int(m1.group(1))
            m2 = re.search(r'\bbuoc\s*([1-4])\b', text_norm)
            if m2:
                return int(m2.group(1))
            if any(k in text_norm for k in ['buoc dau', 'buoc dau tien']):
                return 1
        return None

    def _last_section_from_history(self, chat_history: Optional[List[Dict[str, str]]]) -> Optional[int]:
        if not chat_history:
            return None
        for turn in reversed(chat_history[-6:]):
            raw_text = turn.get('content', '') or ''
            text_norm = self._normalize(raw_text)
            m_sec = re.search(r'\bphan\s*([1-4])\b', text_norm)
            if m_sec:
                return int(m_sec.group(1))
            # bắt thêm các biến thể có dấu ở text gốc
            m_sec2 = re.search(r'\bph[aàầ]n\s*([1-4])\b', raw_text, flags=re.IGNORECASE)
            if m_sec2:
                return int(m_sec2.group(1))
            # parse cả dòng source nếu formatter ghi (PHẦN n, Năm ...)
            m_source = re.search(r'\[SOURCE\].*?\bPH[ẦA]N\s*([1-4])\b', raw_text, flags=re.IGNORECASE)
            if m_source:
                return int(m_source.group(1))
        return None

    def _build_query_frame(
        self,
        query: str,
        refined_query: str,
        entities: Dict[str, Any],
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        q = self._normalize(f"{query} {refined_query}")
        nav_candidates: List[str] = []
        nav_target_type = 'unknown'
        scope = 'global'
        debug_reason = 'fallback_global_rule'

        step_number = entities.get('step_number')
        section_number = entities.get('section_number')
        ask_section_count = bool(entities.get('ask_section_count'))
        ask_step_count_local = bool(entities.get('ask_step_count_local'))
        has_local_pattern = bool(re.search(r'\b(b[1-4])\s*(phan|phần)\s*4\b|\bbuoc\s*[1-4]\s*(cua|trong)\s*(phan|phần)\s*4\b', q))

        if ask_section_count or ask_step_count_local:
            return {
                'rewritten_query': refined_query,
                'language': 'vi',
                'is_followup': bool(chat_history),
                'scope': 'global',
                'task_type': 'ask_navigation',
                'nav_target_type': 'unknown',
                'nav_target_candidates': [],
                'topic_candidates': [],
                'action_candidates': [],
                'time_candidates': [],
                'needs_parent_context': False,
                'should_apply_metadata_filter': True,
                'ambiguity_notes': [],
                'confidence': 0.95,
                'debug_reason': 'ask_section_or_local_step_count'
            }
        # Relative follow-up resolution: ưu tiên trục ngữ cảnh gần nhất (local/global)
        if entities.get('next_step') or entities.get('prev_step'):
            axis = 'local' if entities.get('local_step_scope') else 'global'
            if axis != 'local' and not entities.get('global_section_nav') and not entities.get('section_number'):
                axis = self._infer_relative_axis_from_history(chat_history)
                if axis == 'unknown':
                    axis = 'global'

            if axis == 'local':
                entities['local_step_scope'] = True
                entities.pop('global_section_nav', None)
                last_step = self._last_step_from_history(chat_history)
                if last_step in {1, 2, 3, 4}:
                    if entities.get('next_step'):
                        step_number = min(4, last_step + 1)
                        entities['step_number'] = step_number
                        entities['resolved_from_relative'] = 'next_step'
                    elif entities.get('prev_step'):
                        step_number = max(1, last_step - 1)
                        entities['step_number'] = step_number
                        entities['resolved_from_relative'] = 'prev_step'
                    debug_reason = f"relative_local_step_from_history_b{last_step}"
                else:
                    if entities.get('next_step'):
                        step_number = 2
                        entities['step_number'] = 2
                        entities['resolved_from_relative'] = 'next_step_default'
                    elif entities.get('prev_step'):
                        step_number = 1
                        entities['step_number'] = 1
                        entities['resolved_from_relative'] = 'prev_step_default'
                    debug_reason = 'relative_local_step_no_history_default'
            else:
                last_section = self._last_section_from_history(chat_history)
                if last_section in {1, 2, 3, 4}:
                    if entities.get('next_step'):
                        section_number = min(4, last_section + 1)
                        entities['section_number'] = section_number
                        entities['section_id'] = f"phan_{section_number}"
                        entities['resolved_from_relative'] = 'next_section'
                    elif entities.get('prev_step'):
                        section_number = max(1, last_section - 1)
                        entities['section_number'] = section_number
                        entities['section_id'] = f"phan_{section_number}"
                        entities['resolved_from_relative'] = 'prev_section'
                    debug_reason = f"relative_section_from_history_phan_{last_section}"
                elif section_number in {1, 2, 3, 4}:
                    debug_reason = f"explicit_section_phan_{section_number}"
                else:
                    if entities.get('next_step'):
                        section_number = 2
                        entities['section_number'] = 2
                        entities['section_id'] = 'phan_2'
                        debug_reason = 'relative_section_no_history_default_phan_2'
                    elif entities.get('prev_step'):
                        section_number = 1
                        entities['section_number'] = 1
                        entities['section_id'] = 'phan_1'
                        debug_reason = 'relative_section_no_history_default_phan_1'
                    else:
                        section_number = 1
                        entities['section_number'] = 1
                        entities['section_id'] = 'phan_1'
                        debug_reason = 'relative_section_no_history_default_phan_1'

            entities['resolved_axis'] = axis

        # giữ đồng bộ biến local
        section_number = entities.get('section_number', section_number)
        step_number = entities.get('step_number', step_number)

        # overview local: không lock nav theo section/local-step để formatter trả full B1-B4
        if entities.get('ask_steps_overview_local'):
            entities.pop('step_number', None)
            nav_target_type = 'unknown'
            nav_candidates = []
            scope = 'local_section'
            debug_reason = 'ask_steps_overview_local'
        else:
            # nếu global_section_nav mà chưa có section thì mặc định phần 1
            if entities.get('global_section_nav') and section_number not in {1, 2, 3, 4}:
                section_number = 1
                entities['section_number'] = 1
                entities['section_id'] = 'phan_1'
                debug_reason = 'global_section_nav_default_phan_1'

            # Local mention khi có scope local hoặc đã resolve step local
            has_local_scope = bool(entities.get('local_step_scope')) or has_local_pattern

            if has_local_scope and step_number in {1, 2, 3, 4}:
                nav_target_type = 'local_step'
                step_numbers = entities.get('step_numbers') or [step_number]
                nav_candidates = [f"b{n}_phan_4" for n in step_numbers if n in {1, 2, 3, 4}]
                scope = 'local_section'
                if not debug_reason.startswith('relative_'):
                    debug_reason = 'explicit_local_step_mention'
            elif section_number in {1, 2, 3, 4}:
                nav_target_type = 'section'
                section_numbers = entities.get('section_numbers') or [section_number]
                nav_candidates = [f"phan_{n}" for n in section_numbers if n in {1, 2, 3, 4}]
                scope = 'global'
                if not debug_reason.startswith('relative_'):
                    debug_reason = 'explicit_section_mention'
            elif step_number in {1, 2, 3, 4}:
                if self._history_mentions_section4(chat_history):
                    nav_target_type = 'local_step'
                    nav_candidates = [f"b{step_number}_phan_4"]
                    scope = 'followup_from_history'
                    if not debug_reason.startswith('relative_'):
                        debug_reason = 'history_section4_priority'
                else:
                    nav_target_type = 'global_process_step'
                    nav_candidates = [f"phan_{step_number}"]
                    scope = 'ambiguous'
                    if not debug_reason.startswith('relative_'):
                        debug_reason = 'global_vs_local_ambiguous_default_global'

            # overview global: không lock nav theo section để formatter trả full PHẦN
            if entities.get('ask_steps_overview_global'):
                entities.pop('section_number', None)
                entities.pop('section_id', None)
                nav_target_type = 'unknown'
                nav_candidates = []
                scope = 'global'
                if not debug_reason.startswith('relative_'):
                    debug_reason = 'ask_steps_overview_global'


        task_type = 'ask_what'
        if any(k in q for k in ['phan', 'muc', 'buoc', 'b1', 'b2', 'b3', 'b4']):
            task_type = 'ask_navigation'
        elif any(k in q for k in ['khi nao', 'deadline', 'han', 'moc thoi gian']):
            task_type = 'ask_when'
        elif any(k in q for k in ['o dau', 'dia diem']):
            task_type = 'ask_where'
        elif any(k in q for k in ['hoc phi', 'le phi', 'bao nhieu tien', 'chuyen khoan']):
            task_type = 'ask_payment'
        elif any(k in q for k in ['ho so', 'giay to', 'can gi']):
            task_type = 'ask_documents'
        elif any(k in q for k in ['lien he', 'dien thoai', 'email']):
            task_type = 'ask_contact'
        elif any(k in q for k in ['lich', 'nganh', 'sang', 'chieu']):
            task_type = 'ask_schedule'

        return {
            'rewritten_query': refined_query,
            'language': 'vi',
            'is_followup': bool(chat_history),
            'scope': scope,
            'task_type': task_type,
            'nav_target_type': nav_target_type,
            'nav_target_candidates': nav_candidates,
            'topic_candidates': [],
            'action_candidates': [],
            'time_candidates': [],
            'needs_parent_context': nav_target_type in {'local_step', 'section'} or scope in {'followup_from_history', 'ambiguous'},
            'should_apply_metadata_filter': True,
            'ambiguity_notes': ['global/local ambiguity detected'] if scope == 'ambiguous' else [],
            'confidence': 0.6 if scope == 'ambiguous' else 0.9,
            'debug_reason': debug_reason
        }

    def _canonical_intent(
        self,
        query: str,
        refined_query: str,
        ai_topic: str,
        entities: Dict[str, Any],
        query_frame: Optional[Dict[str, Any]] = None
    ) -> str:
        q = self._normalize(f"{query} {refined_query}")
        query_frame = query_frame or {}

        nav_target_type = query_frame.get('nav_target_type')
        nav_candidates = query_frame.get('nav_target_candidates') or []

        if nav_target_type == 'local_step' and nav_candidates:
            return 'step'

        if entities.get('step_number') and entities.get('local_step_scope'):
            return 'step'

        if nav_target_type in {'global_process_step', 'section'} and nav_candidates:
            return 'admission_procedure'
        if entities.get('step_number'):
            if entities.get('local_step_scope'):
                return 'step'
            return 'admission_procedure'
        if entities.get('ask_steps_overview_local'):
            return 'admission_procedure'
        if entities.get('ask_steps_overview_global'):
            return 'admission_procedure'
        if entities.get('section_number'):
            return 'admission_procedure'

        # intent theo keyword cụ thể trước
        if any(k in q for k in ['tra cuu', 'trung tuyen', 'ma so sinh vien', 'mssv']):
            return 'lookup'
        if 'xac nhan nhap hoc truc tuyen' in q or ('xac nhan' in q and 'truc tuyen' in q):
            return 'online_confirmation'
        if (
            any(k in q for k in ['kenh thanh toan', 'chuyen tien', 'bidv', 'ma dinh danh', 'internet banking', 'mobile banking'])
            or ('hoc phi' in q and 'hinh thuc' in q)
            or ('hoc phi' in q and 'khoang ngay' in q)
            or ('hoc phi' in q and 'tu ngay' in q and 'den' in q)
        ):
            return 'fee_payment'
        if any(k in q for k in ['hoc phi', 'le phi', 'khoan tien', 'tam thu', 'bao nhieu tien']):
            return 'fee_info'
        if 'nop trong ngay nhap hoc' in q or ('ho so' in q and 'trong ngay' in q):
            return 'docs_same_day'
        if (
            any(k in q for k in ['nop theo lop', 'nop sau', 'khi hoc chinh thuc'])
            or ('ho so' in q and 'theo lop' in q)
            or ('07' in q and '28' in q and '9' in q)
        ):
            return 'docs_later'
        if any(k in q for k in ['luu y', 'chu y', 'quan trong', 'tan sinh vien']):
            return 'notes'
        if any(k in q for k in ['buoi sang', 'buoi chieu', 'sang may gio', 'chieu may gio', 'khung gio', 'gio bat dau']):
            return 'schedule_session'
        if entities.get('major_norm') or entities.get('date') or entities.get('time_slot_norm') or any(k in q for k in ['nganh', 'lich', 'sang thu', 'chieu thu']):
            return 'schedule_by_major'
        if any(k in q for k in ['lien he', 'dien thoai', 'email', 'fanpage', 'hotline']):
            return 'contact'
        if any(k in q for k in ['tong hop', 'deadline', 'moc thoi gian', 'han cuoi']):
            return 'deadlines_summary'
        if 'khi nao' in q and any(k in q for k in ['nhap hoc', 'nganh', 'buoi', 'sang', 'chieu']):
            return 'schedule_by_major'
        if 'khi nao' in q:
            return 'deadlines_summary'
        if any(k in q for k in ['thu tuc', 'quy trinh', 'cac buoc', 'b1', 'b2', 'b3', 'b4']):
            return 'admission_procedure'

        topic_map = {
            'fee': 'fee_info',
            'admission_docs': 'document_required',
            'schedule': 'deadlines_summary',
            'procedure': 'admission_procedure',
            'contact': 'contact',
            'major_info': 'schedule_by_major',
            'location': 'admission_procedure',
            'general': 'general',
            'fee_payment': 'fee_payment'
        }
        return topic_map.get(ai_topic, 'general')

    # --------------------------- Retrieval helpers -------------------------
    def _build_where_filter(self, intent: str, entities: Dict[str, Any], query_frame: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        query_frame = query_frame or {}
        nav_candidates = query_frame.get('nav_target_candidates') or []

        if nav_candidates:
            # Nhiều nav targets -> không filter cứng, để broad search + rerank xử lý
            if len(nav_candidates) > 1:
                return None

            primary_nav = str(nav_candidates[0])
            if primary_nav.startswith('b') and '_phan_4' in primary_nav:
                return {'canonical_nav_id': primary_nav}
            if primary_nav.startswith('phan_'):
                if intent == 'admission_procedure' and (entities.get('ask_section_count') or entities.get('ask_step_count_local')):
                    return None
                return {'section_id': primary_nav}

        if intent in {'general', 'admission_procedure'}:
            return None

        where: Dict[str, Any] = {'intent_key': intent}
        if intent == 'step' and entities.get('step_number'):
            where['subtype'] = f"step_b{entities['step_number']}"
            if entities.get('section_id') == 'phan_4':
                where['step_id'] = f"b{entities['step_number']}_phan_4"
        elif intent == 'schedule_by_major' and entities.get('major_norm'):
            where['subtype'] = 'schedule_major'
        elif intent == 'docs_same_day':
            where['subtype'] = 'docs_same_day_item'
        elif intent == 'docs_later':
            where['subtype'] = 'docs_later_item'

        return where

    def _aggregate_quality(
        self,
        query: str,
        refined_query: str,
        chunks: List[Dict[str, Any]],
        intent: str,
        entities: Dict[str, Any]
    ) -> float:
        if not chunks:
            return -1.0
        reranked = self._rerank_chunks(query, refined_query, chunks[:8], intent, entities)
        top = reranked[0].get('grounding_score', 0.0)
        avg = sum(c.get('grounding_score', 0.0) for c in reranked[:3]) / max(1, min(3, len(reranked)))
        return (top * 0.7) + (avg * 0.3)

    def _rerank_chunks(
        self,
        query: str,
        refined_query: str,
        chunks: List[Dict[str, Any]],
        intent: str,
        entities: Dict[str, Any],
        query_frame: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        query_frame = query_frame or {}
        query_tokens = self._tokenize(query)
        refined_tokens = self._tokenize(refined_query)

        for chunk in chunks:
            metadata = chunk.get('metadata', {}) or {}
            content = chunk.get('content', '')
            content_tokens = self._tokenize(content)

            overlap_query = self._lexical_overlap(query_tokens, content_tokens)
            overlap_refined = self._lexical_overlap(refined_tokens, content_tokens)
            lexical_score = (overlap_query * 0.6) + (overlap_refined * 0.4)

            base = chunk.get('relevance_score', 0.0)
            bonus = 0.0

            if metadata.get('intent_key') == intent:
                bonus += 0.15

            if intent == 'step' and entities.get('step_number'):
                if metadata.get('step_number') == entities['step_number']:
                    bonus += 0.25

            if intent == 'schedule_by_major' and entities.get('major_norm'):
                if metadata.get('major_norm') == entities['major_norm']:
                    bonus += 0.30
                elif entities['major_norm'] in self._normalize(content):
                    bonus += 0.15

            if intent in {'docs_same_day', 'docs_later'}:
                subtype = metadata.get('subtype', '')
                if intent == 'docs_same_day' and 'same_day' in subtype:
                    bonus += 0.20
                if intent == 'docs_later' and 'later' in subtype:
                    bonus += 0.20

            from config import get_admission_year
            chunk_year = chunk.get('year') or metadata.get('year')
            if chunk_year == get_admission_year():
                bonus += 0.20

            # Boost chunks thuộc nav_target_candidates được hỏi
            nav_targets = query_frame.get('nav_target_candidates') or []
            if nav_targets:
                chunk_section = metadata.get('section_id') or chunk.get('section_id', '')
                chunk_nav = metadata.get('canonical_nav_id') or chunk.get('canonical_nav_id', '')
                if chunk_section in nav_targets or chunk_nav in nav_targets:
                    bonus += 0.25

            chunk['grounding_score'] = (base * 0.70) + (lexical_score * 0.30) + bonus

        return sorted(chunks, key=lambda x: x.get('grounding_score', 0.0), reverse=True)

    def _enrich_with_hierarchy(self, chunks: List[Dict[str, Any]], intent: str, max_siblings: int = 2) -> List[Dict[str, Any]]:
        """Bổ sung parent/sibling có kiểm soát để tránh nhiễu context."""
        enriched = []
        added_ids = set()

        should_enrich = intent in {
            'admission_procedure', 'step', 'schedule_by_major',
            'docs_same_day', 'docs_later', 'notes', 'contact', 'deadlines_summary'
        }

        for chunk in chunks:
            chunk_id = chunk.get('chunk_id')
            if not chunk_id or chunk_id in added_ids:
                continue
            enriched.append(chunk)
            added_ids.add(chunk_id)

            if not should_enrich:
                continue

            metadata = chunk.get('metadata', {}) or {}

            if intent == 'admission_procedure' and metadata.get('subtype') == 'steps_group':
                child_results = self.vector_db.find(where={'parent_id': chunk_id})
                if child_results and child_results.get('ids'):
                    for i, child_id in enumerate(child_results['ids']):
                        if child_id in added_ids:
                            continue
                        child_meta = child_results['metadatas'][i] or {}
                        if child_meta.get('intent_key') != 'step':
                            continue
                        child_chunk = {
                            'chunk_id': child_id,
                            'content': child_results['documents'][i],
                            'metadata': child_meta,
                            'relevance_score': chunk.get('relevance_score', 0.0) * 0.90,
                            'source': child_meta.get('source', 'Unknown'),
                            'is_child_context': True
                        }
                        enriched.append(child_chunk)
                        added_ids.add(child_id)

            parent_id = metadata.get('parent_id')
            if not parent_id or parent_id in added_ids:
                continue

            parent_result = self.vector_db.get(ids=[parent_id])
            if parent_result and parent_result.get('ids'):
                p_meta = parent_result['metadatas'][0]
                parent_chunk = {
                    'chunk_id': parent_id,
                    'content': parent_result['documents'][0],
                    'metadata': p_meta,
                    'relevance_score': chunk.get('relevance_score', 0.0) * 0.92,
                    'source': (p_meta or {}).get('source', 'Unknown'),
                    'is_parent_context': True
                }
                enriched.append(parent_chunk)
                added_ids.add(parent_id)

            sibling_results = self.vector_db.find(where={'parent_id': parent_id})
            sibling_count = 0
            if sibling_results and sibling_results.get('ids'):
                for i, sib_id in enumerate(sibling_results['ids']):
                    if sibling_count >= max_siblings:
                        break
                    if sib_id in added_ids:
                        continue
                    sib_meta = sibling_results['metadatas'][i] or {}
                    sib_intent = sib_meta.get('intent_key')
                    if sib_intent and sib_intent != intent:
                        if not (
                            intent == 'admission_procedure'
                            and sib_intent in {'step', 'docs_same_day', 'docs_later', 'schedule_by_major', 'schedule_session'}
                        ):
                            continue
                    sibling_chunk = {
                        'chunk_id': sib_id,
                        'content': sibling_results['documents'][i],
                        'metadata': sib_meta,
                        'relevance_score': chunk.get('relevance_score', 0.0) * 0.82,
                        'source': sib_meta.get('source', 'Unknown'),
                        'is_sibling_context': True
                    }
                    enriched.append(sibling_chunk)
                    added_ids.add(sib_id)
                    sibling_count += 1

        return enriched

    def _dedupe_and_cap_context(self, chunks: List[Dict[str, Any]], top_k: int, intent: str) -> List[Dict[str, Any]]:
        deduped = []
        seen_ids = set()
        seen_snippets = set()

        for chunk in chunks:
            chunk_id = chunk.get('chunk_id')
            content = chunk.get('content', '')
            snippet = re.sub(r'\s+', ' ', content.strip().lower())[:180]
            if not chunk_id or chunk_id in seen_ids or snippet in seen_snippets:
                continue

            metadata = chunk.get('metadata', {}) or {}
            chunk['source'] = chunk.get('source') or metadata.get('source', 'Unknown')
            deduped.append(chunk)
            seen_ids.add(chunk_id)
            seen_snippets.add(snippet)

            if intent == 'schedule_by_major':
                cap = max(top_k, 30)
            elif intent in {'admission_procedure', 'deadlines_summary'}:
                cap = top_k
            else:
                cap = min(top_k, 8)
            if len(deduped) >= cap:
                break

        return deduped

    def _tokenize(self, text: str) -> Set[str]:
        text = (text or '').lower()
        tokens = re.findall(r"[\wÀ-ỹ]+", text)
        return {t for t in tokens if len(t) > 1}

    def _lexical_overlap(self, query_tokens: Set[str], content_tokens: Set[str]) -> float:
        if not query_tokens or not content_tokens:
            return 0.0
        return len(query_tokens & content_tokens) / max(1, len(query_tokens))

    @staticmethod
    def _prefer_year(chunks: List[Dict[str, Any]], target_year: int) -> List[Dict[str, Any]]:
        """Lọc ưu tiên chunks đúng năm tuyển sinh. Giữ chunks năm khác nếu không đủ."""
        matched = []
        others = []
        for c in chunks:
            y = c.get('year') or (c.get('metadata') or {}).get('year')
            if y == target_year:
                matched.append(c)
            else:
                others.append(c)
        if matched:
            return matched + others
        return chunks

    def _format_results(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        chunks = []
        if not results or not results.get('ids') or not results['ids'][0]:
            return []

        ids = results['ids'][0]
        documents = results['documents'][0]
        metadatas = results['metadatas'][0]
        distances = results['distances'][0]

        for i in range(len(ids)):
            chunks.append({
                'chunk_id': ids[i],
                'content': documents[i],
                'metadata': metadatas[i],
                'relevance_score': 1 - distances[i]
            })
        return chunks


if __name__ == "__main__":
    retriever = AutomationRetriever()
    results = retriever.retrieve("ngành toán học nhập học lúc nào", top_k=8)
    print(f"\n[OK] Tìm thấy {len(results)} kết quả")
    for i, r in enumerate(results[:5], 1):
        meta = r.get('metadata', {}) or {}
        print(f"[{i}] ({meta.get('intent_key')}/{meta.get('subtype')}) {r.get('content', '')[:120]}...")
