"""
PHASE 3: Query Processing & Retrieval
Hybrid search với semantic + metadata filter + reranking
"""

import json
import re
from typing import List, Dict, Any, Tuple
from phase2_embedding import EmbeddingGenerator, VectorStorage


class QueryAnalyzer:
    """Phân tích query và extract intent"""
    
    # Intent patterns
    INTENT_PATTERNS = {
        'fee_info': ['học phí', 'tiền', 'phí', 'bao nhiêu', 'chi phí', 'nộp tiền', 'khoản'],
        'schedule': ['lịch', 'ngày', 'khi nào', 'thời gian', 'buổi', 'giờ'],
        'document': ['hồ sơ', 'giấy tờ', 'mang gì', 'cần gì', 'chuẩn bị gì', 'nộp gì'],
        'procedure': ['thủ tục', 'các bước', 'làm thế nào', 'cách', 'quy trình'],
        'deadline': ['hạn', 'deadline', 'chót', 'trước ngày', 'sau ngày'],
        'contact': ['liên hệ', 'số điện thoại', 'email', 'địa chỉ', 'phòng'],
        'general': []
    }
    
    def analyze(self, query: str) -> Dict[str, Any]:
        """Phân tích query"""
        query_lower = query.lower()
        
        # Extract year
        year = self._extract_year(query)
        
        # Classify intent
        intent = self._classify_intent(query_lower)
        
        # Extract keywords
        keywords = self._extract_keywords(query)
        
        return {
            'query': query,
            'intent': intent,
            'year': year,
            'keywords': keywords
        }
    
    def _extract_year(self, query: str) -> int:
        """Trích xuất năm từ query"""
        year_match = re.search(r'202[45]', query)
        if year_match:
            return int(year_match.group(0))
        return 2025  # Default
    
    def _classify_intent(self, query_lower: str) -> str:
        """Phân loại intent"""
        scores = {}
        
        for intent, patterns in self.INTENT_PATTERNS.items():
            score = sum(1 for pattern in patterns if pattern in query_lower)
            if score > 0:
                scores[intent] = score
        
        if not scores:
            return 'general'
        
        # Return intent có score cao nhất
        return max(scores.items(), key=lambda x: x[1])[0]
    
    def _extract_keywords(self, query: str) -> List[str]:
        """Trích xuất keywords quan trọng"""
        # Simple tokenization
        words = re.findall(r'\w+', query.lower())
        
        # Filter stopwords
        stopwords = {'là', 'của', 'và', 'có', 'được', 'thì', 'cho', 'với', 'từ', 'trong', 'đến'}
        keywords = [w for w in words if w not in stopwords and len(w) > 2]
        
        return keywords


class HybridRetriever:
    """Hybrid retrieval: Semantic + Metadata filter"""
    
    def __init__(self):
        self.embedding_gen = EmbeddingGenerator()
        self.vector_storage = VectorStorage()
        self.vector_storage.get_or_create_collection()
        self.query_analyzer = QueryAnalyzer()
    
    def retrieve(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Retrieve relevant chunks"""
        # Analyze query
        analysis = self.query_analyzer.analyze(query)
        print(f"🔍 Query analysis:")
        print(f"   - Intent: {analysis['intent']}")
        print(f"   - Year: {analysis['year']}")
        print(f"   - Keywords: {analysis['keywords'][:5]}")
        print()
        
        # Generate query embedding
        query_embedding = self.embedding_gen.generate_embedding(query)
        
        # Build metadata filter
        where_filter = self._build_filter(analysis)
        
        # Semantic search with filter
        print(f"🔎 Searching với filter: {where_filter}")
        results = self.vector_storage.query(
            query_embedding=query_embedding,
            n_results=top_k * 2,  # Lấy nhiều hơn để có thể filter
            where=where_filter if where_filter else None
        )
        
        # Convert results to chunks
        chunks = self._results_to_chunks(results)
        
        # Context enrichment (thêm parent/sibling)
        enriched_chunks = self._enrich_context(chunks[:top_k])
        
        return enriched_chunks
    
    def _build_filter(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Build metadata filter cho ChromaDB"""
        conditions = []
        
        # Filter by year
        if analysis['year']:
            conditions.append({'year': analysis['year']})
        
        # Filter by intent -> type
        intent_to_type = {
            'fee_info': 'fee_info',
            'schedule': 'schedule',
            'document': 'document_list',
            'procedure': 'section'
        }
        
        if analysis['intent'] in intent_to_type:
            conditions.append({'type': intent_to_type[analysis['intent']]})
        
        # ChromaDB requires $and operator for multiple conditions
        if len(conditions) == 0:
            return None
        elif len(conditions) == 1:
            return conditions[0]
        else:
            return {"$and": conditions}
    
    def _results_to_chunks(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert ChromaDB results to chunk format"""
        chunks = []
        
        if not results or not results['ids'] or not results['ids'][0]:
            return chunks
        
        ids = results['ids'][0]
        documents = results['documents'][0]
        metadatas = results['metadatas'][0]
        distances = results['distances'][0]
        
        for i in range(len(ids)):
            chunk = {
                'chunk_id': ids[i],
                'content': documents[i],
                'metadata': metadatas[i],
                'distance': distances[i],
                'relevance_score': 1 - distances[i]  # Convert distance to similarity
            }
            chunks.append(chunk)
        
        return chunks
    
    def _enrich_context(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Bổ sung context với parent/sibling chunks"""
        enriched = chunks.copy()
        added_ids = {chunk['chunk_id'] for chunk in chunks}
        
        for chunk in chunks[:3]:  # Chỉ enrich cho top 3
            metadata = chunk['metadata']
            
            # Thêm overview nếu chưa có
            if 'overview' not in added_ids:
                year = metadata.get('year', 2025)
                overview_id = f'admission_{year}_overview'
                if overview_id not in added_ids:
                    # Query để lấy overview
                    overview_results = self.vector_storage.collection.get(
                        ids=[overview_id]
                    )
                    if overview_results and overview_results['ids']:
                        enriched.append({
                            'chunk_id': overview_id,
                            'content': overview_results['documents'][0],
                            'metadata': overview_results['metadatas'][0],
                            'relevance_score': 0.7,  # Lower score cho context
                            'is_context': True
                        })
                        added_ids.add(overview_id)
        
        return enriched


def main():
    """Test retrieval"""
    print("=" * 70)
    print("PHASE 3: Query Processing & Retrieval")
    print("=" * 70)
    print()
    
    # Initialize retriever (không cần API key)
    retriever = HybridRetriever()
    
    # Test queries
    test_queries = [
        "Học phí năm 2025 là bao nhiêu?",
        "Lịch nhập học ngành Toán?",
        "Cần chuẩn bị hồ sơ gì?",
        "Thủ tục nhập học gồm những bước nào?"
    ]
    
    for query in test_queries:
        print(f"\n{'='*70}")
        print(f"Query: {query}")
        print('='*70)
        
        chunks = retriever.retrieve(query, top_k=3)
        
        print(f"\n📄 Retrieved {len(chunks)} chunks:")
        for i, chunk in enumerate(chunks, 1):
            print(f"\n[{i}] {chunk['chunk_id']}")
            print(f"    Score: {chunk.get('relevance_score', 0):.3f}")
            print(f"    Type: {chunk['metadata'].get('type', 'N/A')}")
            print(f"    Content: {chunk['content'][:150]}...")
        
        print()


if __name__ == '__main__':
    main()
