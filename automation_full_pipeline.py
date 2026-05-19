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
        print(f"   Năm tuyển sinh: {ADMISSION_YEAR}")
        print("=" * 70)

        # 1. Scan documents - chỉ lấy file đúng năm tuyển sinh
        all_files = []
        for ext in ['*.txt', '*.docx', '*.pdf']:
            all_files.extend(glob.glob(os.path.join(data_dir, ext)))

        year_str = str(ADMISSION_YEAR)
        files = [f for f in all_files if year_str in os.path.basename(f)]
        if not files:
            print(f"[WARNING] Không tìm thấy file nào chứa năm {year_str} trong {data_dir}/")
            print(f"          Các file có: {[os.path.basename(f) for f in all_files]}")
            return

        print(f"[FILTER] Chỉ xử lý {len(files)} file cho năm {year_str}:")
        for f in files:
            print(f"         - {os.path.basename(f)}")

        # 2. Load DB và xóa chunks cũ của năm này (rebuild sạch cho năm đó)
        self.vector_db.load()
        existing_chunks = self.vector_db.data.get('chunks', [])
        existing_embeddings = self.vector_db.data.get('embeddings', [])

        keep_chunks = []
        keep_embeddings = []
        removed = 0
        for i, c in enumerate(existing_chunks):
            c_year = c.get('year') or (c.get('metadata') or {}).get('year')
            if c_year == ADMISSION_YEAR:
                removed += 1
            else:
                keep_chunks.append(c)
                if i < len(existing_embeddings):
                    keep_embeddings.append(existing_embeddings[i])

        if removed:
            print(f"[CLEAN] Đã xóa {removed} chunks cũ của năm {year_str} khỏi DB")

        all_ai_chunks = []

        # 3. AI Hierarchical Scanning
        for file_path in files:
            file_name = os.path.basename(file_path)
            print(f"\n[SCAN] Đang nạp tài liệu: {file_name}")
            raw_text = TextExtractor.extract(file_path)
            if not raw_text: continue

            chunks = self.ai.auto_hierarchical_scan(raw_text, file_name)
            print(f"[OK] Đã tạo {len(chunks)} chunks.")
            all_ai_chunks.extend(chunks)

        if not all_ai_chunks:
            print("[ERROR] Không tạo được chunks nào.")
            return

        # 4. Embedding & Storage
        print(f"\n[EMBEDDING] Đang tạo vector cho {len(all_ai_chunks)} chunks...")

        embeddings = []
        final_chunks = []

        for i, chunk in enumerate(all_ai_chunks):
            chunk['year'] = ADMISSION_YEAR

            text_to_embed = self.embedding_gen.prepare_text_for_embedding(chunk)
            embedding = self.embedding_gen.generate_embedding(text_to_embed)

            embeddings.append(embedding)
            final_chunks.append(chunk)

        # Gộp chunks giữ lại (năm khác) + chunks mới (năm hiện tại)
        merged_chunks = keep_chunks + final_chunks
        merged_embeddings = keep_embeddings + embeddings

        self.vector_db.data['chunks'] = merged_chunks
        self.vector_db.data['embeddings'] = merged_embeddings
        self.vector_db.save()

        # Lưu bản backup JSON
        with open('ai_chunks_debug.json', 'w', encoding='utf-8') as f:
            json.dump(final_chunks, f, ensure_ascii=False, indent=2)

        print(f"\n[SUCCESS] Hoàn thành! Vector DB chứa {len(merged_chunks)} chunks tổng cộng.")
        print(f"          - Giữ lại từ năm khác: {len(keep_chunks)}")
        print(f"          - Mới cho năm {ADMISSION_YEAR}: {len(final_chunks)}")
        print("=" * 70)

if __name__ == "__main__":
    pipeline = AutomationPipeline()
    pipeline.run()
