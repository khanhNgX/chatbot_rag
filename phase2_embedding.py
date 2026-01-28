"""
PHASE 2: Embedding & Storage
Module để tạo embeddings và lưu vào ChromaDB
Sử dụng ChromaDB's default embedding function thay vì Gemini API
"""

import json
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from typing import List, Dict, Any


class EmbeddingGenerator:
    """Tạo embeddings sử dụng sentence-transformers (local)"""
    
    def __init__(self):
        # Sử dụng default embedding function của ChromaDB
        self.embedding_function = embedding_functions.DefaultEmbeddingFunction()
    
    def prepare_text_for_embedding(self, chunk: Dict[str, Any]) -> str:
        """Chuẩn bị text để embed theo template"""
        chunk_type = chunk.get('type', 'unknown')
        year = chunk.get('year', '')
        title = chunk.get('title', '')
        content = chunk.get('content', '')
        
        # Lấy metadata quan trọng
        metadata_parts = []
        
        if 'fees' in chunk:
            total = chunk.get('total_required', sum(chunk['fees'].values()))
            metadata_parts.append(f"Total: {total:,}đ")
        
        if 'payment_period' in chunk and chunk['payment_period']:
            period = chunk['payment_period']
            if period:
                metadata_parts.append(f"Period: {period.get('start', '')}-{period.get('end', '')}")
        
        if 'date' in chunk:
            metadata_parts.append(f"Date: {chunk['date']}")
        
        if 'major' in chunk:
            metadata_parts.append(f"Major: {chunk['major']}")
        
        # Combine theo template
        text = f"[TYPE: {chunk_type}] [YEAR: {year}] {title}\n{content}"
        
        if metadata_parts:
            text += f"\nMetadata: {', '.join(metadata_parts)}"
        
        return text
    
    def generate_embedding(self, text: str) -> List[float]:
        """Tạo embedding vector cho text"""
        try:
            embeddings = self.embedding_function([text])
            return embeddings[0] if embeddings else []
        except Exception as e:
            print(f"⚠️ Embedding error: {e}")
            return []


class VectorStorage:
    """Lưu trữ vectors trong ChromaDB"""
    
    def __init__(self, collection_name: str = "admission_chunks"):
        self.client = chromadb.Client(Settings(
            anonymized_telemetry=False,
            allow_reset=True
        ))
        self.collection_name = collection_name
        self.collection = None
        
    def create_collection(self):
        """Tạo collection mới (xóa cũ nếu tồn tại)"""
        try:
            self.client.delete_collection(self.collection_name)
        except:
            pass
        
        self.collection = self.client.create_collection(
            name=self.collection_name,
            metadata={"description": "RAG chunks for admission procedures"}
        )
        print(f"✅ Đã tạo collection: {self.collection_name}")
    
    def get_or_create_collection(self):
        """Lấy hoặc tạo collection"""
        try:
            self.collection = self.client.get_collection(self.collection_name)
            print(f"✅ Đã load collection: {self.collection_name}")
        except:
            self.create_collection()
    
    def add_chunks(self, chunks: List[Dict[str, Any]], embeddings: List[List[float]]):
        """Thêm chunks và embeddings vào database"""
        if not self.collection:
            self.get_or_create_collection()
        
        # Prepare data for ChromaDB
        ids = [chunk['chunk_id'] for chunk in chunks]
        documents = [chunk.get('content', '') for chunk in chunks]
        
        # Prepare metadata (chỉ giữ các fields simple types)
        metadatas = []
        for chunk in chunks:
            metadata = {
                'chunk_id': chunk['chunk_id'],
                'type': chunk['type'],
                'year': chunk['year'],
                'title': chunk.get('title', ''),
            }
            
            # Thêm các fields optional
            if 'section_number' in chunk:
                metadata['section_number'] = chunk['section_number']
            
            if 'step_number' in chunk:
                metadata['step_number'] = chunk['step_number']
            
            if 'date' in chunk:
                metadata['date'] = chunk['date']
            
            if 'major' in chunk:
                metadata['major'] = chunk['major']
            
            # Keywords as string
            if 'metadata' in chunk and 'keywords' in chunk['metadata']:
                metadata['keywords'] = ','.join(chunk['metadata']['keywords'])
            
            metadatas.append(metadata)
        
        # Add to collection
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )
        
        print(f"✅ Đã thêm {len(chunks)} chunks vào database")
    
    def query(self, query_embedding: List[float], n_results: int = 10, 
              where: Dict = None) -> Dict[str, Any]:
        """Query vector database"""
        if not self.collection:
            self.get_or_create_collection()
        
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where
        )
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """Lấy thống kê database"""
        if not self.collection:
            return {}
        
        count = self.collection.count()
        return {
            'total_chunks': count,
            'collection_name': self.collection_name
        }


class EmbeddingPipeline:
    """Pipeline để xử lý chunks thành embeddings và lưu vào DB"""
    
    def __init__(self):
        self.embedding_gen = EmbeddingGenerator()
        self.vector_storage = VectorStorage()
    
    def process_chunks(self, chunks: List[Dict[str, Any]]):
        """Xử lý tất cả chunks"""
        print(f"🔨 Đang xử lý {len(chunks)} chunks...")
        
        # Tạo embeddings
        embeddings = []
        for idx, chunk in enumerate(chunks, 1):
            print(f"   [{idx}/{len(chunks)}] Embedding: {chunk['chunk_id']}")
            
            # Prepare text
            text = self.embedding_gen.prepare_text_for_embedding(chunk)
            
            # Generate embedding
            embedding = self.embedding_gen.generate_embedding(text)
            
            if embedding is not None and len(embedding) > 0:
                embeddings.append(embedding)
            else:
                print(f"   ⚠️ Không tạo được embedding cho chunk {chunk['chunk_id']}")
                # Sử dụng dummy embedding (zeros)
                embeddings.append([0.0] * 384)  # Default embedding size
        
        print()
        
        # Lưu vào database
        print("💾 Đang lưu vào ChromaDB...")
        self.vector_storage.create_collection()
        self.vector_storage.add_chunks(chunks, embeddings)
        
        # Stats
        stats = self.vector_storage.get_stats()
        print(f"\n📊 Database stats:")
        print(f"   - Total chunks: {stats['total_chunks']}")
        print(f"   - Collection: {stats['collection_name']}")


def main():
    """Test embedding và storage"""
    print("=" * 70)
    print("PHASE 2: Embedding & Storage")
    print("=" * 70)
    print()
    
    # Load chunks
    print("📄 Đang load chunks từ file...")
    try:
        with open('chunks.json', 'r', encoding='utf-8') as f:
            chunks = json.load(f)
        print(f"✅ Đã load {len(chunks)} chunks")
        print()
    except FileNotFoundError:
        print("❌ Không tìm thấy chunks.json")
        print("   Vui lòng chạy phase1_chunking.py trước")
        return
    
    # Process embeddings (không cần API key)
    pipeline = EmbeddingPipeline()
    pipeline.process_chunks(chunks)
    
    print("\n✅ PHASE 2 hoàn thành!")


if __name__ == '__main__':
    main()
