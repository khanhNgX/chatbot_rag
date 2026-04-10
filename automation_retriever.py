# -*- coding: utf-8 -*-
"""
AUTOMATION RETRIEVER
Sử dụng LLM để Rewrite Query và Detect Metadata Tag phục vụ tìm kiếm chính xác 99%
"""

import os
from typing import List, Dict, Any, Optional
from automation_ai_rag import AIAutomation
from phase2_embedding import EmbeddingGenerator, VectorStorage

class AutomationRetriever:
    def __init__(self):
        self.ai = AIAutomation()
        self.embedding_gen = EmbeddingGenerator()
        self.vector_db = VectorStorage()
        # Để tương thích với app.py
        self.query_analyzer = self
        
    def analyze(self, query: str) -> Dict[str, Any]:
        """Wrapper để tương thích với query_analyzer.analyze của app.py"""
        res = self.ai.process_user_query(query)
        # Map detected_topic về intent để app.py không lỗi
        res['intent'] = res.get('detected_topic', 'general')
        return res
        
    def retrieve(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """Quy trình tìm kiếm thông minh: Rewrite -> Tagging -> Filter -> Search"""
        print(f"\n[USER QUERY] Gốc: {query}")
        
        # 1. AI Rewrite & Tagging Query
        processed = self.ai.process_user_query(query)
        refined_query = processed.get('refined_query', query)
        detected_topic = processed.get('detected_topic', 'general')
        
        print(f"[AI REWRITE] Mới: {refined_query}")
        print(f"[AI TAGGING] Nhận diện Topic: {detected_topic}")
        
        # 2. Embedding câu query đã viết lại (Tốt hơn query gốc nhiều lần)
        query_embedding = self.embedding_gen.generate_embedding(refined_query)
        
        # 3. Build AI Metadata Filter
        # Chỉ lọc theo topic nếu topic không phải 'general' (để mở rộng kết quả)
        where_filter = None
        if detected_topic != 'general':
            where_filter = {"topic": detected_topic}
            print(f"[FILTERING] Chỉ tìm kiếm trong các đoạn có nhãn: {detected_topic}")
            
        # 4. Tìm kiếm tương đồng vector trong ChromaDB
        results = self.vector_db.query(
            query_embedding=query_embedding,
            n_results=top_k,
            where=where_filter
        )
        
        # 5. Xử lý kết quả (Hierarchical Retrieval)
        ids = results.get('ids', [[]])[0]
        if not ids and where_filter:
            # Fallback: Nếu lọc quá chặt không có kết quả, bỏ lọc và tìm lại
            print("[FALLBACK] Lọc quá chặt, đang thử tìm kiếm toàn văn...")
            results = self.vector_db.query(
                query_embedding=query_embedding,
                n_results=top_k,
                where=None
            )
            
        raw_chunks = self._format_results(results)
        
        # 6. ENRICHMENT: Nếu là đoạn Con, lôi thêm đoạn Cha lên
        enriched_chunks = []
        added_ids = set()
        
        for chunk in raw_chunks:
            chunk_id = chunk['chunk_id']
            if chunk_id in added_ids: continue
            
            # Thêm chính nó
            enriched_chunks.append(chunk)
            added_ids.add(chunk_id)
            
            # Nếu là mảnh Con, tìm Cha và Anh Chị Em của nó
            metadata = chunk.get('metadata', {})
            parent_id = metadata.get('parent_id')
            
            if parent_id and parent_id not in added_ids:
                print(f"[HIERARCHY] Đang lôi thêm context từ Cha & Anh Chị Em cho: {parent_id}")
                
                # 1. Lấy nội dung Cha
                parent_results = self.vector_db.get(ids=[parent_id])
                if parent_results and parent_results['ids']:
                    enriched_chunks.append({
                        'chunk_id': parent_id,
                        'content': parent_results['documents'][0],
                        'metadata': parent_results['metadatas'][0],
                        'relevance_score': chunk['relevance_score'] * 0.9,
                        'is_parent_context': True
                    })
                    added_ids.add(parent_id)
                
                # 2. Lấy toàn bộ Anh Chị Em (Siblings) để đảm bảo không mất các mục trong danh sách
                # Sibling retrieval giúp lấy toàn bộ danh sách hồ sơ/lịch nếu 1 mục được tìm thấy
                sibling_results = self.vector_db.find(where={"parent_id": parent_id})
                if sibling_results and sibling_results['ids']:
                    for i in range(len(sibling_results['ids'])):
                        sib_id = sibling_results['ids'][i]
                        if sib_id not in added_ids:
                            enriched_chunks.append({
                                'chunk_id': sib_id,
                                'content': sibling_results['documents'][i],
                                'metadata': sibling_results['metadatas'][i],
                                'relevance_score': chunk['relevance_score'] * 0.8, # Score thấp hơn
                                'is_sibling_context': True
                            })
                            added_ids.add(sib_id)
                    
        return enriched_chunks

    def _format_results(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Chuẩn hóa kết quả tìm kiếm"""
        chunks = []
        if not results['ids'] or not results['ids'][0]:
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
    # Test query
    results = retriever.retrieve("tiền học năm 2025 nộp khi nào")
    print(f"\n[OK] Tìm thấy {len(results)} kết quả tương đồng nhất.")
    for i, r in enumerate(results[:2], 1):
        print(f"[{i}] [{r['metadata'].get('topic')}] {r['content'][:100]}...")
