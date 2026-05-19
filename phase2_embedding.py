# -*- coding: utf-8 -*-
"""
PHASE 2: Embedding & Storage (Pure REST Version)
Module để tạo embeddings bằng Gemini API qua REST và lưu vào file JSON
"""

import json
import os
import hashlib
import numpy as np
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional
import requests

# Load biến môi trường
load_dotenv()
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_MODEL_EMBED = (os.getenv('GEMINI_MODEL_EMBED') or 'gemini-embedding-001').strip()

class EmbeddingGenerator:
    """Tạo embeddings sử dụng Gemini API qua REST (Pure Python)."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = (api_key or GEMINI_API_KEY or '').strip()
        self.embed_model = GEMINI_MODEL_EMBED
        self._last_dim = 1024
        if not self.api_key:
            print("[WARNING] Missing GEMINI_API_KEY. Embedding generation will fail.")
    
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
        canonical_nav_id = chunk.get('canonical_nav_id') or (chunk.get('metadata', {}) or {}).get('canonical_nav_id')
        section_id = chunk.get('section_id') or (chunk.get('metadata', {}) or {}).get('section_id')
        step_id = chunk.get('step_id') or (chunk.get('metadata', {}) or {}).get('step_id')

        text = f"[TYPE: {chunk_type}] [YEAR: {year}] {title}\n{content}"
        if canonical_nav_id:
            metadata_parts.append(f"CanonicalNav: {canonical_nav_id}")
        if section_id:
            metadata_parts.append(f"SectionID: {section_id}")
        if step_id:
            metadata_parts.append(f"StepID: {step_id}")

        if metadata_parts:
            text += f"\nMetadata: {', '.join(metadata_parts)}"
        return text
    
    def generate_embedding(self, text: str) -> List[float]:
        """Tạo embedding vector qua Gemini Embeddings API."""
        if not self.api_key:
            return [0.0] * self._last_dim

        payload = {
            'model': f"models/{self.embed_model}",
            'content': {
                'parts': [{'text': text or ''}]
            }
        }

        try:
            response = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{self.embed_model}:embedContent?key={self.api_key}",
                headers={'content-type': 'application/json'},
                json=payload,
                timeout=45
            )

            if response.status_code == 429:
                raise Exception('quota')
            if response.status_code != 200:
                raise Exception(f"API {response.status_code}: {response.text[:300]}")

            result = response.json()
            emb = ((result.get('embedding') or {}).get('values') or [])
            if emb:
                self._last_dim = len(emb)
                return emb
            raise Exception('embedding_not_found_in_response')
        except Exception as e:
            print(f"[WARNING] REST Embedding error: {e}")
            return [0.0] * self._last_dim


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

    def find(self, where: Dict[str, Any] = None) -> Dict[str, Any]:
        """Tìm chunks theo metadata filter (tương thích với automation_retriever)."""
        if not where:
            return {
                "ids": [chunk.get("chunk_id") for chunk in self.data["chunks"]],
                "documents": [chunk.get("content", "") for chunk in self.data["chunks"]],
                "metadatas": self.data["chunks"]
            }

        found_ids = []
        found_docs = []
        found_metadatas = []

        for chunk in self.data["chunks"]:
            match = True
            for key, value in where.items():
                if chunk.get(key) != value:
                    match = False
                    break
            if match:
                found_ids.append(chunk.get("chunk_id"))
                found_docs.append(chunk.get("content", ""))
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

    def _invalidate_response_cache(self, cache_file: str = "response_cache.json"):
        """Reset cache sau reindex để tránh trả lời cũ lệch dữ liệu mới."""
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=2)
            print(f"[CACHE] Đã reset {cache_file} sau khi reindex")
        except Exception as e:
            print(f"[WARNING] Không thể reset cache: {e}")

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
        self._invalidate_response_cache()
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
