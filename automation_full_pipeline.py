# -*- coding: utf-8 -*-
"""
AUTOMATION FULL PIPELINE V2
Quy trình: Load Doc -> AI Semantic Chunking -> AI Metadata Tagging -> Embedding -> Vector DB
"""

import os
import json
import glob
from typing import List, Dict, Any
from pathlib import Path

from automation_ai_rag import AIAutomation
from phase1_chunking import TextExtractor
from phase2_embedding import EmbeddingGenerator, VectorStorage
from config import get_admission_year

ADMISSION_YEAR = get_admission_year()

class AutomationPipeline:
    def __init__(self):
        self.ai = AIAutomation()
        self.embedding_gen = EmbeddingGenerator()
        self.vector_db = VectorStorage()
        
    def run(self, data_dir: str = 'data'):
        """Chạy toàn bộ quy trình tự động hóa"""
        print("=" * 70)
        print("🚀 KHỞI CHẠY AUTOMATION PIPELINE (AI-POWERED)")
        print("=" * 70)
        
        # 1. Scan documents
        files = []
        for ext in ['*.txt', '*.docx', '*.pdf']:
            files.extend(glob.glob(os.path.join(data_dir, ext)))
        
        # 2. Kiểm tra xem file nào đã có trong DB
        self.vector_db.load()
        indexed_files = set([c.get('source') for c in self.vector_db.data.get('chunks', [])])
        
        all_ai_chunks = []
        
        # 3. AI Hierarchical Scanning (Chỉ nạp file MỚI)
        for file_path in files:
            file_name = os.path.basename(file_path)
            if file_name in indexed_files:
                print(f"[SKIP] Bỏ qua file đã có trong bộ nhớ: {file_name}")
                continue
                
            print(f"\n[SCAN] Đang nạp tài liệu MỚI: {file_name}")
            raw_text = TextExtractor.extract(file_path)
            if not raw_text: continue
            
            # Gọi LLM thực hiện One-Shot Hierarchy cho file mới
            chunks = self.ai.auto_hierarchical_scan(raw_text, file_name)
            print(f"[OK] Đã tạo {len(chunks)} chunks cho file mới.")
            all_ai_chunks.extend(chunks)

        if not all_ai_chunks:
            print("[ERROR] Không tạo được chunks nào.")
            return

        # 3. Embedding & Storage
        print(f"\n[EMBEDDING] Đang tạo vector cho {len(all_ai_chunks)} chunks...")
        
        embeddings = []
        final_chunks = []
        
        for i, chunk in enumerate(all_ai_chunks):
            # Giữ nguyên ID và các thông tin phân cấp từ AI
            chunk['year'] = ADMISSION_YEAR 
            
            # Sử dụng EmbeddingGenerator để chuẩn bị text
            text_to_embed = self.embedding_gen.prepare_text_for_embedding(chunk)
            embedding = self.embedding_gen.generate_embedding(text_to_embed)
            
            embeddings.append(embedding)
            final_chunks.append(chunk)
            
        # Lưu vào DB (CHẾ ĐỘ CỘNG DỒN - APPEND)
        # Không gọi create_collection() để giữ các file đã nạp trước đó
        self.vector_db.load() # Load lại DB hiện tại trước khi thêm mới
        self.vector_db.add_chunks(chunks=final_chunks, embeddings=embeddings)
        
        # Lưu bản backup JSON
        with open('ai_chunks_debug.json', 'w', encoding='utf-8') as f:
            json.dump(final_chunks, f, ensure_ascii=False, indent=2)
            
        print(f"\n[SUCCESS] Hoàn thành! Đã cộng dồn thêm {len(final_chunks)} chunks vào Vector DB.")
        print("=" * 70)

if __name__ == "__main__":
    pipeline = AutomationPipeline()
    pipeline.run()
