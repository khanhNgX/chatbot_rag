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

    def analyze(self, query: str) -> Dict[str, Any]:
        """Trả về intent + entities để app.py/generator dùng chung."""
        processed = self._safe_ai_process(query)
        refined = processed.get('refined_query', query)
        topic = processed.get('detected_topic', 'general')

        entities = self._extract_entities(query)
        intent = self._canonical_intent(query=query, refined_query=refined, ai_topic=topic, entities=entities)
        entities['intent'] = intent

        return {
            'raw_query': query,
            'refined_query': refined,
            'detected_topic': topic,
            'intent': intent,
            'entities': entities,
            'reason': processed.get('reason', '')
        }

    def retrieve(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """Retrieve theo intent/entity: analyze -> filter -> search -> rerank -> enrich."""
        print(f"\n[USER QUERY] Gốc: {query}")

        analysis = self.analyze(query)
        refined_query = analysis.get('refined_query', query)
        intent = analysis.get('intent', 'general')
        entities = analysis.get('entities', {}) or {}

        print(f"[AI REWRITE] Mới: {refined_query}")
        print(f"[INTENT] Canonical: {intent}")

        query_embedding = self.embedding_gen.generate_embedding(refined_query)

        where_filter = self._build_where_filter(intent, entities)
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

        filtered_score = self._aggregate_quality(query, refined_query, filtered_chunks, intent, entities)
        broad_score = self._aggregate_quality(query, refined_query, broad_chunks, intent, entities)

        use_broad = (not filtered_chunks) or (broad_score > filtered_score + 0.10)
        best_chunks = broad_chunks if use_broad else filtered_chunks
        if use_broad and where_filter:
            print("[FALLBACK] Dùng toàn văn do chất lượng cao hơn filtered")

        reranked = self._rerank_chunks(query, refined_query, best_chunks, intent, entities)
        enriched = self._enrich_with_hierarchy(reranked, intent=intent)
        final_chunks = self._dedupe_and_cap_context(enriched, top_k=top_k, intent=intent)

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

    def _extract_entities(self, query: str) -> Dict[str, Any]:
        qn = self._normalize(query)
        entities: Dict[str, Any] = {}

        # Bước B1-B4
        m_step = re.search(r'\bb\s*([1-4])\b|\bbuoc\s*([1-4])\b|\bbước\s*([1-4])\b', qn)
        if m_step:
            step_no = next((int(g) for g in m_step.groups() if g), None)
            if step_no:
                entities['step_number'] = step_no

        # Ngành
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

        # Thời gian/hạn
        date_matches = re.findall(r'\b\d{1,2}/\d{1,2}/\d{4}\b', query)
        if date_matches:
            entities['date'] = date_matches[0]

        # Buổi sáng/chiều
        if any(k in qn for k in ['buoi sang', 'sang']):
            entities['time_slot_norm'] = 'sáng'
        elif any(k in qn for k in ['buoi chieu', 'chieu']):
            entities['time_slot_norm'] = 'chiều'

        return entities

    def _canonical_intent(
        self,
        query: str,
        refined_query: str,
        ai_topic: str,
        entities: Dict[str, Any]
    ) -> str:
        q = self._normalize(f"{query} {refined_query}")

        if entities.get('step_number'):
            return 'step'

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

        # map từ ai topic nếu không khớp cụ thể
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
    def _build_where_filter(self, intent: str, entities: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if intent in {'general', 'admission_procedure'}:
            return None

        # Ưu tiên bắt đúng intent_key trước
        where: Dict[str, Any] = {'intent_key': intent}

        # Một số intent nằm trong detail subtype
        if intent == 'step' and entities.get('step_number'):
            where['subtype'] = f"step_b{entities['step_number']}"
        elif intent == 'schedule_by_major' and entities.get('major_norm'):
            where['subtype'] = 'schedule_major'
        elif intent == 'docs_same_day':
            where['subtype'] = 'docs_same_day_item'
        elif intent == 'docs_later':
            where['subtype'] = 'docs_later_item'
        elif intent == 'fee_payment':
            # ưu tiên quét toàn bộ chunk hướng dẫn thanh toán
            pass

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
        entities: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
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

            # Intent bonus
            if metadata.get('intent_key') == intent:
                bonus += 0.15

            # Step bonus
            if intent == 'step' and entities.get('step_number'):
                if metadata.get('step_number') == entities['step_number']:
                    bonus += 0.25

            # Major bonus
            if intent == 'schedule_by_major' and entities.get('major_norm'):
                if metadata.get('major_norm') == entities['major_norm']:
                    bonus += 0.30
                elif entities['major_norm'] in self._normalize(content):
                    bonus += 0.15

            # Docs group bonus
            if intent in {'docs_same_day', 'docs_later'}:
                subtype = metadata.get('subtype', '')
                if intent == 'docs_same_day' and 'same_day' in subtype:
                    bonus += 0.20
                if intent == 'docs_later' and 'later' in subtype:
                    bonus += 0.20

            chunk['grounding_score'] = (base * 0.70) + (lexical_score * 0.30) + bonus

        return sorted(chunks, key=lambda x: x.get('grounding_score', 0.0), reverse=True)

    def _enrich_with_hierarchy(self, chunks: List[Dict[str, Any]], intent: str, max_siblings: int = 2) -> List[Dict[str, Any]]:
        """Bổ sung parent/sibling có kiểm soát để tránh nhiễu context."""
        enriched = []
        added_ids = set()

        # Chỉ enrich mạnh cho intent cần ngữ cảnh
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

            # admission_procedure: khi đang ở nhóm steps thì kéo luôn các step con B1-B4
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

            # parent
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

            # sibling cùng parent + cùng intent_key
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

            # intent factual giữ gọn hơn, riêng schedule_by_major cần rộng hơn để không thiếu ngành
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
