# -*- coding: utf-8 -*-
"""
PHASE 2: Embedding & Storage (Pure REST Version)
Module để tạo embeddings bằng Gemini API qua REST và lưu vào file JSON
Loại bỏ hoàn toàn thư viện google-generativeai để tránh lỗi pydantic-core/grpcio
"""

import json
import os
import numpy as np
import requests
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional

# Load biến môi trường
load_dotenv()
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

class EmbeddingGenerator:
    """Tạo embeddings sử dụng Gemini API qua REST (Pure Python)"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or GEMINI_API_KEY
        if not self.api_key:
            print("[WARNING] Cảnh báo: Chưa cấu hình GEMINI_API_KEY. Việc tạo embedding sẽ thất bại.")
    
    def prepare_text_for_embedding(self, chunk: Dict[str, Any]) -> str:
        """Chuẩn bị text để embed theo template"""
        chunk_type = chunk.get('type', 'unknown')
        year = chunk.get('year', '')
        title = chunk.get('title', '')
        content = chunk.get('content', '')
        
        # Lấy metadata quan trọng
        metadata_parts = []
        if 'fees' in chunk:
            total = chunk.get('total_required', sum(chunk.get('fees', {}).values()) if isinstance(chunk.get('fees'), dict) else 0)
            metadata_parts.append(f"Total: {total:,}đ")
        
        if 'date' in chunk:
            metadata_parts.append(f"Date: {chunk['date']}")
        
        if 'major' in chunk:
            metadata_parts.append(f"Major: {chunk['major']}")
        
        # Combine
        text = f"[TYPE: {chunk_type}] [YEAR: {year}] {title}\n{content}"
        if metadata_parts:
            text += f"\nMetadata: {', '.join(metadata_parts)}"
        return text
    
    def generate_embedding(self, text: str) -> List[float]:
        """Tạo embedding vector qua REST call"""
        if not self.api_key:
            return [0.0] * 3072
            
        models_to_try = ["text-embedding-004", "gemini-embedding-001"]
        headers = {"Content-Type": "application/json"}
        payload = {
            "content": {"parts": [{"text": text}]},
            "task_type": "RETRIEVAL_DOCUMENT"
        }
        
        response = None
        for model in models_to_try:
            for version in ["v1beta", "v1"]:
                url = f"https://generativelanguage.googleapis.com/{version}/models/{model}:embedContent?key={self.api_key}"
                try:
                    res = requests.post(url, headers=headers, json=payload, timeout=20)
                    if res.status_code == 200:
                        response = res
                        break
                except:
                    continue
            if response: break
            
        try:
            if not response:
                raise Exception("Không thể kết nối tới các endpoint Embedding.")
                
            result = response.json()
            return result.get('embedding', {}).get('values', [])
        except Exception as e:
            print(f"[WARNING] REST Embedding error: {e}")
            return [0.0] * 3072


class VectorStorage:
    """Lưu trữ vectors trong file JSON (Pure Python fallback cho chromadb)"""
    
    def __init__(self, db_path: str = "vector_db.json"):
        self.db_path = db_path
        self.data = {"chunks": [], "embeddings": []}
        self.load()
        
    def create_collection(self):
        """Reset database"""
        self.data = {"chunks": [], "embeddings": []}
        self.save()
        print(f"[OK] Đã reset database tại {self.db_path}")
    
    def add_chunks(self, chunks: List[Dict[str, Any]], embeddings: List[List[float]]):
        """Thêm chunks và embeddings vào database file"""
        for chunk in chunks:
            if 'source' not in chunk:
                chunk['source'] = 'Unknown'
        
        self.data["chunks"].extend(chunks)
        self.data["embeddings"].extend(embeddings)
        self.save()
        print(f"[OK] Đã thêm {len(chunks)} chunks vào database file")
    
    def query(self, query_embedding: List[float], n_results: int = 10, 
              where: Dict = None) -> Dict[str, Any]:
        """Query vector database sử dụng cosine similarity (Numpy)"""
        if not self.data["embeddings"]:
            return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}
        
        # Chuyển sang numpy arrays
        q = np.array(query_embedding)
        E = np.array(self.data["embeddings"])
        
        # Tính cosine similarity
        q_norm = q / (np.linalg.norm(q) + 1e-9)
        E_norm = E / (np.linalg.norm(E, axis=1, keepdims=True) + 1e-9)
        similarities = np.dot(E_norm, q_norm)
        
        # Metadata filter
        indices = np.arange(len(similarities))
        mask = np.ones(len(similarities), dtype=bool)
        if where:
            for i in range(len(self.data["chunks"])):
                chunk = self.data["chunks"][i]
                match = True
                if "$and" in where:
                    for cond in where["$and"]:
                        for k, v in cond.items():
                            if chunk.get(k) != v: match = False; break
                        if not match: break
                else:
                    for k, v in where.items():
                        if chunk.get(k) != v: match = False; break
                if not match:
                    mask[i] = False
        
        valid_indices = indices[mask]
        valid_similarities = similarities[mask]
        if len(valid_indices) == 0:
            return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}
            
        top_k = min(n_results, len(valid_indices))
        sorted_indices_of_valid = np.argsort(valid_similarities)[::-1][:top_k]
        final_indices = valid_indices[sorted_indices_of_valid]
        final_similarities = valid_similarities[sorted_indices_of_valid]
        
        return {
            "ids": [[self.data["chunks"][i]["chunk_id"] for i in final_indices]],
            "documents": [[self.data["chunks"][i]["content"] for i in final_indices]],
            "metadatas": [[self.data["chunks"][i] for i in final_indices]],
            "distances": [[float(1.0 - s) for s in final_similarities]]
        }
    
    def get(self, ids: List[str]) -> Dict[str, Any]:
        """Lấy chunks theo IDs"""
        found_docs = []
        found_metadatas = []
        found_ids = []
        id_set = set(ids)
        for chunk in self.data["chunks"]:
            if chunk["chunk_id"] in id_set:
                found_ids.append(chunk["chunk_id"])
                found_docs.append(chunk["content"])
                found_metadatas.append(chunk)
        return {"ids": found_ids, "documents": found_docs, "metadatas": found_metadatas}

    def find(self, where: Dict) -> Dict[str, Any]:
        """Tìm kiếm chunks theo metadata (không dùng vector)"""
        found_docs = []
        found_metadatas = []
        found_ids = []
        
        for i, chunk in enumerate(self.data["chunks"]):
            match = True
            for k, v in where.items():
                if chunk.get(k) != v:
                    match = False
                    break
            if match:
                found_ids.append(chunk.get("chunk_id", f"idx_{i}"))
                found_docs.append(chunk["content"])
                found_metadatas.append(chunk)
                
        return {"ids": found_ids, "documents": found_docs, "metadatas": found_metadatas}

    def save(self):
        """Lưu toàn bộ database ra file JSON"""
        with open(self.db_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
            
    def load(self):
        """Load database từ file JSON"""
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
                print(f"[OK] Đã load {len(self.data['chunks'])} chunks từ {self.db_path}")
            except Exception as e:
                print(f"[WARNING] Lỗi load database: {e}. Khởi tạo DB mới.")
                self.data = {"chunks": [], "embeddings": []}
        else:
            self.data = {"chunks": [], "embeddings": []}

    def get_stats(self) -> Dict[str, Any]:
        return {'total_chunks': len(self.data["chunks"]), 'db_path': self.db_path}


class EmbeddingPipeline:
    """Pipeline để xử lý chunks thành embeddings và lưu vào DB"""
    def __init__(self):
        self.embedding_gen = EmbeddingGenerator()
        self.vector_storage = VectorStorage()
    
    def process_chunks(self, chunks: List[Dict[str, Any]]):
        print(f"🔨 Đang xử lý {len(chunks)} chunks bằng REST API...")
        embeddings = []
        for idx, chunk in enumerate(chunks, 1):
            print(f"   [{idx}/{len(chunks)}] Embedding: {chunk['chunk_id']}")
            text = self.embedding_gen.prepare_text_for_embedding(chunk)
            embedding = self.embedding_gen.generate_embedding(text)
            if embedding:
                embeddings.append(embedding)
            else:
                print(f"   [WARNING] Lỗi chunk {chunk['chunk_id']}, dùng vector rỗng.")
                embeddings.append([0.0] * 3072)
        
        self.vector_storage.create_collection()
        self.vector_storage.add_chunks(chunks, embeddings)
        print(f"[OK] PHASE 2 hoàn thành! Tổng: {len(chunks)} chunks.")

def main():
    print("=" * 70)
    print("PHASE 2: Embedding & Storage (REST Fallback)")
    print("=" * 70)
    try:
        with open('all_chunks.json', 'r', encoding='utf-8') as f:
            chunks = json.load(f)
        pipeline = EmbeddingPipeline()
        pipeline.process_chunks(chunks)
    except Exception as e:
        print(f"[ERROR] Lỗi: {e}")

if __name__ == '__main__':
    main()
